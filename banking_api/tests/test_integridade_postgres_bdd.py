from uuid import UUID

import psycopg
from pytest_bdd import given, parsers, scenarios, then, when


scenarios("features/integridade_financeira.feature")


def saldos_e_comprovantes(dsn):
    with psycopg.connect(dsn) as connection:
        saldos = dict(connection.execute("SELECT id, saldo_centavos FROM contas").fetchall())
        comprovantes = connection.execute(
            "SELECT id, origem, destino, valor_centavos FROM transferencias"
        ).fetchall()
    return saldos, comprovantes


@given("que o banco tem as duas contas com os saldos iniciais", target_fixture="estado_inicial")
def verificar_estado_inicial(postgres_dsn):
    estado = saldos_e_comprovantes(postgres_dsn)
    assert estado == ({"conta-a": 10_000, "conta-b": 5_000}, [])
    return estado


@given("que o PostgreSQL interrompe o crédito após observar o débito")
def interromper_credito(postgres_dsn):
    with psycopg.connect(postgres_dsn) as connection:
        # Sequências preservam nextval mesmo se a transação for revertida.
        connection.execute("CREATE SEQUENCE credito_interrompido")
        connection.execute("""
            CREATE FUNCTION interromper_credito() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF (SELECT saldo_centavos FROM contas WHERE id = 'conta-a') = 9750 THEN
                    PERFORM nextval('credito_interrompido');
                    RAISE EXCEPTION 'Falha controlada antes do crédito';
                END IF;
                RETURN NEW;
            END;
            $$
            """)
        connection.execute("""
            CREATE TRIGGER falha_no_credito BEFORE UPDATE ON contas
            FOR EACH ROW WHEN (NEW.id = 'conta-b') EXECUTE FUNCTION interromper_credito()
            """)


@when(parsers.parse("solicito uma transferência de {valor:d} centavos"), target_fixture="resposta")
def transferir(api, tokens, valor):
    return api.transferir(
        {"origem": "conta-a", "destino": "conta-b", "valor_centavos": valor},
        tokens["conta-a"],
    )


@then("a API confirma a transferência")
def confirmar_transferencia(resposta):
    assert resposta.status_code == 201


@then(parsers.parse("o banco registra um débito de {valor:d} centavos, o crédito e o comprovante"))
def verificar_persistencia(postgres_dsn, resposta, estado_inicial, valor):
    antes, _ = estado_inicial
    saldos, comprovantes = saldos_e_comprovantes(postgres_dsn)
    assert saldos == {"conta-a": antes["conta-a"] - valor, "conta-b": antes["conta-b"] + valor}
    assert comprovantes == [(UUID(resposta.json()["id"]), "conta-a", "conta-b", valor)]


@then("a API rejeita a transferência por saldo insuficiente")
def confirmar_rejeicao(resposta):
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "saldo_insuficiente"}


@then("a API informa uma falha de armazenamento")
def confirmar_falha(resposta):
    assert resposta.status_code == 503
    assert resposta.json() == {"detail": "armazenamento_indisponivel"}


@then("o banco registra que a falha ocorreu após o débito")
def confirmar_falha_intermediaria(postgres_dsn):
    with psycopg.connect(postgres_dsn) as connection:
        assert connection.execute(
            "SELECT last_value, is_called FROM credito_interrompido"
        ).fetchone() == (1, True)


@then("o banco mantém os dois saldos e nenhum comprovante")
def verificar_preservacao(postgres_dsn, estado_inicial):
    assert saldos_e_comprovantes(postgres_dsn) == estado_inicial
