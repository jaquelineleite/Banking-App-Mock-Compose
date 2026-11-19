from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread

import pytest
from httpx2 import Client, ReadTimeout, Timeout

from banking_api.tests.api_client import BankingApiClient


def test_timeout_de_leitura_aguardando_resposta_da_transferencia():
    requisicao_recebida = Event()
    liberar_resposta = Event()

    class RespostaRetida(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/transferencias":
                self.send_error(404)
                return
            self.rfile.read(int(self.headers["Content-Length"]))
            requisicao_recebida.set()
            if liberar_resposta.wait(timeout=5):
                try:
                    self.send_response(204)
                    self.end_headers()
                except OSError:
                    # O cliente pode ter fechado a conexão após o timeout.
                    pass

    with HTTPServer(("127.0.0.1", 0), RespostaRetida) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        try:
            with Client(
                base_url=f"http://127.0.0.1:{server.server_port}",
                timeout=Timeout(5.0, read=0.5),
                trust_env=False,
            ) as client:
                api = BankingApiClient(client)
                with pytest.raises(ReadTimeout):
                    api.transferir(
                        {"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250},
                        token=None,
                    )
                assert requisicao_recebida.is_set()
        finally:
            liberar_resposta.set()
            server.shutdown()
            thread.join()
