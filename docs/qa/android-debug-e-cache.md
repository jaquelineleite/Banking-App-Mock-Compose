# Build debug e integração Android com Room

O projeto versiona `android.useAndroidX=true` para resolver as dependências
AndroidX em um checkout limpo. O Gradle usa heap de 2 GB para a etapa de
DEX. O build usa a assinatura debug padrão do
Android Gradle Plugin quando `keystore.properties` estiver ausente. O pacote continua
`by.alexandr7035.banking.debug`. Quando o arquivo local estiver presente,
debug e release usam a assinatura configurada, como antes. Os campos
obrigatórios são `keyAlias`, `keyPassword`, `storeFile` e `storePassword`.
A configuração rejeita campos ausentes sem imprimir valores.
O empacotamento release exige o arquivo de assinatura.

Use um AVD dedicado para os testes. Um APK debug instalado com outra chave
não pode ser atualizado diretamente com a chave debug padrão. Nesse caso,
use um AVD limpo ou preserve a assinatura original por configuração local.

## Cobertura

| Cenário | Oráculo |
| --- | --- |
| Saldo agregado e consulta de cartão | Dois cartões sintéticos somam USD 40,00. O cartão B retorna USD 14,50. |
| Histórico sem filtro | A página retorna os IDs em ordem decrescente. |
| Histórico por tipo | SEND, RECEIVE e TOP_UP retornam exatamente os IDs semeados para o filtro selecionado. |
| Filtro sem resultados | A página tem lista vazia e próxima chave ausente. |

Cada teste abre e fecha seu próprio banco Room em memória, usando o DAO,
o conversor e a fonte de paginação do aplicativo. Os dados incluem tipos,
datas e valores fixos. O registro RECEIVE é inserido no banco para validar a
consulta, enquanto o processamento de recebimento continua fora da cobertura.
A leitura do saldo aguarda a primeira emissão com prazo explícito.
A interface Compose, a execução do WorkManager e os centavos sujeitos a
arredondamento permanecem fora desses quatro testes.

## Execução no Windows

Use JDK 17, Android SDK 35, platform-tools e um emulador ou dispositivo
Android conectado. Em um checkout novo, ajuste o SDK pelo Android Studio
ou pela configuração local do projeto e rode na raiz:

```powershell
adb devices
.\gradlew.bat :app:assembleDebug :app:assembleDebugAndroidTest
.\gradlew.bat :app:connectedDebugAndroidTest "-Pandroid.testInstrumentationRunnerArguments.class=by.alexandr7035.banking.data.BankingCacheIntegrationTest"
```

O APK fica em `app/build/outputs/apk/debug/`. O relatório instrumentado fica
em `app/build/reports/androidTests/connected/`. Na revisão, registre o commit,
o resultado do build, o dispositivo e os quatro resultados instrumentados.

## Evidências

Validação em Linux com JDK 17, SDK 35 e Gradle 8.11.1, sem
`keystore.properties` no checkout.

| Verificação | Resultado observado |
| --- | --- |
| `gradle :app:assembleDebug :app:assembleDebugAndroidTest :app:testDebugUnitTest` | Build concluído em 2 min e 6 s. Os dois APKs foram gerados e o teste unitário já existente passou (1/1). |
| `aapt dump badging` | Pacotes `by.alexandr7035.banking.debug` e `by.alexandr7035.banking.debug.test` confirmados nos APKs. |
| `gradle :app:signingReport` | Configuração `debug` selecionada para app e testes instrumentados na ausência de assinatura local. |
| `gradle :app:assembleRelease :app:bundleRelease --dry-run` | A proteção de assinatura apareceu no grafo antes dos empacotamentos APK e AAB. |
| `gradle :app:requireReleaseSigning` | Falha esperada, com mensagem solicitando `keystore.properties`. |
| AndroidJUnitRunner em AVD x86_64, API 30 | 5 aprovados em 1,111 s. Inclui os quatro testes novos e o smoke existente de pacote Android. |

O runner foi chamado após instalar os dois APKs no AVD:

```text
adb shell am instrument -w -r by.alexandr7035.banking.debug.test/androidx.test.runner.AndroidJUnitRunner

Time: 1.111

OK (5 tests)
```

O smoke Appium do PR #3 tem execução própria e fica fora deste resultado.
