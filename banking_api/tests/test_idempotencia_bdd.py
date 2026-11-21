from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient
from httpx2 import ReadTimeout
from pytest_bdd import given, scenarios, then, when

from banking_api.main import create_app
from banking_api.tests.api_client import BankingApiClient


scenarios("features/idempotencia.feature")

CHAVE = "transferencia-001"
DADOS = {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250}


def comprovante_persistido(dsn):
    with psycopg.connect(dsn) as connection:
        saldos = dict(connection.execute("SELECT id, saldo_centavos FROM contas").fetchall())
        recibos = connection.execute(
            "SELECT id, origem, destino, valor_centavos, chave_idempotencia FROM transferencias"
        ).fetchall()

    assert saldos == {"conta-a": 9_750, "conta-b": 5_250}
    [(recibo, origem, destino, valor, chave)] = recibos
    assert (origem, destino, valor, chave) == ("conta-a", "conta-b", 250, CHAVE)
    return recibo


@given("que a resposta da primeira transferência foi perdida após a confirmação",
       target_fixture="id_original")
def perder_resposta(tokens, postgres_dsn):
    app = create_app()

    async def descartar_resposta(scope, receive, send):
        async def entregar(message):
            if scope["type"] == "http" and message["type"] == "http.response.start":
                assert message["status"] == 201
                raise ReadTimeout("Resposta descartada após confirmação da transferência")
            await send(message)

        await app(scope, receive, entregar)

    with TestClient(descartar_resposta) as client:
        with pytest.raises(ReadTimeout, match="Resposta descartada"):
            BankingApiClient(client).transferir(DADOS, tokens["conta-a"], CHAVE)

    return comprovante_persistido(postgres_dsn)


@given("que uma transferência foi confirmada com uma chave", target_fixture="id_original")
def confirmar_transferencia(api, tokens, postgres_dsn):
    resposta = api.transferir(DADOS, tokens["conta-a"], CHAVE)
    assert resposta.status_code == 201
    assert UUID(resposta.json()["id"]) == comprovante_persistido(postgres_dsn)
    return UUID(resposta.json()["id"])


@when("reenvio a transferência com a mesma chave e os mesmos dados", target_fixture="resposta")
def repetir_transferencia(api, tokens):
    return api.transferir(DADOS, tokens["conta-a"], CHAVE)


@when("reenvio a transferência com a mesma chave e um valor diferente", target_fixture="resposta")
def alterar_valor(api, tokens):
    return api.transferir({**DADOS, "valor_centavos": 251}, tokens["conta-a"], CHAVE)


@then("recebo o comprovante original")
def conferir_reenvio(resposta, id_original):
    assert resposta.status_code == 201
    assert resposta.json() == {"id": str(id_original), **DADOS, "moeda": "BRL"}


@then("a API informa conflito de idempotência")
def conferir_conflito(resposta):
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "chave_idempotencia_em_conflito"}


@then("o PostgreSQL registra um único débito, crédito e comprovante")
def conferir_estado(postgres_dsn, id_original):
    assert comprovante_persistido(postgres_dsn) == id_original
