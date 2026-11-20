import os
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from fastapi.testclient import TestClient

from banking_api.database import migrar
from banking_api.main import create_app
from banking_api.tests.api_client import BankingApiClient


@pytest.fixture
def tokens(monkeypatch):
    tokens = {"conta-a": "a" * 32, "conta-b": "b" * 32}
    monkeypatch.setenv("BANKING_LAB_TOKEN_A", tokens["conta-a"])
    monkeypatch.setenv("BANKING_LAB_TOKEN_B", tokens["conta-b"])
    return tokens


@pytest.fixture
def postgres_dsn(monkeypatch):
    base_dsn = os.environ.get("BANKING_TEST_DATABASE_URL")
    if not base_dsn:
        pytest.fail("Configure BANKING_TEST_DATABASE_URL com um PostgreSQL de teste.")
    schema = f"test_{uuid4().hex}"
    schema_id = sql.Identifier(schema)
    with psycopg.connect(base_dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema_id))
        try:
            dsn = make_conninfo(base_dsn, options=f"-csearch_path={schema}")
            migrar(dsn)
            monkeypatch.setenv("BANKING_DATABASE_URL", dsn)
            yield dsn
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema_id))


@pytest.fixture
def client(tokens, postgres_dsn):
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def api(client):
    return BankingApiClient(client)
