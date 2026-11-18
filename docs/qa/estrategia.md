# Estratégia de Quality Engineering

## Auditoria da baseline

Fork `jaquelineleite/Banking-App-Mock-Compose`, branch `master`, commit
`6e96757ae76a17cababc0ad9803721b7ddaa27f0`. Os PRs #1 (smoke Appium)
e #2 (gitignore) constavam como integrados na auditoria. As duas branches
de origem ainda existiam.

- O Android usa um módulo `app`, Kotlin, Jetpack Compose e navegação AndroidX.
  A UI trabalha com ViewModels e casos de uso. Koin liga as interfaces do
  domínio a repositórios simulados na camada de dados.
- Dashboard, saldo agregado de cartões, histórico paginado e filtros estão
  implementados. Há cartões, contatos, poupanças, login e OTP simulados, além
  de PIN e biometria locais. O envio e a recarga são simulações. O envio
  reduz o saldo do cartão local e registra uma transação. O código auditado
  não credita uma segunda conta. O processamento `RECEIVE` no worker é um
  `TODO()`. O filtro `Request` visível não comprova processamento de recebimento.
- Room 2.7.1 mantém cartões e transações em SQLite. WorkManager 2.10.1
  processa envio/recarga após atraso simulado e exige conectividade.
  Não há serviço HTTP bancário, autenticação por token, PostgreSQL, Kafka
  ou pipeline de QA versionado nessa baseline.
- Gradle Wrapper 8.11.1, AGP 8.9.3, Kotlin 2.1.20, Compose BOM 2025.05.01,
  bytecode Java 17, compile SDK 35, target SDK 34 e min SDK 23. O módulo
  abre `keystore.properties` incondicionalmente e usa assinatura personalizada
  também no debug. O checkout não traz esse arquivo. Um APK de teste já
  instalado permite rodar Appium sem reconstruir o app.
- O PR #1 adicionou dois Page Objects e dois testes com uma fixture no próprio
  arquivo. O saldo era constatado pelo rótulo e o histórico pela presença dos
  filtros. A execução histórica registrada no PR foi de 2 aprovados em 18,22 s.
  Os exemplos nativos de JUnit/instrumentação existentes não formam cobertura
  de regras financeiras.
- Neste ambiente há Python 3.12.14 e JDK 21. ADB, emulador, Appium CLI e Docker
  não estão no PATH, `/dev/kvm` não está presente e a porta local 4723 recusou
  conexão. O APK e a execução instrumentada ficaram sem validação.

## Onde testar

| Camada | Decisão | Evidência esperada |
| --- | --- | --- |
| Unidade | Kotlin para regras e estados do app. pytest para configuração da suíte e, futuramente, regras do serviço Python. | Testes com entradas e resultados explícitos, sem emulador. |
| Mobile | Appium para poucos fluxos que dependem da UI. Usar esperas explícitas e preferir IDs semânticos após validar a árvore Compose. | HTML e identificação do APK, dispositivo, locale e commit. |
| Integração Android | Room instrumentado e WorkManager de teste para saldo, estado e atualização do histórico. | Estado persistido antes e depois; confirmação do status final. |
| Serviço | FastAPI e OpenAPI em laboratório próprio. Validar regras por HTTP e persistência com PostgreSQL real para os casos transacionais. | Resposta, estado persistido e identificadores sintéticos correlacionados. |
| Mensageria | Broker Kafka real em Docker para validar entrega, offsets, contratos e replay. Avaliar outbox transacional e consumidor idempotente juntos. | Evento por ID/chave, offset e efeito persistido por correlação. |

O laboratório de API e a integração do Android com ele exigem decisões
independentes. O PR de FastAPI deve começar com rotas de contas e envio,
contrato monetário e regras explícitas. Adotar unidades mínimas inteiras ou
decimal de escala fixa antes de liberar movimentação persistente. Definir a
semântica de arredondamento, a política de limites, o status de conta e o
vínculo de autorização no contrato. Para um envio concluído, conferir débito,
crédito, conservação do total, histórico e atomicidade. Para rejeições,
conferir ausência de alterações de negócio.

## Massa, relógio e execução

- O smoke atual usa APK de teste, UI em inglês e perfil local já preparado
  em AVD dedicado. A sessão é descartada por teste. `noReset=True` preserva
  autenticação e cache, portanto essa suíte deve rodar em série e seus três
  testes de navegação não gravam movimentações.
- Antes dos testes que alteram estado, criar bootstrap de perfil/cartões/
  transações sintéticos e reset repetível por caso ou snapshot reproduzível.
  Verificar cada cenário sozinho e com ordem invertida. Injetar relógio e
  dispatcher nos componentes temporais e aguardar estado observável com prazo.
- Para paralelismo mobile, reservar AVD, UDID, porta UiAutomator2 e massa
  exclusivos por worker. Para concorrência financeira, rodar clientes
  independentes sincronizados por barreira contra a mesma conta em PostgreSQL
  real e reconciliar saldos e registros depois.
- Usar identificadores sintéticos por teste e processar retries com limites
  definidos. Registrar métricas de instabilidade sem ocultar falhas com reruns.

## Riscos e critérios de aceite

| Risco | Prioridade | Controle e oráculo |
| --- | --- | --- |
| Centavos divergentes com `Float` em `MoneyAmount` | Crítica | Testes de precisão e escala; comparar valores exatos na futura API e no banco. |
| Atualizações concorrentes gravarem saldo obsoleto; débito e status são atualizações distintas no mock | Crítica | Reproduzir concorrência controlada na camada de dados, verificar saldo final e definir transação atômica e política de conflito para o serviço. Análise estática ainda sem reprodução. |
| Retry após resposta perdida gerar débito duplo | Crítica | Chave por cliente/operação, retenção definida, impressão do payload e unicidade persistida; comparar ID, saldo e contagem de movimentações. |
| Conta fora do escopo ou dados sensíveis em logs | Alta | Validar autorização por conta e inspecionar logs de teste com identificadores sintéticos; nunca publicar credenciais, dumps ou conteúdo bancário real. |
| Evento persistido sem publicação ou efeito duplicado por replay | Alta | Avaliar outbox na mesma transação do envio; reiniciar publicador e consumidor e reconciliar estado, evento e efeito final. |
| Smoke instável por UI textual, onboarding e cache compartilhado | Alta | Fixar locale e perfil, usar esperas explícitas e medir falhas repetidas. |
| Checkout limpo não gera APK sem assinatura local | Alta | Validar build debug em ambiente limpo com estratégia de assinatura local antes de exigir mobile na CI. |

Aceite desta etapa: rastreabilidade com distinção entre comportamento local,
teste coletado e integração planejada. A configuração deve preservar os
defaults históricos, selecionar o emulador pelo UDID e ser verificável sem
Appium. As três jornadas precisam executar no Windows para validar a
navegação e os seletores em runtime antes de aprovar a revisão mobile.

## Estimativas restantes

Horas de trabalho após este PR. As fases de infraestrutura supõem um
ambiente com Docker e uma imagem Android disponíveis.

| PR planejado | Entrega e dependência | Horas restantes |
| --- | --- | --- |
| #3 | Estratégia e fixture entregues para revisão. Validar os três casos no Windows. | 0,5–1 |
| #4 | Reproduzir build debug e ampliar positivos, filtros e cartões. | 4–6 |
| #5 | Negativos e bordas locais com dados sintéticos. | 4–6 |
| #6 | Perfil/reset, relógio/dispatcher e execução independente da ordem. | 4–6 |
| #7 | FastAPI, OpenAPI e decisões sobre dinheiro e autorização. | 6–8 |
| #8 | Contratos, contas e transferências por HTTP, inicialmente com persistência limitada ao que existir. | 4–6 |
| #9 | Negativos de API, limites, precisão e timeout de transporte. | 4–6 |
| #10 | PostgreSQL, migrações, atomicidade e reconciliação. | 6–8 |
| #11 | Idempotência persistida e retry após resposta perdida. | 5–7 |
| #12 | Corrida por saldo, sessões paralelas e mesma chave simultânea. | 5–8 |
| #13 | Kafka em Docker e decisão de outbox com teste banco/broker. | 7–10 |
| #14 | Contratos, partições, duplicidade e reprocessamento. | 6–9 |
| #15 | Falhas, retries limitados, DLQ e recuperação. | 5–8 |
| #16 | Carga, estresse, SLO de latência e throughput. | 4–6 |
| #17 | CI, jobs por camada, artefatos e gates reproduzíveis. | 5–8 |
| #18 | Observabilidade, evidências rastreáveis e revisão defensiva. | 4–6 |

[Matriz de rastreabilidade](matriz.md) · [Validação desta etapa](validacao.md) · [Execução no Windows](../../qa_mobile/README.md)
