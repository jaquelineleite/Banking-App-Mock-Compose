import argparse
import json
import logging
from uuid import UUID

import psycopg

from banking_api.database import database_url
from banking_api.eventos import PublicadorTransferencias


logger = logging.getLogger(__name__)
MAX_TENTATIVAS = 3


def despachar_lote(
    dsn: str,
    publicador: PublicadorTransferencias,
    *,
    transferencia_id: UUID | None = None,
) -> int:
    """Tenta entregar cada registro selecionado uma vez neste lote."""
    eventos = []
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
            eventos.append({
                "evento": "outbox.tentativa",
                "transferencia_id": str(id_evento),
                "estado": estado,
                "tentativas": tentativas,
            })

    for evento in eventos:
        nivel = logging.INFO if evento["estado"] == "publicado" else logging.WARNING
        logger.log(nivel, "%s", json.dumps(evento))
    return len(eventos)


def consultar_estado(dsn: str) -> dict:
    with psycopg.connect(dsn) as banco:
        pendentes, publicados, dlq, idade = banco.execute("""
            SELECT count(*) FILTER (WHERE estado = 'pendente'),
                   count(*) FILTER (WHERE estado = 'publicado'),
                   count(*) FILTER (WHERE estado = 'dlq'),
                   EXTRACT(EPOCH FROM (now() - min(criado_em) FILTER (WHERE estado = 'pendente')))
            FROM outbox_transferencias
        """).fetchone()

    return {
        "pendentes": pendentes,
        "publicados": publicados,
        "dlq": dlq,
        "pendente_mais_antigo_segundos": max(0.0, round(float(idade), 3)) if idade is not None else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Operações da outbox bancária")
    parser.add_argument("--status", action="store_true", help="Exibe as métricas sem publicar eventos")
    if parser.parse_args().status:
        print(json.dumps(consultar_estado(database_url())))
        raise SystemExit(0)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    publicador = PublicadorTransferencias.configurar()
    if publicador is None:
        raise SystemExit("Configure BANKING_KAFKA_BOOTSTRAP_SERVERS.")
    print(f"Eventos tentados neste lote: {despachar_lote(database_url(), publicador)}")
