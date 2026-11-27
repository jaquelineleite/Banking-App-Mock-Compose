# Auditoria final de Quality Engineering

| Área | Cobertura e evidência | Limite da validação |
| --- | --- | --- |
| API e segurança | Contrato OpenAPI, valores-limite, rejeições e autorização entre contas fictícias. [Guia da API](../../banking_api/README.md) · [OWASP e acessibilidade](owasp-e-wcag.md) | A segurança cobre o controle de acesso aos objetos do cenário de laboratório. |
| PostgreSQL | Testes BDD verificam commit, rollback, saldos, idempotência e disputa de saldo com bloqueio de linhas. [Execução de referência](https://github.com/jaquelineleite/Banking-App-Mock-Compose/actions/runs/45415727644) | Os cenários de concorrência exercitam duas chamadas. |
| Kafka e resiliência | Contrato JSON, publicação, consumo, replay por offset, recuperação da outbox e retenção após três falhas. [Integração de resiliência](https://github.com/jaquelineleite/Banking-App-Mock-Compose/actions/runs/45310160597) | O despacho em lote é acionado por comando. A confirmação Kafka seguida de falha no commit da outbox pode causar duplicidade. |
| Performance | 160 requisições HTTP com quatro clientes e checagem dos saldos finais. [Evidência JSON e JUnit](https://github.com/jaquelineleite/Banking-App-Mock-Compose/actions/runs/45315208834/artifacts/14884947887) | Medição de laboratório com Kafka desabilitado. |
| CI/CD | O check **Quality Gate da API** consolida 65 casos de regressão e um de performance na execução de referência. [CI e artefatos](https://github.com/jaquelineleite/Banking-App-Mock-Compose/actions/runs/45415727644) | A obrigatoriedade para merge depende da configuração da regra da branch. |
| Android e Appium | Oito testes unitários de configuração passaram na auditoria. Em 26/11/2026, três testes de interface passaram em 82,63 s no Android 15: saldo visível, abertura do Histórico e retorno à Home. [Guia e limites](../../qa_mobile/README.md) | É um smoke de navegação: confirma rótulos e fluxo, não o valor numérico do saldo, a filtragem real ou a persistência. O commit e a versão do APK usados nessa execução não foram registrados. |
| Acessibilidade | O projeto tem teste instrumentado de nome, papel e seleção das abas Compose, alinhado ao critério 4.1.2. [Comando e roteiro de TalkBack](owasp-e-wcag.md) | A execução instrumentada e o roteiro manual com TalkBack aguardam validação em dispositivo. |

## Diagnóstico da mensageria

Use o ID do comprovante para localizar as tentativas nos logs da outbox
e o evento consumido. Compare o último estado registrado com a saída de
`python -m banking_api.outbox --status` para avaliar o volume e a idade
dos pendentes. O BDD valida a transição pendente para publicado e o
encaminhamento à DLQ. O painel de monitoramento e os alertas operacionais
dependem do ambiente onde a aplicação for implantada.
