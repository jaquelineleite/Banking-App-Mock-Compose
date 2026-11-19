import pytest
from jsonschema import Draft202012Validator


@pytest.fixture
def contrato(api):
    resposta = api.consultar_openapi()
    assert resposta.status_code == 200
    return resposta.json()


def validar_resposta(contrato, resposta, rota, metodo, status):
    assert resposta.status_code == status
    assert resposta.headers["content-type"].split(";", 1)[0] == "application/json"
    schema = contrato["paths"][rota][metodo]["responses"][str(status)]["content"]["application/json"]["schema"]
    schema_com_referencias = {
        "components": contrato["components"],
        "allOf": [schema],
    }
    Draft202012Validator(
        schema_com_referencias,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    ).validate(resposta.json())


@pytest.mark.parametrize("rota", ["/contas", "/contas/{conta_id}"])
def test_contrato_de_consulta(api, tokens, contrato, rota):
    token = tokens["conta-a"]
    resposta = (
        api.listar_contas(token) if rota == "/contas" else api.consultar_conta("conta-a", token)
    )
    validar_resposta(contrato, resposta, rota, "get", 200)


@pytest.mark.parametrize(
    ("status", "alteracao", "autenticado"),
    [
        (201, {}, True),
        (401, {}, False),
        (404, {"destino": "inexistente"}, True),
        (409, {"valor_centavos": 10_001}, True),
        (422, {"valor_centavos": 0}, True),
    ],
)
def test_contrato_de_transferencia(api, tokens, contrato, status, alteracao, autenticado):
    dados = {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250} | alteracao
    resposta = api.transferir(dados, tokens["conta-a"] if autenticado else None)
    validar_resposta(contrato, resposta, "/transferencias", "post", status)


def test_contrato_de_consulta_sem_token(api, contrato):
    validar_resposta(contrato, api.listar_contas(None), "/contas", "get", 401)


def test_contrato_de_consulta_indisponivel(api, tokens, contrato):
    resposta = api.consultar_conta("inexistente", tokens["conta-a"])
    validar_resposta(contrato, resposta, "/contas/{conta_id}", "get", 404)
