import json
import os
from uuid import UUID, uuid4

import psycopg
import pytest
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic
from pytest_bdd import given, parsers, scenarios, then, when


scenarios("features/eventos_kafka.feature")


@given("um tópico Kafka isolado", target_fixture="topico_kafka")
def preparar_topico(monkeypatch, request):
    servidores = os.environ.get("BANKING_TEST_KAFKA_BOOTSTRAP_SERVERS")
    if not servidores:
        pytest.skip("Configure BANKING_TEST_KAFKA_BOOTSTRAP_SERVERS com um Kafka de teste.")

    topico = f"transferencias-teste-{uuid4().hex}"
    admin = AdminClient({"bootstrap.servers": servidores})
    admin.create_topics([NewTopic(topico, 1, 1)], request_timeout=20)[topico].result()
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
    consumer.assign([TopicPartition(topico, 0, 0)])
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
    mensagem = consumidor.poll(10)
    assert mensagem is not None, "Nenhum evento chegou ao consumidor Kafka"
    assert mensagem.error() is None
    assert mensagem.key() == b"conta-a"
    assert json.loads(mensagem.value()) == {
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
    assert consumidor.get_watermark_offsets(TopicPartition(topico, 0), timeout=10) == (0, 0)
    with psycopg.connect(postgres_dsn) as banco:
        assert banco.execute("SELECT count(*) FROM transferencias").fetchone() == (0,)
