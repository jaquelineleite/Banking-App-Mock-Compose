# Casos negativos e de borda no envio local

O caso de uso rejeita valores menores ou iguais a zero e valores não finitos
antes de encaminhar o envio para agendamento. O repositório de contas
repete a validação antes de alterar o saldo persistido, inclusive quando
o processamento chega direto à camada de dados. A mensagem usa o erro de
validação existente.

A revisão encontrou uma lacuna no comportamento anterior. Como o repositório
subtraía o valor do saldo, um valor negativo podia aumentar o saldo. A regra
deste PR exige um valor positivo e finito para o envio simulado.

| Camada | Cenário | Verificação |
| --- | --- | --- |
| Caso de uso | Zero, negativo, NaN e infinito | Retorna erro de validação e nenhuma submissão chega ao repositório de transações. |
| Caso de uso | Valor positivo válido | Encaminha uma submissão SEND com o valor, cartão e contato esperados. |
| Room e repositório | Envio acima do saldo | Retorna saldo insuficiente e preserva o cartão de origem. |
| Room e repositório | Cartão de origem removido | Retorna cartão inexistente e preserva os demais cartões. |
| Room e repositório | Envio igual ao saldo | Persiste saldo zero no cartão de origem. |
| Room e repositório | Zero, negativo, NaN e infinito | Retorna erro de validação e preserva o cartão de origem para cada entrada. |

Os testes instrumentados usam um banco Room em memória novo por teste.
Os testes unitários usam um repositório de transações que registra as
chamadas para verificar o limite do caso de uso. O registro do histórico
após o WorkManager processar uma operação continua pendente. Esta cobertura
também não executa a interface Compose nem altera a representação monetária
em Float, as regras de recarga ou os limites do seletor de valor.

## Execução no Windows

Com JDK 17, SDK 35 e emulador ou dispositivo conectado, execute na raiz:

```powershell
adb devices
.\gradlew.bat :app:testDebugUnitTest
.\gradlew.bat :app:connectedDebugAndroidTest "-Pandroid.testInstrumentationRunnerArguments.class=by.alexandr7035.banking.data.BankingCacheIntegrationTest"
```

A configuração de build e assinatura está no [guia de Android](android-debug-e-cache.md).

## Evidências de execução

Build em Linux com JDK 17, Android SDK 35 e Gradle 8.11.1. O comando
`gradle :app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest`
concluiu em 47 s e gerou os dois APKs. Os três testes unitários passaram
(dois novos e um existente).

AndroidJUnitRunner no emulador Android API 30 aprovou 9 testes em 1,75 s,
incluindo os quatro novos cenários de integração com Room. Após instalar
os APKs, o resultado da suíte instrumentada foi:

```text
adb shell am instrument -w -r by.alexandr7035.banking.debug.test/androidx.test.runner.AndroidJUnitRunner

Time: 1.75

OK (9 tests)
```
