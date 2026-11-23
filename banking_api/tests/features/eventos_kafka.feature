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

  Cenário: O reenvio idempotente não duplica o evento
    Dado um tópico Kafka isolado
    Quando reenvio uma transferência com a mesma chave de idempotência
    Então o comprovante é reutilizado e o tópico contém apenas um evento

  Cenário: Eventos da mesma conta mantêm a ordem de publicação na partição
    Dado um tópico Kafka isolado
    Quando confirmo três transferências sequenciais da mesma conta
    Então os eventos são consumidos na ordem dos comprovantes

  Cenário: Um consumidor reiniciado pode reler um evento pelo offset
    Dado um tópico Kafka isolado
    Quando solicito uma transferência de 250 centavos com mensageria habilitada
    Então outro consumidor consegue reler o evento sem alterar os saldos
