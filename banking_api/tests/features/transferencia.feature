# language: pt
Funcionalidade: Transferência entre contas de laboratório

  Cenário: O valor sai da origem e entra no destino
    Dado que a conta A tem 10000 centavos e a conta B tem 5000 centavos
    Quando transfiro 250 centavos da conta A para a conta B
    Então o comprovante confirma a origem, o destino e 250 centavos em BRL
    E os saldos finais são 9750 e 5250 centavos
    E o saldo total das duas contas permanece igual ao inicial
