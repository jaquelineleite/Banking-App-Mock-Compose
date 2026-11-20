CREATE TABLE IF NOT EXISTS contas (
    id text PRIMARY KEY,
    saldo_centavos bigint NOT NULL CHECK (saldo_centavos >= 0)
);

CREATE TABLE IF NOT EXISTS transferencias (
    id uuid PRIMARY KEY,
    origem text NOT NULL REFERENCES contas(id),
    destino text NOT NULL REFERENCES contas(id),
    valor_centavos bigint NOT NULL CHECK (valor_centavos BETWEEN 1 AND 1000000000),
    CHECK (origem <> destino)
);

INSERT INTO contas (id, saldo_centavos)
VALUES ('conta-a', 10000), ('conta-b', 5000)
ON CONFLICT (id) DO NOTHING;
