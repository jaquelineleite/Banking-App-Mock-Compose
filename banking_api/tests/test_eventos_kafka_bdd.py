import json
import os
from pathlib import Path
from threading import Event
from time import monotonic
from uuid import UUID, uuid4

import psycopg
import pytest
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic
from jsonschema import Draft202012Validator, FormatChecker
from pytest_bdd import given, parsers, scenarios, then, when
from fastapi.testclient import TestClient

from banking_api.eventos import PublicadorTransferencias
from banking_api.main import create_app
from banking_api.outbox import despachar_lote
from banking_api.tests.api_client import BankingApiClient


scenarios("features/eventos_kafka.feature")

PARTICOES = range(3)
CONTRATO = Path(__file__).resolve().parents[1] / "contratos" / "transferencia.confirmada.v1.json"
VALIDADOR = Draft202012Validator(
    json.loads(CONTRATO.read_text(encoding="utf-8")), format_checker=FormatChecker()
)


def ler_evento(consumidor):
    mensagem = consumidor.poll(10)
    assert mensagem is not None, "Nenhum evento chegou ao consumidor Kafka"
    assert mensagem.error() is None
    return mensagem


def contar_eventos(consumidor, topico):
    intervalos = [
        consumidor.get_watermark_offsets(TopicPartition(topico, particao), timeout=10)
        for particao in PARTICOES
    ]
    return sum(fim - inicio for inicio, fim in intervalos)


@given("um tópico Kafka isolado", target_fixture="topico_kafka")
def preparar_topico(monkeypatch, request):
    servidores = os.environ.get("BANKING_TEST_KAFKA_BOOTSTRAP_SERVERS")
    if not servidores:
        pytest.skip("Configure BANKING_TEST_KAFKA_BOOTSTRAP_SERVERS com um Kafka de teste.")

    topico = f"transferencias-teste-{uuid4().hex}"
    admin = AdminClient({"bootstrap.servers": servidores})
    admin.create_topics([NewTopic(topico, len(PARTICOES), 1)], request_timeout=20)[topico].result()
    request.addfinalizer(
        lambda: admin.delete_topics([topico], request_timeout=10)[topico].result()
    )
    monkeypatch.setenv("BANKING_KAFKA_BOOTSTRAP_SERVERS", servidores)
    monkeypatch.setenv("BANKING_KAFKA_TOPIC", topico)

    consumer = Consumer({
        "bootstrap.servers": servidores,
        "group.id": topico,
        "enable.auto.commit": False,
    })
    request.addfinalizer(consumer.close)
    prazo = monotonic() + 10
    espera = Event()
    while monotonic() < prazo:
        metadados = consumer.list_topics(timeout=max(0.1, prazo - monotonic()))
        dados = metadados.topics.get(topico)
        if dados and dados.error is None and set(dados.partitions) == set(PARTICOES) and all(
            particao.error is None and particao.leader >= 0
            for particao in dados.partitions.values()
        ):
            break
        espera.wait(0.1)
    else:
        pytest.fail(f"Partições do tópico {topico} sem líder dentro do prazo.")

    consumer.assign([TopicPartition(topico, particao, 0) for particao in PARTICOES])
    return consumer, topico


@when(parsers.parse("solicito uma transferência de {valor:d} centavos com mensageria habilitada"),
      target_fixture="resposta")
def solicitar(api, tokens, valor):
    return api.transferir(
        {"origem": "conta-a", "destino": "conta-b", "valor_centavos": valor},
        tokens["conta-a"],
    )


@then("o evento consumido corresponde ao comprovante persistido")
def conferir_evento(topico_kafka, postgres_dsn, resposta):
    assert resposta.status_code == 201
    comprovante = resposta.json()
    consumidor, _ = topico_kafka
    mensagem = ler_evento(consumidor)
    assert mensagem.key() == b"conta-a"
    evento = json.loads(mensagem.value())
    VALIDADOR.validate(evento)
    assert evento == {
        "tipo": "transferencia.confirmada.v1",
        "transferencia_id": comprovante["id"],
        "valor_centavos": 250,
        "moeda": "BRL",
    }
    with psycopg.connect(postgres_dsn) as banco:
        assert banco.execute(
            "SELECT id, origem, destino, valor_centavos FROM transferencias"
        ).fetchall() == [(UUID(comprovante["id"]), "conta-a", "conta-b", 250)]


@then("a API rejeita a transferência e o tópico permanece vazio")
def conferir_rejeicao(topico_kafka, postgres_dsn, resposta):
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "saldo_insuficiente"}
    consumidor, topico = topico_kafka
    assert contar_eventos(consumidor, topico) == 0
    with psycopg.connect(postgres_dsn) as banco:
        assert banco.execute("SELECT count(*) FROM transferencias").fetchone() == (0,)


@when("reenvio uma transferência com a mesma chave de idempotência", target_fixture="respostas")
def reenviar(api, tokens):
    dados = {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250}
    return [api.transferir(dados, tokens["conta-a"], "transferencia-250") for _ in range(2)]


@then("o comprovante é reutilizado e o tópico contém apenas um evento")
def conferir_evento_unico(topico_kafka, respostas):
    original, repetida = respostas
    assert original.status_code == repetida.status_code == 201
    assert original.json() == repetida.json()
    consumidor, topico = topico_kafka
    mensagem = ler_evento(consumidor)
    assert json.loads(mensagem.value())["transferencia_id"] == original.json()["id"]
    assert contar_eventos(consumidor, topico) == 1


@when("confirmo três transferências sequenciais da mesma conta", target_fixture="comprovantes")
def transferir_em_ordem(api, tokens):
    comprovantes = []
    for valor in (100, 200, 300):
        resposta = solicitar(api, tokens, valor)
        assert resposta.status_code == 201
        comprovantes.append(resposta.json()["id"])
    return comprovantes


@then("os eventos são consumidos na ordem dos comprovantes")
def conferir_ordem(topico_kafka, comprovantes):
    consumidor, topico = topico_kafka
    mensagens = [ler_evento(consumidor) for _ in comprovantes]
    assert {mensagem.key() for mensagem in mensagens} == {b"conta-a"}
    assert len({mensagem.partition() for mensagem in mensagens}) == 1
    primeiro_offset = mensagens[0].offset()
    assert [mensagem.offset() for mensagem in mensagens] == list(
        range(primeiro_offset, primeiro_offset + len(comprovantes))
    )
    assert [json.loads(mensagem.value())["transferencia_id"] for mensagem in mensagens] == comprovantes
    assert contar_eventos(consumidor, topico) == len(comprovantes)


@then("outro consumidor consegue reler o evento sem alterar os saldos")
def reler_evento(topico_kafka, postgres_dsn, resposta):
    assert resposta.status_code == 201
    consumidor, topico = topico_kafka
    original = ler_evento(consumidor)
    particao, offset = original.partition(), original.offset()
    with psycopg.connect(postgres_dsn) as banco:
        consulta = "SELECT id, saldo_centavos FROM contas ORDER BY id"
        saldos = banco.execute(consulta).fetchall()
    assert saldos == [("conta-a", 9750), ("conta-b", 5250)]

    # Uma nova instância retoma explicitamente a posição original de leitura.
    reiniciado = Consumer({
        "bootstrap.servers": os.environ["BANKING_TEST_KAFKA_BOOTSTRAP_SERVERS"],
        "group.id": topico,
        "enable.auto.commit": False,
    })
    try:
        reiniciado.assign([TopicPartition(topico, particao, offset)])
        repetido = ler_evento(reiniciado)
        assert (repetido.partition(), repetido.offset()) == (particao, offset)
        assert (repetido.key(), repetido.value()) == (original.key(), original.value())
        assert json.loads(repetido.value())["transferencia_id"] == resposta.json()["id"]
    finally:
        reiniciado.close()

    with psycopg.connect(postgres_dsn) as banco:
        assert banco.execute(consulta).fetchall() == saldos
        assert banco.execute("SELECT id FROM transferencias").fetchall() == [
            (UUID(resposta.json()["id"]),)
        ]


@when("confirmo uma transferência com o broker inacessível", target_fixture="resposta")
def confirmar_sem_broker(topico_kafka, postgres_dsn, tokens, monkeypatch):
    # A API usa um endpoint inacessível. O consumidor continua ligado ao broker real.
    with monkeypatch.context() as ambiente:
        ambiente.setenv("BANKING_KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:1")
        with TestClient(create_app()) as cliente:
            return solicitar(BankingApiClient(cliente), tokens, 250)


def estado_outbox(dsn):
    with psycopg.connect(dsn) as banco:
        return banco.execute(
            "SELECT transferencia_id, estado, tentativas, topico FROM outbox_transferencias"
        ).fetchall()


@then("a outbox mantém o evento pendente")
def conferir_pendencia(topico_kafka, postgres_dsn, resposta):
    assert resposta.status_code == 201
    consumidor, topico = topico_kafka
    assert estado_outbox(postgres_dsn) == [(UUID(resposta.json()["id"]), "pendente", 1, topico)]
    assert contar_eventos(consumidor, topico) == 0


@when("tento publicar novamente pelo broker disponível")
def recuperar_publicacao(postgres_dsn):
    publicador = PublicadorTransferencias.configurar()
    assert despachar_lote(postgres_dsn, publicador) == 1
    assert despachar_lote(postgres_dsn, publicador) == 0


@then("o evento recuperado corresponde ao comprovante e os saldos permanecem corretos")
def conferir_recuperacao(topico_kafka, postgres_dsn, resposta):
    conferir_evento(topico_kafka, postgres_dsn, resposta)
    consumidor, topico = topico_kafka
    assert contar_eventos(consumidor, topico) == 1
    assert estado_outbox(postgres_dsn) == [(UUID(resposta.json()["id"]), "publicado", 2, topico)]
    conferir_saldos(postgres_dsn)


@when("tento publicar mais duas vezes sem acesso ao broker")
def esgotar_tentativas(postgres_dsn, topico_kafka):
    _, topico = topico_kafka
    publicador = PublicadorTransferencias("127.0.0.1:1", topico)
    assert despachar_lote(postgres_dsn, publicador) == 1
    assert despachar_lote(postgres_dsn, publicador) == 1
    assert despachar_lote(postgres_dsn, publicador) == 0


@then("a outbox registra o evento na DLQ e os saldos permanecem corretos")
def conferir_dlq(topico_kafka, postgres_dsn, resposta):
    consumidor, topico = topico_kafka
    assert estado_outbox(postgres_dsn) == [(UUID(resposta.json()["id"]), "dlq", 3, topico)]
    assert contar_eventos(consumidor, topico) == 0
    conferir_saldos(postgres_dsn)


def conferir_saldos(dsn):
    with psycopg.connect(dsn) as banco:
        assert dict(banco.execute("SELECT id, saldo_centavos FROM contas")) == {
            "conta-a": 9750,
            "conta-b": 5250,
        }
