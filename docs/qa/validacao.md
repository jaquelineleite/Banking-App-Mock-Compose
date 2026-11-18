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
| `curl -fsS --max-time 3 http://127.0.0.1:4723/status` | Conexão recusada. |

A verificação unitária cobre defaults, valores sobrescritos e independência
de objetos de configuração. A execução mobile aguarda o Android e Appium
descritos no [guia do Windows](../../qa_mobile/README.md).
