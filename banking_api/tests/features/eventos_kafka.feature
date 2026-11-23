# language: pt
Funcionalidade: Eventos de transferência

  Cenário: Uma transferência confirmada gera um evento
    Dado um tópico Kafka isolado
    Quando solicito uma transferência de 250 centavos com mensageria habilitada
    Então o evento consumido corresponde ao comprovante persistido

  Cenário: Saldo insuficiente não gera evento
    Dado um tópico Kafka isolado
    Quando solicito uma transferência de 10001 centavos com mensageria habilitada
    Então a API rejeita a transferência e o tópico permanece vazio
