import logging
import os
import re
from hmac import compare_digest
from typing import Annotated, Literal
from uuid import UUID, uuid4

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field


from banking_api.database import (
    ChaveIdempotenciaEmConflito,
    ContaNaoEncontrada,
    MesmaConta,
    PostgreSQLBank,
    SaldoInsuficiente,
    database_url,
)
from banking_api.eventos import PublicadorTransferencias
from banking_api.outbox import despachar_lote


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
BANCO_INDISPONIVEL = {503: {"model": Erro, "description": "Falha no armazenamento"}}
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
    banco = PostgreSQLBank(database_url())
    publicador = PublicadorTransferencias.configurar()

    @app.exception_handler(psycopg.Error)
    async def falha_no_banco(request: Request, error: psycopg.Error) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "armazenamento_indisponivel"})

    @app.exception_handler(ContaNaoEncontrada)
    async def conta_nao_encontrada(request: Request, error: ContaNaoEncontrada) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "conta_nao_encontrada"})

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

    @app.get("/contas", responses=NAO_AUTENTICADO | BANCO_INDISPONIVEL, summary="Listar contas próprias")
    def listar_contas(conta: Annotated[str, Depends(conta_autenticada)]) -> list[Conta]:
        try:
            return [Conta(id=conta, saldo_centavos=banco.saldo(conta))]
        except ContaNaoEncontrada:
            return []

    @app.get(
        "/contas/{conta_id}",
        responses=NAO_AUTENTICADO | CONTA_INDISPONIVEL | BANCO_INDISPONIVEL,
        summary="Consultar conta própria",
    )
    def consultar_conta(
        conta_id: str, conta: Annotated[str, Depends(conta_autenticada)]
    ) -> Conta:
        if conta_id != conta:
            raise HTTPException(404, "conta_nao_encontrada")
        return Conta(id=conta_id, saldo_centavos=banco.saldo(conta_id))

    @app.post(
        "/transferencias",
        status_code=201,
        responses=NAO_AUTENTICADO | CONTA_INDISPONIVEL | BANCO_INDISPONIVEL | {
            409: {"model": Erro, "description": "Saldo insuficiente, mesma conta ou chave em conflito"}
        },
        summary="Transferir saldo entre contas de laboratório",
    )
    def transferir(
        solicitacao: SolicitacaoTransferencia,
        conta: Annotated[str, Depends(conta_autenticada)],
        chave: Annotated[
            str | None,
            Header(
                alias="Idempotency-Key",
                min_length=1,
                max_length=128,
                pattern=r"^[A-Za-z0-9._-]+$",
                description="Chave opcional por conta de origem para recuperar o comprovante em reenvios.",
            ),
        ] = None,
    ) -> Transferencia:
        origem, destino, valor = solicitacao.origem, solicitacao.destino, solicitacao.valor_centavos
        if origem != conta:
            raise HTTPException(404, "conta_nao_encontrada")
        try:
            id_novo = uuid4()
            id_transferencia = banco.transferir(
                id_novo, origem, destino, valor, chave,
                topico=publicador.topico if publicador is not None else None,
            )
        except SaldoInsuficiente as error:
            raise HTTPException(409, "saldo_insuficiente") from error
        except MesmaConta as error:
            raise HTTPException(409, "mesma_conta") from error
        except ChaveIdempotenciaEmConflito as error:
            raise HTTPException(409, "chave_idempotencia_em_conflito") from error

        comprovante = Transferencia(
            id=id_transferencia, origem=origem, destino=destino, valor_centavos=valor
        )
        if publicador is not None and id_transferencia == id_novo:
            try:
                despachar_lote(banco.dsn, publicador, transferencia_id=id_transferencia)
            except psycopg.Error:
                logging.getLogger(__name__).warning(
                    "Falha ao atualizar a outbox da transferência %s", id_transferencia
                )
        return comprovante

    return app
