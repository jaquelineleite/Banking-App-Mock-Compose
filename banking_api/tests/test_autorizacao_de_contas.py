import pytest


@pytest.mark.parametrize(
    ("propria", "outra"),
    [("conta-a", "conta-b"), ("conta-b", "conta-a")],
)
def test_isolamento_de_contas_por_titular(api, tokens, propria, outra):
    def saldos():
        respostas = [api.consultar_conta(conta, token) for conta, token in tokens.items()]
        assert all(resposta.status_code == 200 for resposta in respostas)
        return [resposta.json()["saldo_centavos"] for resposta in respostas]

    antes = saldos()
    lista = api.listar_contas(tokens[propria])
    assert lista.status_code == 200
    assert [conta["id"] for conta in lista.json()] == [propria]

    consulta = api.consultar_conta(outra, tokens[propria])
    inexistente = api.consultar_conta("conta-inexistente", tokens[propria])
    assert consulta.status_code == inexistente.status_code == 404
    assert consulta.json() == inexistente.json() == {"detail": "conta_nao_encontrada"}

    transferencia = api.transferir(
        {"origem": outra, "destino": propria, "valor_centavos": 1},
        tokens[propria],
    )
    assert transferencia.status_code == 404
    assert transferencia.json() == {"detail": "conta_nao_encontrada"}
    assert saldos() == antes
