import os
import re
from hmac import compare_digest
from threading import Lock
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field


class Conta(BaseModel):
    id: str
    saldo_centavos: int
    moeda: Literal["BRL"] = "BRL"


class SolicitacaoTransferencia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origem: Annotated[str, Field(min_length=1, max_length=64)]
    destino: Annotated[str, Field(min_length=1, max_length=64)]
    valor_centavos: Annotated[int, Field(strict=True, ge=1, le=1_000_000_000)]


class Transferencia(BaseModel):
    id: UUID
    origem: str
    destino: str
    valor_centavos: int
    moeda: Literal["BRL"] = "BRL"


class Erro(BaseModel):
    detail: str


NAO_AUTENTICADO = {401: {"model": Erro, "description": "Token ausente ou inválido"}}
CONTA_INDISPONIVEL = {404: {"model": Erro, "description": "Conta não encontrada"}}


def create_app() -> FastAPI:
    tokens = {
        "conta-a": os.environ.get("BANKING_LAB_TOKEN_A", ""),
        "conta-b": os.environ.get("BANKING_LAB_TOKEN_B", ""),
    }
    if len(set(tokens.values())) != len(tokens) or any(
        not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token) for token in tokens.values()
    ):
        raise RuntimeError("Configure dois tokens distintos em BANKING_LAB_TOKEN_A e BANKING_LAB_TOKEN_B.")

    app = FastAPI(title="API bancária de laboratório", version="0.1.0")
    bearer = HTTPBearer(auto_error=False)
    saldos = {"conta-a": 10_000, "conta-b": 5_000}
    lock = Lock()

    def conta_autenticada(
        credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> str:
        recebido = credencial.credentials.encode("utf-8") if credencial else b""
        contas = [
            conta for conta, token in tokens.items()
            if compare_digest(recebido, token.encode("ascii"))
        ]
        if not contas:
            raise HTTPException(401, "token_invalido", headers={"WWW-Authenticate": "Bearer"})
        return contas[0]

    @app.get("/contas", responses=NAO_AUTENTICADO, summary="Listar contas próprias")
    def listar_contas(conta: Annotated[str, Depends(conta_autenticada)]) -> list[Conta]:
        with lock:
            return [Conta(id=conta, saldo_centavos=saldos[conta])]

    @app.get(
        "/contas/{conta_id}",
        responses=NAO_AUTENTICADO | CONTA_INDISPONIVEL,
        summary="Consultar conta própria",
    )
    def consultar_conta(
        conta_id: str, conta: Annotated[str, Depends(conta_autenticada)]
    ) -> Conta:
        if conta_id != conta:
            raise HTTPException(404, "conta_nao_encontrada")
        with lock:
            return Conta(id=conta_id, saldo_centavos=saldos[conta_id])

    @app.post(
        "/transferencias",
        status_code=201,
        responses=NAO_AUTENTICADO | CONTA_INDISPONIVEL | {
            409: {"model": Erro, "description": "Saldo insuficiente ou mesma conta"}
        },
        summary="Transferir saldo entre contas de laboratório",
    )
    def transferir(
        solicitacao: SolicitacaoTransferencia,
        conta: Annotated[str, Depends(conta_autenticada)],
    ) -> Transferencia:
        origem, destino, valor = solicitacao.origem, solicitacao.destino, solicitacao.valor_centavos
        if origem != conta or destino not in saldos:
            raise HTTPException(404, "conta_nao_encontrada")
        if origem == destino:
            raise HTTPException(409, "mesma_conta")

        with lock:
            if valor > saldos[origem]:
                raise HTTPException(409, "saldo_insuficiente")
            transferencia = Transferencia(
                id=uuid4(), origem=origem, destino=destino, valor_centavos=valor
            )
            saldos[origem] -= valor
            saldos[destino] += valor
        return transferencia

    return app
