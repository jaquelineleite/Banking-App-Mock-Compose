# language: pt
Funcionalidade: Reenvio seguro de transferências

  Cenário: A resposta pode se perder depois da confirmação no banco
    Dado que a resposta da primeira transferência foi perdida após a confirmação
    Quando reenvio a transferência com a mesma chave e os mesmos dados
    Então recebo o comprovante original
    E o PostgreSQL registra um único débito, crédito e comprovante

  Cenário: Uma chave usada não pode confirmar outro valor
    Dado que uma transferência foi confirmada com uma chave
    Quando reenvio a transferência com a mesma chave e um valor diferente
    Então a API informa conflito de idempotência
    E o PostgreSQL registra um único débito, crédito e comprovante
