# Matriz de rastreabilidade

**Coletado** indica que o pytest encontrou o teste neste PR. Os três testes
mobile aguardam execução em Android. Os demais itens estão **planejados**.

| ID | Requisito ou condição | Verificação esperada | Camada / PR planejado | Estado |
| --- | --- | --- | --- | --- |
| MOB-01 | Dashboard | Rótulo My Balance presente e pacote esperado. | Appium / #3 | Coletado |
| MOB-02 | Entrada no Histórico | Filtros All, Send, Request e Top up presentes. | Appium / #3 | Coletado |
| MOB-03 | Retorno do Histórico | Após visitar o Histórico, Home volta a mostrar o rótulo do saldo. | Appium / #3 | Coletado |
| MOB-04 | Valor, filtros e lista de cartões | Saldo coincide com a massa, filtros retornam somente o tipo escolhido e cartão consultado corresponde ao cadastro local. Incluir filtro sem resultados. | Appium e Room / #4 | Planejado |
| MOB-05 | Envio local e recarga | Variação do saldo do cartão e item no histórico com status final coerente. | Appium e WorkManager / #4 | Planejado |
| MOB-06 | Saldo insuficiente, cartão removido e valores de borda | Exercitar zero, negativo, mínimo da UI e saldo exato. Comparar estado antes/depois e mensagens observáveis. | Kotlin, Room e Appium / #5 | Planejado |
| DET-01 | Massa, relógio e ordem | Reset reproduzível, casos isolados em ordem invertida e prazos explícitos para o worker. | Kotlin, Room, Appium / #6 | Planejado |
| API-01 | Contas, transferência, histórico e contrato | Resposta conforme OpenAPI; conferir débito, crédito e histórico conforme a persistência disponível. | HTTP / #7–#8 | Planejado |
| API-02 | Autorização, token inválido ou expirado | Recusar operações fora do escopo da conta e autenticação inválida; conferir integridade e ausência de exposição nos logs. | HTTP / #7–#9, #18 | Planejado |
| API-03 | Conta inexistente/bloqueada, saldo insuficiente e payload incompleto | Erros estáveis e nenhum efeito financeiro. | HTTP / #9 | Planejado |
| API-04 | Zero, negativo, mínimo, saldo exato, limite e escala | Exercitar limite −1, limite e limite +1 em unidades mínimas; validar precisão e política de arredondamento. | Unidade e HTTP / #9 | Planejado |
| API-05 | Timeout e rate limit | Transporte encerra dentro do prazo; limite de requisições retorna a resposta contratada. | HTTP / #9, #16 | Planejado |
| DB-01 | Atomicidade e durabilidade | Induzir falha entre efeitos da transferência; conferir rollback integral, histórico consistente e persistência após reinício. | PostgreSQL / #10 | Planejado |
| IDE-01 | Mesma chave com payload igual/diferente e chaves distintas | Repetição igual preserva ID e saldo; conflito rejeita alteração; chaves diferentes contabilizam operações válidas separadamente. | HTTP e PostgreSQL / #11 | Planejado |
| IDE-02 | Timeout após commit | Retry devolve o resultado persistido; verificar uma movimentação e um débito. | HTTP e PostgreSQL / #11 | Planejado |
| CON-01 | Mesma chave simultânea e disputa pela mesma conta | Usar barreira entre clientes; conferir efeito único por chave, saldo não negativo e conservação do total. | HTTP e PostgreSQL / #12 | Planejado |
| KAF-01 | Publicação, consumo, contrato e ordenação por chave | Validar schema/versionamento, chave, correlação e ordem na mesma partição. | PostgreSQL e Kafka / #13–#14 | Planejado |
| KAF-02 | Duplicidade, reinicialização e replay | Reiniciar após efeito e antes do commit do offset; reprocessar e observar apenas um efeito por evento. | Kafka e consumidor / #14 | Planejado |
| KAF-03 | Broker indisponível e consistência do outbox | Comparar estado da transferência e outbox; restaurar broker, reconciliar evento publicado e efeito persistido. | PostgreSQL e Kafka / #13, #15 | Planejado |
| RES-01 | Falha transitória e permanente | Retry limitado na transitória; DLQ e reprocessamento controlado na permanente; serviço recupera após retorno da dependência. | HTTP e Kafka / #15 | Planejado |
| PERF-01 | Carga e estresse | Medir p95/p99, throughput e erros com massa e ambiente identificados; validar SLO definido e consistência pós-carga. | Serviço real / #16 | Planejado |
| CI-01 | Repetibilidade, segurança dos artefatos e evidência | Gates por camada com resultados publicados, sem dados sensíveis; correlacionar falhas com identificador sintético. | CI / #17–#18 | Planejado |
