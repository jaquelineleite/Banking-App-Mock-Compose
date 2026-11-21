ALTER TABLE transferencias
    ADD COLUMN chave_idempotencia varchar(128),
    ADD CONSTRAINT transferencias_origem_chave_unique
        UNIQUE (origem, chave_idempotencia);
