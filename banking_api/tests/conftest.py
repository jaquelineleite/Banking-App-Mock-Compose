import pytest
from fastapi.testclient import TestClient

from banking_api.main import create_app
from banking_api.tests.api_client import BankingApiClient


@pytest.fixture
def tokens(monkeypatch):
    tokens = {"conta-a": "a" * 32, "conta-b": "b" * 32}
    monkeypatch.setenv("BANKING_LAB_TOKEN_A", tokens["conta-a"])
    monkeypatch.setenv("BANKING_LAB_TOKEN_B", tokens["conta-b"])
    return tokens


@pytest.fixture
def client(tokens):
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def api(client):
    return BankingApiClient(client)
