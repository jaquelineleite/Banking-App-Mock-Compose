import os
from pathlib import Path
from uuid import UUID

import psycopg


class ContaNaoEncontrada(Exception):
    pass


class SaldoInsuficiente(Exception):
    pass


class MesmaConta(Exception):
    pass


class ChaveIdempotenciaEmConflito(Exception):
    pass


def database_url() -> str:
    dsn = os.environ.get("BANKING_DATABASE_URL")
    if not dsn:
        raise RuntimeError("Configure BANKING_DATABASE_URL para conectar ao PostgreSQL.")
    return dsn


def migrar(dsn: str) -> None:
    migrations = Path(__file__).with_name("migrations")
    with psycopg.connect(dsn) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(902173)")
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY)")
        for migration in sorted(migrations.glob("*.sql")):
            applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s", (migration.name,)
            ).fetchone()
            if applied is None:
                connection.execute(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (migration.name,)
                )


class PostgreSQLBank:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def saldo(self, conta: str) -> int:
        with psycopg.connect(self.dsn) as connection:
            row = connection.execute(
                "SELECT saldo_centavos FROM contas WHERE id = %s", (conta,)
            ).fetchone()
            if row is None:
                raise ContaNaoEncontrada
            return row[0]

    def transferir(
        self, id: UUID, origem: str, destino: str, valor: int, chave: str | None = None,
        *, topico: str | None = None,
    ) -> UUID:
        with psycopg.connect(self.dsn) as connection:
            # Depois de obter os bloqueios, a consulta da chave deve ver o último commit.
            connection.isolation_level = psycopg.IsolationLevel.READ_COMMITTED
            contas = dict(connection.execute(
                "SELECT id, saldo_centavos FROM contas "
                "WHERE id IN (%s, %s) ORDER BY id FOR UPDATE",
                (origem, destino),
            ).fetchall())
            if chave is not None:
                anterior = connection.execute(
                    "SELECT id, destino, valor_centavos FROM transferencias "
                    "WHERE origem = %s AND chave_idempotencia = %s",
                    (origem, chave),
                ).fetchone()
                if anterior is not None:
                    id_original, destino_original, valor_original = anterior
                    if (destino_original, valor_original) != (destino, valor):
                        raise ChaveIdempotenciaEmConflito
                    return id_original

            if origem not in contas or destino not in contas:
                raise ContaNaoEncontrada
            if origem == destino:
                raise MesmaConta
            if valor > contas[origem]:
                raise SaldoInsuficiente

            connection.execute(
                "UPDATE contas SET saldo_centavos = saldo_centavos - %s WHERE id = %s",
                (valor, origem),
            )
            connection.execute(
                "UPDATE contas SET saldo_centavos = saldo_centavos + %s WHERE id = %s",
                (valor, destino),
            )
            connection.execute(
                "INSERT INTO transferencias (id, origem, destino, valor_centavos, chave_idempotencia) "
                "VALUES (%s, %s, %s, %s, %s)",
                (id, origem, destino, valor, chave),
            )
            if topico is not None:
                connection.execute(
                    "INSERT INTO outbox_transferencias (transferencia_id, topico) VALUES (%s, %s)",
                    (id, topico),
                )
            return id


if __name__ == "__main__":
    migrar(database_url())
