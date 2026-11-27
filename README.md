# Banking App Mock Compose — Engenharia de Qualidade

Projeto de portfólio em QA com automação de testes mobile, testes de API bancária e validação de eventos com Kafka. A suíte mobile usa um [aplicativo Android demonstrativo de Alexandr](https://github.com/alexandr7035/Banking-App-Mock-Compose), desenvolvido com Jetpack Compose. Os cenários de API e mensageria rodam em um laboratório separado, com dados fictícios.

## Escopo da minha contribuição

Este repositório é um fork de um aplicativo Android demonstrativo criado por Alexandr7035; o app original não é de minha autoria. Minha contribuição neste projeto está na estratégia e nas evidências de QA: automação mobile, laboratório independente de API com FastAPI e PostgreSQL, cenários de Kafka/outbox, testes de performance, CI e documentação. O laboratório de API usa dados fictícios e não está integrado ao aplicativo Android.

## O que os testes cobrem

| Área | Cobertura | Como consultar |
| --- | --- | --- |
| Mobile | Três jornadas smoke com Appium e pytest. Em 26/11/2026, 3 passaram em 82,63 s no Android 15: exibição do saldo, abertura do histórico e retorno à Home. | [Execução e limites](qa_mobile/README.md) |
| API e banco de dados | Contrato OpenAPI, autorização entre contas, valores-limite, rollback, idempotência e concorrência em transferências com FastAPI e PostgreSQL. | [Guia da API](banking_api/README.md) |
| Kafka | Contrato dos eventos, publicação, consumo, reprocessamento por offset e recuperação de eventos pendentes na outbox. | [Auditoria e evidências](docs/qa/auditoria-final.md#diagnóstico-da-mensageria) |
| Performance e CI | Teste de carga da API, verificação dos saldos ao final e relatórios no GitHub Actions. | [Execuções do GitHub Actions](https://github.com/jaquelineleite/Banking-App-Mock-Compose/actions) |
| Acessibilidade e segurança | Teste instrumentado para as abas, roteiro com TalkBack e verificações de autorização na API. | [OWASP e acessibilidade](docs/qa/owasp-e-wcag.md) |

## Como começar

- Para rodar os testes mobile, siga o [guia do Appium no Windows](qa_mobile/README.md) e o [guia de build do APK](docs/qa/android-debug-e-cache.md).
- Para preparar o ambiente com Python, Docker e PostgreSQL e rodar os testes de API, siga o [guia do laboratório](banking_api/README.md).

### Credenciais fictícias do aplicativo Android

| Campo | Valor |
| --- | --- |
| E-mail | `example@mail.com` |
| Senha | `1234567Ab` |
| Código de verificação (OTP) | `1111` |

Se o aplicativo pedir um QR Code, use o código gerado em **Profile** ou a [imagem de teste do projeto original](https://github.com/alexandr7035/Banking-App-Mock-Compose/assets/22574399/c35d4e0e-4092-4e84-9b90-e0ea843aad7d).

## Estratégia e evidências

- [Estratégia de testes](docs/qa/estrategia.md)
- [Matriz de rastreabilidade](docs/qa/matriz.md)
- [Auditoria final, evidências e limites da validação](docs/qa/auditoria-final.md)

## Sobre o aplicativo Android

O aplicativo demonstrativo simula operações bancárias como consulta de saldo, gerenciamento de cartões e histórico de transações. Ele usa Jetpack Compose e organiza o código em camadas de dados, domínio e interface. Os dados bancários são simulados na camada de dados, com persistência local para cartões e transações.

Consulte a arquitetura, a demonstração e a referência de design na [documentação do aplicativo original](https://github.com/alexandr7035/Banking-App-Mock-Compose#readme).
