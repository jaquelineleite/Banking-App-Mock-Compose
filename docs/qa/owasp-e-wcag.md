# OWASP e acessibilidade no Banking App

| Referência | Pergunta para lembrar | Evidência no projeto |
| --- | --- | --- |
| OWASP API1:2023 | A API confirma que o titular tem acesso à conta solicitada? | Testes de autorização com as duas contas fictícias, conferindo listagem, rejeição de consulta e transferência, e saldos preservados. |
| WCAG 4.1.2, com orientação WCAG2ICT | A tecnologia assistiva consegue identificar o nome, a função e o estado do controle? | Teste instrumentado da semântica Compose de duas abas do componente reutilizado pelo app. Confere rótulos, papel de aba e mudança da seleção. |

## Conferência no Android

No Windows, com o emulador conectado, rode:

```powershell
.\gradlew.bat :app:connectedDebugAndroidTest "-Pandroid.testInstrumentationRunnerArguments.class=by.alexandr7035.banking.ui.BottomNavigationAccessibilityTest"
```

No app, com TalkBack ativo, navegue por Home e History. Confirme se cada
aba é identificável pelo nome, se a seleção é anunciada e se a navegação
continua utilizável ao mudar de tela. Registre a versão do Android, do
TalkBack e os anúncios observados. O teste Compose cobre o componente
isolado. A execução no dispositivo e a conferência com TalkBack estão
pendentes. A unidade de cobertura é um critério aplicado a um componente.

## Execução da API

`python -m pytest banking_api/tests -q` executa a suíte de API. A execução
local aprovou 46 casos, incluindo os dois novos de autorização.

## Referências

- [OWASP API1:2023 — Broken Object Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
- [W3C — Nome, função e valor](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value)
- [W3C — Orientação para aplicar WCAG a software não web (WCAG2ICT)](https://www.w3.org/TR/wcag2ict-22/)
