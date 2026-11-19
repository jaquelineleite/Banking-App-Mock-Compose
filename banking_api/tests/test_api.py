import pytest
from fastapi.testclient import TestClient

from banking_api.main import create_app


TOKEN_A = "a" * 32
TOKEN_B = "b" * 32
ENV_A = "BANKING_LAB_TOKEN_A"
ENV_B = "BANKING_LAB_TOKEN_B"
AUTH_A = {"Authorization": f"Bearer {TOKEN_A}"}
AUTH_B = {"Authorization": f"Bearer {TOKEN_B}"}
ENVIO = {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv(ENV_A, TOKEN_A)
    monkeypatch.setenv(ENV_B, TOKEN_B)
    with TestClient(create_app()) as client:
        yield client


def saldos(client):
    return [
        client.get(f"/contas/conta-{conta}", headers=headers).json()["saldo_centavos"]
        for conta, headers in [("a", AUTH_A), ("b", AUTH_B)]
    ]


def test_lista_e_consulta_apenas_contas_proprias(client):
    response = client.get("/contas", headers=AUTH_A)
    assert response.status_code == 200
    assert response.json() == [{"id": "conta-a", "saldo_centavos": 10_000, "moeda": "BRL"}]
    assert saldos(client) == [10_000, 5_000]
    assert client.get("/contas/conta-b", headers=AUTH_A).status_code == 404


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer desconhecido"}])
def test_requer_token_valido(client, headers):
    resposta = client.get("/contas", headers=headers)
    assert resposta.status_code == 401
    assert resposta.headers["WWW-Authenticate"] == "Bearer"
    assert client.post("/transferencias", headers=headers, json=ENVIO).status_code == 401
    assert saldos(client) == [10_000, 5_000]


@pytest.mark.parametrize("valor", [250, 10_000])
def test_transfere_valor_preservando_total(client, valor):
    resposta = client.post("/transferencias", headers=AUTH_A, json=ENVIO | {"valor_centavos": valor})
    assert resposta.status_code == 201
    assert resposta.json()["valor_centavos"] == valor
    assert saldos(client) == [10_000 - valor, 5_000 + valor]


@pytest.mark.parametrize("valor", [0, -1, "250", 1.5, True, 1_000_000_001])
def test_recusa_valores_fora_do_contrato(client, valor):
    resposta = client.post("/transferencias", headers=AUTH_A, json=ENVIO | {"valor_centavos": valor})
    assert resposta.status_code == 422
    assert saldos(client) == [10_000, 5_000]


@pytest.mark.parametrize(
    ("alteracao", "token", "status", "detail"),
    [
        ({}, AUTH_B, 404, "conta_nao_encontrada"),
        ({"destino": "inexistente"}, AUTH_A, 404, "conta_nao_encontrada"),
        ({"destino": "conta-a"}, AUTH_A, 409, "mesma_conta"),
        ({"valor_centavos": 10_001}, AUTH_A, 409, "saldo_insuficiente"),
    ],
)
def test_rejeicao_preserva_os_dois_saldos(client, alteracao, token, status, detail):
    resposta = client.post("/transferencias", headers=token, json=ENVIO | alteracao)
    assert resposta.status_code == status
    assert resposta.json() == {"detail": detail}
    assert saldos(client) == [10_000, 5_000]


def test_openapi_documenta_seguranca_limites_e_respostas(client):
    contrato = client.get("/openapi.json").json()
    assert contrato["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    post = contrato["paths"]["/transferencias"]["post"]
    assert post["security"] == [{"HTTPBearer": []}]
    assert set(post["responses"]) == {"201", "401", "404", "409", "422"}
    valor = contrato["components"]["schemas"]["SolicitacaoTransferencia"]["properties"]["valor_centavos"]
    assert (valor["type"], valor["minimum"], valor["maximum"]) == ("integer", 1, 1_000_000_000)


def test_configuracao_recusa_tokens_ausentes_ou_iguais(monkeypatch):
    monkeypatch.delenv(ENV_A, raising=False)
    monkeypatch.delenv(ENV_B, raising=False)
    with pytest.raises(RuntimeError, match=ENV_A):
        create_app()
    monkeypatch.setenv(ENV_A, TOKEN_A)
    monkeypatch.setenv(ENV_B, TOKEN_A)
    with pytest.raises(RuntimeError, match=ENV_B):
        create_app()
