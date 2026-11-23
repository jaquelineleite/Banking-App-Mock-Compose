# API bancária de laboratório

Serviço FastAPI para exercitar testes de API com duas contas fictícias.
A primeira migração cadastra `conta-a` em R$ 100,00 e `conta-b` em R$ 50,00.
Os valores trafegam em **centavos inteiros de BRL**. O PostgreSQL preserva
saldos e comprovantes quando o serviço reinicia.

## Rodar no Windows

Na raiz do projeto, com Python 3.12, Docker e PowerShell:

```powershell
py -3.12 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r banking_api/requirements-test.txt
docker run --name banking-lab-pg -d -p 127.0.0.1:5432:5432 -e POSTGRES_USER=banking -e POSTGRES_PASSWORD=banking-local -e POSTGRES_DB=banking postgres:16
docker exec banking-lab-pg pg_isready -U banking -d banking
$env:BANKING_DATABASE_URL = "postgresql://banking:banking-local@127.0.0.1:5432/banking"
$env:BANKING_TEST_DATABASE_URL = $env:BANKING_DATABASE_URL
& $python -m banking_api.database
& $python -m pytest banking_api/tests -q

$env:BANKING_LAB_TOKEN_A = & $python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:BANKING_LAB_TOKEN_B = & $python -c "import secrets; print(secrets.token_urlsafe(32))"
& $python -m uvicorn banking_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Aguarde o `pg_isready` indicar que o banco aceita conexões antes de
rodar a migração. As credenciais acima são apenas para o laboratório local.

A página [Swagger UI](http://127.0.0.1:8000/docs) permite autorizar com o
token de uma conta e experimentar as rotas. O [OpenAPI em JSON](http://127.0.0.1:8000/openapi.json)
documenta os tipos, limites e respostas HTTP.

| Rota | Retorno |
| --- | --- |
| `GET /contas` | `200` com as contas visíveis para o token. |
| `GET /contas/{conta_id}` | `200` com a conta própria ou `404` quando indisponível. |
| `POST /transferencias` | `201` com o identificador, a origem, o destino e o valor. |

Exemplo de corpo de transferência com o token da conta A:

```json
{"origem": "conta-a", "destino": "conta-b", "valor_centavos": 250}
```

- `401` para token ausente ou inválido.
- `404` para origem fora do escopo ou destino inexistente.
- `409` para saldo insuficiente ou origem igual ao destino.
- `422` para corpo inválido, incluindo valores decimais, zero, negativos
  ou superiores a 1.000.000.000 centavos.
- `503` para falha de armazenamento.

Os tokens são de laboratório, distintos, vinculados a uma conta e fornecidos
por variáveis de ambiente. Use somente dados fictícios e mantenha o serviço
em localhost. O débito, o crédito e o comprovante são gravados na mesma
transação do PostgreSQL, com bloqueio das duas contas na ordem do ID.
Idempotência, integração Android e testes de concorrência ficam para
as etapas seguintes.

Os testes de API isolam os dados em um esquema PostgreSQL por caso, com
remoção ao final. Eles verificam autorização, contrato,
débito/crédito e preservação de ambos os saldos em rejeições.

## Evidências

Em 19/11/2026, os 17 testes da API passaram em um ambiente Python 3.12
criado do zero. Os 8 testes unitários da base Appium também passaram.
Um smoke HTTP com Uvicorn confirmou a consulta autenticada, a
transferência de 250 centavos e os saldos finais de 9.750 e 5.250 centavos.

## Contrato e jornada de transferência

Na raiz do projeto, rode `python -m pytest banking_api/tests -q` no
ambiente preparado acima. O Service Object `BankingApiClient` centraliza
as chamadas HTTP e devolve a resposta para as asserções dos testes.

- `test_openapi_contract.py` valida status, tipo de conteúdo e respostas
  JSON contra os esquemas publicados em `/openapi.json`. As expectativas
  de negócio e de status também ficam explícitas nos testes.
- `features/transferencia.feature` descreve em Gherkin a transferência
  de R$ 2,50 e verifica comprovante, débito, crédito e preservação do saldo
  total. Para executar só a jornada, rode
  `python -m pytest banking_api/tests/test_transferencia_bdd.py -v`.
- Cada caso usa sua própria instância da API. A execução passa pelo
  `TestClient` do FastAPI dentro do processo de testes.

Validação do PR #8 em 19/11/2026: 27 testes da API aprovados em Python
3.12, sendo 17 existentes, 9 de contrato e 1 jornada BDD. Os resultados
foram obtidos em execução local.

## GitHub Actions

O workflow **Testes da API bancária** inicia um PostgreSQL 16 dedicado
e executa a suíte nos pull requests destinados à `master`.
O check **pytest da API** mostra o resultado do pytest. O artefato
`banking-api-junit` contém o XML JUnit, publicado mesmo quando algum teste
falha, desde que o pytest gere o relatório.

## Limites e timeout HTTP

Os cenários parametrizados cobrem campos ausentes, extras e tipos inválidos.
A cada rejeição, o teste consulta as duas contas antes e depois e verifica
que os saldos foram preservados. A matriz de valores distingue o limite
da conta do limite do contrato. Com o saldo inicial de 10.000 centavos,
1 centavo e o saldo exato são aceitos. O teto contratual de 1.000.000.000
centavos chega à regra de saldo e recebe `409`. Um centavo acima do teto
recebe `422`.

O cenário de timeout usa uma conexão HTTP local em porta dinâmica. O
servidor de teste recebe a requisição e retém a resposta para provocar um
timeout de leitura no cliente HTTP. A única conclusão é que o cliente
ficou sem resposta no prazo. O resultado financeiro de uma transferência
real permanece desconhecido nessa situação. Retry seguro será coberto
na etapa de idempotência.

Na raiz do projeto, execute:

```powershell
python -m pytest banking_api/tests -q --junitxml=reports/banking-api-junit.xml
```

Validação local em 19/11/2026: **44 testes aprovados**, incluindo 17 casos
novos. O mesmo comando roda no GitHub Actions com publicação do JUnit.


## Integridade financeira no PostgreSQL

A migração versionada cria as tabelas e as restrições de integridade.
Reexecutá-la preserva os saldos e os comprovantes já gravados.

Os cenários em `features/integridade_financeira.feature` consultam o banco
diretamente para confirmar transferência concluída, saldo insuficiente e
rollback. No rollback, um gatilho exclusivo do esquema de teste verifica
que o débito já ocorreu e interrompe o crédito. Uma sequência registra
que a falha foi provocada nesse ponto, mesmo após o rollback. O teste
então confirma os dois saldos originais e a ausência de comprovantes.

Para rodar apenas esse BDD:

```powershell
& $python -m pytest banking_api/tests/test_integridade_postgres_bdd.py -v
```

Em 20/11/2026, 54 testes da API passaram localmente com PostgreSQL 18.7,
incluindo os três cenários BDD e cinco verificações de migração e esquema.

## Idempotência de transferências

Em `POST /transferencias`, envie o cabeçalho opcional `Idempotency-Key`
com 1 a 128 caracteres ASCII (letras, dígitos, ponto, hífen ou sublinhado).
Gere uma chave por transferência e reutilize a mesma chave e os mesmos
dados se a resposta se perder.

| Requisição | Resultado |
| --- | --- |
| Chave inédita e transferência válida | `201`, com débito, crédito e comprovante persistidos na mesma transação |
| Mesma conta de origem, chave, destino e valor | `201`, com o comprovante original e sem nova movimentação |
| Mesma conta de origem e chave, com destino ou valor válido diferente | `409`, com `chave_idempotencia_em_conflito` e saldos preservados |
| Cabeçalho inválido | `422` |
| Sem cabeçalho | Cada requisição válida é processada como uma nova transferência |

A migração `002_idempotencia.sql` persiste a chave na linha da transferência
e garante sua unicidade por conta de origem. A autorização da origem é
verificada em cada chamada. Rejeições não reservam a chave. A chave
permanece vinculada ao comprovante e não tem expiração configurada.

O BDD simula a perda da resposta na interface ASGI após a confirmação.
O PostgreSQL é real e o teste consulta diretamente os dois saldos e o
comprovante antes e depois do reenvio. O cenário de timeout HTTP por socket
continua separado.

```powershell
& $python -m pytest banking_api/tests/test_idempotencia_bdd.py -v
& $python -m pytest banking_api/tests -q --junitxml=reports/banking-api-junit.xml
```

## Concorrência de transferências

Os cenários em `features/concorrencia.feature` enviam duas solicitações
concorrentes de 6.000 centavos de uma conta com saldo de 10.000 centavos.
Com a mesma chave, ambas recebem o mesmo comprovante. Com chaves
distintas, uma recebe `201` e a outra recebe `409` por saldo insuficiente.
O teste confere os dois saldos e um único registro de transferência
diretamente no PostgreSQL, independentemente de qual chamada termine primeiro.

Cada cenário usa um esquema isolado. Uma conexão de teste bloqueia a
conta de origem e libera o bloqueio quando o PostgreSQL confirma que
ambas as requisições estão aguardando. A consulta de bloqueios tem prazo
limitado. As chamadas usam o TestClient dentro do processo e o banco é real.

```powershell
& $python -m pytest banking_api/tests/test_concorrencia_bdd.py -v
& $python -m pytest banking_api/tests -q --junitxml=reports/banking-api-junit.xml
```

## Eventos de transferência no Kafka

A API de laboratório publica `transferencia.confirmada.v1` depois do
commit no PostgreSQL, quando `BANKING_KAFKA_BOOTSTRAP_SERVERS` está
configurada. O tópico padrão é `banking.transferencias.v1` e pode ser
substituído por `BANKING_KAFKA_TOPIC`. O tópico deve existir antes de
usar a API. A chave da mensagem é a conta de origem. O JSON contém
`tipo`, `transferencia_id`, `valor_centavos` e `moeda`.
Uma rejeição ou um reenvio idempotente não publica um novo evento.

O BDD usa um tópico temporário por cenário. Ele consome a mensagem de
uma transferência aprovada e compara com o comprovante persistido.
Para saldo insuficiente, verifica os offsets do tópico e a ausência
de comprovante no banco.

Com o PostgreSQL de teste configurado, execute na raiz:

```powershell
docker run --rm -d --name banking-kafka -p 127.0.0.1:9092:9092 apache/kafka:4.1.1
$env:BANKING_TEST_KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
& $python -m pytest banking_api/tests -q --junitxml=reports/banking-api-junit.xml
docker stop banking-kafka
```

Sem a variável de Kafka de teste, os dois cenários de mensageria são
ignorados localmente. O GitHub Actions fornece PostgreSQL e Kafka reais.

O Kafka e o PostgreSQL confirmam operações separadas. Se a publicação
falhar depois do commit, a API mantém o comprovante e registra um aviso.
A entrega confiável após falha depende de uma etapa posterior de resiliência.

### Contrato, duplicidade, ordenação e releitura

O JSON Schema `contratos/transferencia.confirmada.v1.json` especifica
os campos obrigatórios, o UUID do comprovante, o valor em centavos e a
moeda. O BDD valida o payload consumido do broker contra esse contrato.

Em tópicos isolados com três partições, os testes verificam que o
reenvio da mesma transferência preserva o comprovante e publica um
único evento. Três transferências sequenciais da mesma conta chegam com
a mesma chave, na mesma partição e com offsets crescentes. A ordem
verificada vale para aquela partição e para publicações sequenciais.

Uma segunda instância do consumidor pode reler a mensagem na mesma
partição e no mesmo offset. O teste compara os bytes e verifica que
a releitura preserva saldos e comprovante. Esse consumidor de teste só
lê mensagens. O cenário demonstra replay por offset explícito. A
deduplicação de efeitos em consumidores de negócio e a recuperação de
publicações perdidas pertencem às etapas seguintes.

```powershell
& $python -m pytest banking_api/tests/test_eventos_kafka_bdd.py -v
```
