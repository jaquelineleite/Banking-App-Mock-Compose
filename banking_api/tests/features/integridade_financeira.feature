# language: pt
Funcionalidade: Integridade da transferência no PostgreSQL

  Cenário: Débito, crédito e comprovante são persistidos juntos
    Dado que o banco tem as duas contas com os saldos iniciais
    Quando solicito uma transferência de 250 centavos
    Então a API confirma a transferência
    E o banco registra um débito de 250 centavos, o crédito e o comprovante

  Cenário: Saldo insuficiente preserva as contas
    Dado que o banco tem as duas contas com os saldos iniciais
    Quando solicito uma transferência de 10001 centavos
    Então a API rejeita a transferência por saldo insuficiente
    E o banco mantém os dois saldos e nenhum comprovante

  Cenário: Uma falha após o débito desfaz a transferência
    Dado que o banco tem as duas contas com os saldos iniciais
    E que o PostgreSQL interrompe o crédito após observar o débito
    Quando solicito uma transferência de 250 centavos
    Então a API informa uma falha de armazenamento
    E o banco registra que a falha ocorreu após o débito
    E o banco mantém os dois saldos e nenhum comprovante
