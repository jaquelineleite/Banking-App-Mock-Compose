from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo
from pytest_bdd import scenarios, then, when

from banking_api.main import create_app
from banking_api.tests.api_client import BankingApiClient


scenarios("features/concorrencia.feature")

VALOR = 6_000
DADOS = {"origem": "conta-a", "destino": "conta-b", "valor_centavos": VALOR}


def aguardar_disputa(dsn, nome, pid_bloqueador):
    prazo = monotonic() + 10
    intervalo = Event()
    with psycopg.connect(dsn, autocommit=True) as observador:
        while monotonic() < prazo:
            bloqueios = observador.execute(
                "SELECT pg_blocking_pids(pid) FROM pg_stat_activity WHERE application_name = %s",
                (nome,),
            ).fetchall()
            if sum(bool(pids) for (pids,) in bloqueios) == 2 and any(
                pid_bloqueador in pids for (pids,) in bloqueios
            ):
                return
            intervalo.wait(0.02)

    raise AssertionError("As duas requisições não chegaram à disputa pelo lock no PostgreSQL")


def disputar(postgres_dsn, tokens, monkeypatch, chaves):
    nome = f"concorrencia_{uuid4().hex}"
    dsn_api = make_conninfo(
        postgres_dsn, application_name=nome,
        options=f"{psycopg.conninfo.conninfo_to_dict(postgres_dsn)['options']} -cstatement_timeout=15000",
    )
    monkeypatch.setenv("BANKING_DATABASE_URL", dsn_api)
    app = create_app()

    def enviar(chave):
        client = TestClient(app)
        try:
            return BankingApiClient(client).transferir(DADOS, tokens["conta-a"], chave)
        finally:
            client.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        # O lock inicial garante a sobreposição observável das duas transações.
        with psycopg.connect(postgres_dsn) as bloqueador:
            bloqueador.execute("SELECT id FROM contas WHERE id = 'conta-a' FOR UPDATE")
            chamadas = [executor.submit(enviar, chave) for chave in chaves]
            aguardar_disputa(postgres_dsn, nome, bloqueador.info.backend_pid)
        return [chamada.result(timeout=20) for chamada in chamadas]


@when("duas transferências de 6000 centavos disputam a conta com a mesma chave",
      target_fixture="respostas")
def concorrer_com_mesma_chave(postgres_dsn, tokens, monkeypatch):
    return disputar(postgres_dsn, tokens, monkeypatch, ("operacao-a", "operacao-a"))


@when("duas transferências de 6000 centavos disputam a conta com chaves distintas",
      target_fixture="respostas")
def concorrer_com_chaves_distintas(postgres_dsn, tokens, monkeypatch):
    return disputar(postgres_dsn, tokens, monkeypatch, ("operacao-a", "operacao-b"))


@then("as duas respostas devolvem o mesmo comprovante")
def conferir_repeticao(respostas):
    primeira, segunda = respostas
    assert primeira.status_code == segunda.status_code == 201
    assert primeira.json() == segunda.json()


@then("apenas uma transferência é aprovada e a outra é rejeitada por saldo insuficiente")
def conferir_disputa(respostas):
    aprovada, rejeitada = sorted(respostas, key=lambda resposta: resposta.status_code)
    assert (aprovada.status_code, rejeitada.status_code) == (201, 409)
    assert rejeitada.json() == {"detail": "saldo_insuficiente"}


@then("o banco registra um único débito e um único crédito")
def conferir_movimentacao(postgres_dsn, respostas):
    comprovante = next(resposta.json() for resposta in respostas if resposta.status_code == 201)
    with psycopg.connect(postgres_dsn) as banco:
        saldos = dict(banco.execute("SELECT id, saldo_centavos FROM contas").fetchall())
        registros = banco.execute(
            "SELECT id, origem, destino, valor_centavos FROM transferencias"
        ).fetchall()

    assert saldos == {"conta-a": 4_000, "conta-b": 11_000}
    assert registros == [(UUID(comprovante["id"]), "conta-a", "conta-b", VALOR)]
