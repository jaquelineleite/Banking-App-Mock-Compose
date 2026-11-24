"""Carga HTTP de laboratório, executada explicitamente pelo caminho do arquivo."""

import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, socket
from threading import Event, Thread
from time import monotonic, perf_counter

import psycopg
import pytest
import uvicorn
from httpx2 import Client, RequestError

from banking_api.main import create_app
from banking_api.tests.api_client import BankingApiClient


CLIENTES = 4
REQUISICOES_POR_CLIENTE = 20


@pytest.fixture
def servidor_http(postgres_dsn, tokens, monkeypatch):
    monkeypatch.delenv("BANKING_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    servidor = uvicorn.Server(uvicorn.Config(create_app(), log_level="warning"))
    with socket(AF_INET, SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        porta = listener.getsockname()[1]
        thread = Thread(target=servidor.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            prazo = monotonic() + 10
            espera = Event()
            while not servidor.started and thread.is_alive() and monotonic() < prazo:
                espera.wait(0.02)
            assert servidor.started, "O servidor HTTP não iniciou no prazo"
            yield f"http://127.0.0.1:{porta}"
        finally:
            servidor.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "O servidor HTTP não encerrou no prazo"


def executar_carga(url, token, operacao, status_esperado):
    def executar_cliente(_):
        with Client(base_url=url, timeout=5, trust_env=False) as cliente:
            api = BankingApiClient(cliente)
            medidas = []
            for _ in range(REQUISICOES_POR_CLIENTE):
                inicio = perf_counter()
                try:
                    resposta = operacao(api, token)
                    status = str(resposta.status_code)
                except RequestError as erro:
                    status = type(erro).__name__
                medidas.append(((perf_counter() - inicio) * 1000, status))
            return medidas

    inicio = perf_counter()
    with ThreadPoolExecutor(max_workers=CLIENTES) as executor:
        medidas = [medida for lote in executor.map(executar_cliente, range(CLIENTES))
                   for medida in lote]
    duracao = perf_counter() - inicio
    latencias = sorted(latencia for latencia, _ in medidas)
    status = Counter(status for _, status in medidas)
    return {
        "requisicoes": len(medidas),
        "conexoes_concorrentes": CLIENTES,
        "latencia_p95_ms": round(latencias[ceil(len(latencias) * 0.95) - 1], 2),
        "requisicoes_por_segundo": round(len(medidas) / duracao, 2),
        "taxa_erro_percentual": round(100 * (1 - status[str(status_esperado)] / len(medidas)), 2),
        "resultados": dict(status),
    }


def test_carga_controlada_da_api(servidor_http, tokens, postgres_dsn):
    token = tokens["conta-a"]
    consultas = executar_carga(servidor_http, token, lambda api, t: api.consultar_conta("conta-a", t), 200)
    dados = {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 1}
    transferencias = executar_carga(servidor_http, token, lambda api, t: api.transferir(dados, t), 201)

    relatorio = {"consulta_conta": consultas, "transferencia": transferencias}
    saida = Path(os.environ.get("BANKING_PERFORMANCE_REPORT", "reports/banking-api-performance.json"))
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(relatorio, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(relatorio, indent=2))

    assert consultas["taxa_erro_percentual"] == transferencias["taxa_erro_percentual"] == 0
    total = CLIENTES * REQUISICOES_POR_CLIENTE
    with psycopg.connect(postgres_dsn) as banco:
        assert dict(banco.execute("SELECT id, saldo_centavos FROM contas")) == {
            "conta-a": 10_000 - total,
            "conta-b": 5_000 + total,
        }
        assert banco.execute("SELECT count(*), sum(valor_centavos) FROM transferencias").fetchone() == (
            total, total,
        )
