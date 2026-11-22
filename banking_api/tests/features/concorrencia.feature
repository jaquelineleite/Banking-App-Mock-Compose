# language: pt
Funcionalidade: Transferências concorrentes

  Cenário: Duas chamadas simultâneas repetem a mesma operação
    Quando duas transferências de 6000 centavos disputam a conta com a mesma chave
    Então as duas respostas devolvem o mesmo comprovante
    E o banco registra um único débito e um único crédito

  Cenário: Duas operações simultâneas disputam saldo para apenas uma
    Quando duas transferências de 6000 centavos disputam a conta com chaves distintas
    Então apenas uma transferência é aprovada e a outra é rejeitada por saldo insuficiente
    E o banco registra um único débito e um único crédito
