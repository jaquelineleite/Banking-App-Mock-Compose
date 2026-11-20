from uuid import UUID

from pytest_bdd import given, parsers, scenario, then, when


@scenario("features/transferencia.feature", "O valor sai da origem e entra no destino")
def test_jornada_de_transferencia():
    pass


def consultar_saldos(api, tokens):
    respostas = [api.consultar_conta(conta, token) for conta, token in tokens.items()]
    assert [resposta.status_code for resposta in respostas] == [200, 200]
    return tuple(resposta.json()["saldo_centavos"] for resposta in respostas)


@given(
    parsers.parse("que a conta A tem {origem:d} centavos e a conta B tem {destino:d} centavos"),
    target_fixture="saldos_iniciais",
)
def verificar_saldos_iniciais(api, tokens, origem, destino):
    saldos = consultar_saldos(api, tokens)
    assert saldos == (origem, destino)
    return saldos


@when(
    parsers.parse("transfiro {valor:d} centavos da conta A para a conta B"),
    target_fixture="resposta_transferencia",
)
def enviar_transferencia(api, tokens, valor):
    return api.transferir(
        {"origem": "conta-a", "destino": "conta-b", "valor_centavos": valor},
        tokens["conta-a"],
    )


@then(parsers.parse("o comprovante confirma a origem, o destino e {valor:d} centavos em BRL"))
def verificar_comprovante(resposta_transferencia, valor):
    assert resposta_transferencia.status_code == 201
    comprovante = resposta_transferencia.json()
    assert UUID(comprovante["id"]).version == 4
    assert comprovante["origem"] == "conta-a"
    assert comprovante["destino"] == "conta-b"
    assert comprovante["valor_centavos"] == valor
    assert comprovante["moeda"] == "BRL"


@then(parsers.parse("os saldos finais são {origem:d} e {destino:d} centavos"), target_fixture="saldos_finais")
def verificar_saldos_finais(api, tokens, origem, destino):
    saldos = consultar_saldos(api, tokens)
    assert saldos == (origem, destino)
    return saldos


@then("o saldo total das duas contas permanece igual ao inicial")
def verificar_conservacao_do_saldo(saldos_iniciais, saldos_finais):
    assert sum(saldos_finais) == sum(saldos_iniciais)
