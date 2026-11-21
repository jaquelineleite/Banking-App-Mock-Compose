from httpx2 import Client, Response


class BankingApiClient:
    def __init__(self, client: Client):
        self.client = client

    def listar_contas(self, token: str | None) -> Response:
        return self.client.get("/contas", headers=self._headers(token))

    def consultar_conta(self, conta: str, token: str | None) -> Response:
        return self.client.get(f"/contas/{conta}", headers=self._headers(token))

    def transferir(
        self, dados: dict, token: str | None, chave: str | None = None
    ) -> Response:
        headers = self._headers(token)
        if chave is not None:
            headers["Idempotency-Key"] = chave
        return self.client.post("/transferencias", json=dados, headers=headers)

    def consultar_openapi(self) -> Response:
        return self.client.get("/openapi.json")

    @staticmethod
    def _headers(token: str | None) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token is not None else {}
