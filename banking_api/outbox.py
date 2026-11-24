from uuid import UUID

import psycopg

from banking_api.database import database_url
from banking_api.eventos import PublicadorTransferencias


MAX_TENTATIVAS = 3


def despachar_lote(
    dsn: str,
    publicador: PublicadorTransferencias,
    *,
    transferencia_id: UUID | None = None,
) -> int:
    """Tenta entregar cada registro selecionado uma vez neste lote."""
    with psycopg.connect(dsn) as banco:
        filtro = "AND o.transferencia_id = %s" if transferencia_id is not None else ""
        parametros = (transferencia_id,) if transferencia_id is not None else ()
        registros = banco.execute(
            f"""
            SELECT o.transferencia_id, o.topico, o.tentativas, t.origem, t.valor_centavos
            FROM outbox_transferencias o
            JOIN transferencias t ON t.id = o.transferencia_id
            WHERE o.estado = 'pendente' {filtro}
            ORDER BY o.criado_em, o.transferencia_id
            LIMIT 10 FOR UPDATE OF o SKIP LOCKED
            """,
            parametros,
        ).fetchall()
        for id_evento, topico, tentativas, origem, valor in registros:
            confirmado = publicador.publicar(
                {"id": str(id_evento), "origem": origem, "valor_centavos": valor, "moeda": "BRL"},
                topico=topico,
            )
            tentativas += 1
            estado = "publicado" if confirmado else (
                "dlq" if tentativas >= MAX_TENTATIVAS else "pendente"
            )
            banco.execute(
                "UPDATE outbox_transferencias SET estado = %s, tentativas = %s "
                "WHERE transferencia_id = %s",
                (estado, tentativas, id_evento),
            )
        return len(registros)


if __name__ == "__main__":
    publicador = PublicadorTransferencias.configurar()
    if publicador is None:
        raise SystemExit("Configure BANKING_KAFKA_BOOTSTRAP_SERVERS.")
    print(f"Eventos tentados neste lote: {despachar_lote(database_url(), publicador)}")
