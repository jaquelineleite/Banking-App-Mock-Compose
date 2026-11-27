# Automação mobile com Appium

Execute a partir da raiz do fork. A conexão usa Appium 3 com UiAutomator2.
A configuração padrão aponta para `http://127.0.0.1:4723`, UDID
`emulator-5554` e pacote `by.alexandr7035.banking.debug`.

## Windows PowerShell

Pré-requisitos: Python 3.12, Android SDK com platform-tools e AVD, Appium 3
com UiAutomator2 instalado, e APK debug instalado em emulador dedicado. Para
construir o APK debug, use JDK 17 e SDK 35. Consulte o
[guia de build Android](../docs/qa/android-debug-e-cache.md).
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
As variáveis são opcionais. Use um AVD exclusivo para a suíte e rode em
série. Cada teste abre e encerra sua própria sessão e volta para Home,
aguardando o saldo antes de iniciar o cenário. O perfil autenticado e o
cache do AVD são preservados. A suíte atual só consulta saldo e histórico.

As esperas de interação e de visibilidade usam 20 segundos por condição.
Para diagnóstico em um emulador lento, use por exemplo
`$env:BANKING_UI_WAIT_SECONDS = "40"` antes de rodar. Um erro durante a
preparação do Dashboard aponta para os pré-requisitos de idioma, onboarding
e desbloqueio.

A coleta valida descoberta/importação dos cenários. A execução mobile
depende da resposta do servidor e do APK. O rótulo de saldo e os nomes
dos filtros comprovam presença na hierarquia da UI. Validação numérica,
filtragem de lançamentos e reset de dados persistidos são etapas futuras.

## Evidências

Gere apenas relatórios com massa fictícia e anote commit, versão do APK,
Appium, UiAutomator2, API do Android, locale e resultado. Os arquivos em
`qa_mobile/reports/` ficam fora do Git.

[Auditoria e estratégia](../docs/qa/estrategia.md) · [Matriz de rastreabilidade](../docs/qa/matriz.md)


## Validação inicial da preparação dos testes

Em 18/11/2026, `python -m pytest qa_mobile/unit -q` aprovou 8 casos e
`python -m pytest qa_mobile/tests --collect-only -q` coletou os 3 cenários
Appium. Naquele ambiente, não havia ADB no PATH, o emulador não estava
disponível e a porta local 4723 recusou a conexão. A execução posterior em
Android está registrada acima. O commit e a versão do APK dessa execução
precisam ser capturados em uma próxima evidência para permitir reprodução
exata.
