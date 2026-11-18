# Automação mobile com Appium

Execute a partir da raiz do fork. A conexão usa Appium 3 com UiAutomator2.
A configuração padrão aponta para `http://127.0.0.1:4723`, UDID
`emulator-5554` e pacote `by.alexandr7035.banking.debug`.

## Windows PowerShell

Pré-requisitos: Python 3.12, Android SDK com platform-tools e AVD, Appium 3
com UiAutomator2 instalado, e APK debug instalado em emulador dedicado. Para
construir o APK com o Gradle atual, use JDK 17, SDK 35 e assinatura local
de teste configurada em `keystore.properties` (ignorado pelo Git).
No Android Studio, prepare o AVD em inglês, conclua o onboarding e entre
com o perfil fictício do [README do projeto](../README.md). Deixe a barra
de navegação disponível e a sessão desbloqueada.

Em um terminal, confirme o driver e inicie o servidor:

```powershell
appium driver list --installed
appium
```

Em outro terminal:

```powershell
adb devices
py -3.12 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r qa_mobile/requirements.txt
New-Item -ItemType Directory -Force qa_mobile/reports | Out-Null
& $python -m pytest qa_mobile/unit -q
& $python -m pytest qa_mobile/tests --collect-only -q
Invoke-RestMethod http://127.0.0.1:4723/status
& $python -m pytest qa_mobile/tests -q --html=qa_mobile/reports/mobile.html --self-contained-html
```

Se necessário, configure `$env:BANKING_ANDROID_UDID` com o serial retornado
por ADB, `$env:BANKING_APPIUM_URL` com a URL do servidor e
`$env:BANKING_APP_PACKAGE` com o pacote instalado, antes de rodar o pytest.
Essas variáveis são opcionais. A seleção usa o UDID explícito e cada teste
cria e encerra sua própria sessão. Rode em série, pois o cache e a
autenticação do APK são reaproveitados.

A coleta valida descoberta/importação dos cenários. A execução mobile
depende da resposta do servidor e do APK. O rótulo de saldo e os nomes
dos filtros comprovam presença na hierarquia da UI. Validação numérica,
filtragem de lançamentos e reset de dados são etapas futuras.

## Evidências

Gere apenas relatórios com massa fictícia e anote commit, versão do APK,
Appium, UiAutomator2, API do Android, locale e resultado. Os arquivos em
`qa_mobile/reports/` ficam fora do Git.

[Auditoria e estratégia](../docs/qa/estrategia.md) · [Matriz de rastreabilidade](../docs/qa/matriz.md)
