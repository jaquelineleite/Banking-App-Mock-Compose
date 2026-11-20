import psycopg
import pytest

from banking_api.database import migrar
from banking_api.main import create_app
from banking_api.tests.api_client import BankingApiClient
from fastapi.testclient import TestClient


def test_reaplicar_migracao_e_recriar_app_preserva_saldos(api, tokens, postgres_dsn):
    token = tokens["conta-a"]
    resposta = api.transferir(
        {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250}, token
    )
    assert resposta.status_code == 201

    migrar(postgres_dsn)
    with TestClient(create_app()) as client:
        novo_app = BankingApiClient(client)
        assert novo_app.consultar_conta("conta-a", token).json()["saldo_centavos"] == 9750
        assert novo_app.consultar_conta(
            "conta-b", tokens["conta-b"]
        ).json()["saldo_centavos"] == 5250

    with psycopg.connect(postgres_dsn) as connection:
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM transferencias").fetchone() == (1,)


@pytest.mark.parametrize(
    ("operacao", "erro"),
    [
        ("UPDATE contas SET saldo_centavos = -1 WHERE id = 'conta-a'", psycopg.errors.CheckViolation),
        (
            "INSERT INTO transferencias VALUES (gen_random_uuid(), 'conta-a', 'conta-b', 0)",
            psycopg.errors.CheckViolation,
        ),
        (
            "INSERT INTO transferencias VALUES (gen_random_uuid(), 'conta-a', 'conta-a', 1)",
            psycopg.errors.CheckViolation,
        ),
        (
            "INSERT INTO transferencias VALUES (gen_random_uuid(), 'conta-a', 'inexistente', 1)",
            psycopg.errors.ForeignKeyViolation,
        ),
    ],
)
def test_banco_rejeita_operacoes_invalidas(postgres_dsn, operacao, erro):
    with pytest.raises(erro), psycopg.connect(postgres_dsn) as connection:
        connection.execute(operacao)
