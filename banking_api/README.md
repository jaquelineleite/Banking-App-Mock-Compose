# API bancária de laboratório

Serviço FastAPI para exercitar testes de API com duas contas fictícias.
Cada instância começa com `conta-a` em R$ 100,00 e `conta-b` em R$ 50,00.
Os valores trafegam em **centavos inteiros de BRL**. Execute com um único
processo. Reiniciar o serviço restaura os saldos iniciais.

## Rodar no Windows

Na raiz do projeto, com Python 3.12 e PowerShell:

```powershell
py -3.12 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r banking_api/requirements-test.txt
& $python -m pytest banking_api/tests -q

$env:BANKING_LAB_TOKEN_A = & $python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:BANKING_LAB_TOKEN_B = & $python -c "import secrets; print(secrets.token_urlsafe(32))"
& $python -m uvicorn banking_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

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

Os tokens são de laboratório, distintos, vinculados a uma conta e fornecidos
por variáveis de ambiente. Use somente dados fictícios e mantenha o serviço
em localhost. O saldo é compartilhado dentro de um processo e o débito e
o crédito ocorrem sob o mesmo bloqueio. Persistência, idempotência,
integração Android e testes de concorrência fazem parte das etapas seguintes.

Os testes criam uma instância por caso e verificam autorização, contrato,
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

O workflow **Testes da API bancária** executa a suíte da API nos pull requests
destinados à `master`, incluindo os testes de contrato e a jornada BDD.
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
