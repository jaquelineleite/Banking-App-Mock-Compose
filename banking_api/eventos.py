import json
import logging
import os
from threading import Event
from time import monotonic

from confluent_kafka import KafkaException, Producer


logger = logging.getLogger(__name__)


class PublicadorTransferencias:
    def __init__(self, servidores: str, topico: str):
        self.topico = topico
        self.produtor = Producer({
            "bootstrap.servers": servidores,
            "enable.idempotence": True,
            "message.timeout.ms": 3000,
            "log_level": 0,
        })

    @classmethod
    def configurar(cls):
        servidores = os.environ.get("BANKING_KAFKA_BOOTSTRAP_SERVERS")
        if servidores:
            return cls(servidores, os.environ.get("BANKING_KAFKA_TOPIC", "banking.transferencias.v1"))
        return None

    def publicar(self, comprovante: dict, *, topico: str) -> bool:
        entregue = Event()
        confirmado = Event()

        def confirmar(erro, _mensagem):
            if erro is None:
                confirmado.set()
            entregue.set()

        try:
            self.produtor.produce(
                topico,
                key=comprovante["origem"],
                value=json.dumps({
                    "tipo": "transferencia.confirmada.v1",
                    "transferencia_id": comprovante["id"],
                    "valor_centavos": comprovante["valor_centavos"],
                    "moeda": comprovante["moeda"],
                }),
                on_delivery=confirmar,
            )
            prazo = monotonic() + 4
            while not entregue.is_set() and monotonic() < prazo:
                self.produtor.poll(0.05)
            if not confirmado.is_set():
                logger.warning("Publicação do evento de transferência não confirmada pelo Kafka")
        except (KafkaException, BufferError):
            logger.warning("Falha ao publicar evento de transferência no Kafka")

        return confirmado.is_set()
