import pytest


DADOS_VALIDOS = {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250}


def consultar_saldos(api, tokens):
    origem = api.consultar_conta("conta-a", tokens["conta-a"])
    destino = api.consultar_conta("conta-b", tokens["conta-b"])
    assert origem.status_code == destino.status_code == 200
    return origem.json()["saldo_centavos"], destino.json()["saldo_centavos"]


@pytest.mark.parametrize(
    ("campo", "alteracao", "tipo"),
    [
        pytest.param("origem", {}, "missing", id="sem-origem"),
        pytest.param("destino", {}, "missing", id="sem-destino"),
        pytest.param("valor_centavos", {}, "missing", id="sem-valor"),
        pytest.param("moeda", {"moeda": "BRL"}, "extra_forbidden", id="campo-extra"),
        pytest.param("origem", {"origem": 1}, "string_type", id="origem-numerica"),
        pytest.param("destino", {"destino": []}, "string_type", id="destino-lista"),
        pytest.param("valor_centavos", {"valor_centavos": None}, "int_type", id="valor-nulo"),
    ],
)
def test_payload_invalido_preserva_os_saldos(api, tokens, campo, alteracao, tipo):
    dados = DADOS_VALIDOS.copy()
    if tipo == "missing":
        del dados[campo]
    dados.update(alteracao)
    antes = consultar_saldos(api, tokens)

    resposta = api.transferir(dados, tokens["conta-a"])

    assert resposta.status_code == 422
    erros = {(tuple(erro["loc"]), erro["type"]) for erro in resposta.json()["detail"]}
    assert (("body", campo), tipo) in erros
    assert consultar_saldos(api, tokens) == antes


@pytest.mark.parametrize(
    ("valor", "status", "erro"),
    [
        pytest.param(0, 422, "greater_than_equal", id="abaixo-do-minimo"),
        pytest.param(1, 201, None, id="minimo"),
        pytest.param(2, 201, None, id="acima-do-minimo"),
        pytest.param(9_999, 201, None, id="abaixo-do-saldo"),
        pytest.param(10_000, 201, None, id="saldo-exato"),
        pytest.param(10_001, 409, "saldo_insuficiente", id="acima-do-saldo"),
        pytest.param(999_999_999, 409, "saldo_insuficiente", id="abaixo-do-maximo"),
        pytest.param(1_000_000_000, 409, "saldo_insuficiente", id="maximo-do-contrato"),
        pytest.param(1_000_000_001, 422, "less_than_equal", id="acima-do-maximo"),
    ],
)
def test_limites_de_valor(api, tokens, valor, status, erro):
    origem, destino = consultar_saldos(api, tokens)

    resposta = api.transferir(DADOS_VALIDOS | {"valor_centavos": valor}, tokens["conta-a"])

    assert resposta.status_code == status
    if status == 201:
        assert resposta.json()["valor_centavos"] == valor
        assert consultar_saldos(api, tokens) == (origem - valor, destino + valor)
    elif status == 409:
        assert resposta.json() == {"detail": erro}
        assert consultar_saldos(api, tokens) == (origem, destino)
    else:
        detalhe, = resposta.json()["detail"]
        assert detalhe["loc"] == ["body", "valor_centavos"]
        assert detalhe["type"] == erro
        assert consultar_saldos(api, tokens) == (origem, destino)
