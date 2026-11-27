# Registro de validação da base mobile

Ambiente Linux, Python 3.12.14, Appium Python Client 5.2.4, Selenium 4.53.0,
pytest 8.4.2 e pytest-html 4.1.1.

| Comando | Resultado observado |
| --- | --- |
| `python -m pytest qa_mobile/unit -q --html=qa_mobile/reports/unit.html --self-contained-html` | 3 aprovados em 0,02 s. HTML gerado localmente. |
| `python -m pytest` com os três caminhos de teste selecionados na ordem inversa | 3 aprovados em 0,02 s. |
| `python -m pytest qa_mobile/tests --collect-only -q` | 3 coletados em 0,00 s. |
| `python -m compileall -q qa_mobile/config.py qa_mobile/pages qa_mobile/tests qa_mobile/unit` | Código Python compilado sem erros. |
| `python -m pip check` | Nenhum requisito quebrado. |
| `git diff --cached --check` | Diff sem erros de whitespace. |
| `curl -fsS --max-time 3 http://127.0.0.1:4723/status` | Conexão recusada neste ambiente de auditoria. |

A verificação unitária cobre defaults, valores sobrescritos e independência
de objetos de configuração. A falha de conexão acima descreve apenas este
ambiente Linux; ela não invalida a execução local posterior registrada abaixo.

## Execução local em Android — 26/11/2026

| Suíte | Resultado observado |
| --- | --- |
| `qa_mobile/tests` com Appium | 3 aprovados em 82,63 s em Android 15: saldo visível no Dashboard, abertura do Histórico e retorno à Home. |

Essa execução valida as três jornadas de navegação e a presença dos elementos
consultados. Ela não confirma o valor numérico do saldo nem que os filtros
retornam as transações corretas. O commit e a versão do APK não foram anotados
junto ao resultado. Para reproduzir a suíte, consulte o [guia do Appium](../../qa_mobile/README.md).
