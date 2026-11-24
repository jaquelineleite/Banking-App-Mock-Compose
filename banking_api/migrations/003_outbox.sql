CREATE TABLE outbox_transferencias (
    transferencia_id uuid PRIMARY KEY REFERENCES transferencias(id),
    topico text NOT NULL,
    tentativas integer NOT NULL DEFAULT 0 CHECK (tentativas BETWEEN 0 AND 3),
    estado text NOT NULL DEFAULT 'pendente' CHECK (estado IN ('pendente', 'publicado', 'dlq')),
    criado_em timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX outbox_pendentes_idx ON outbox_transferencias (criado_em, transferencia_id)
WHERE estado = 'pendente';
