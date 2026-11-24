"""Resume os relatórios do pytest e rejeita execuções incompletas."""

import os
import sys
from pathlib import Path
from xml.etree import ElementTree


def validar(relatorios: list[Path]) -> int:
    linhas = [
        "## Evidências da API bancária",
        "",
        "| Relatório | Testes | Falhas | Erros | Ignorados |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    problemas = []
    for relatorio in relatorios:
        try:
            raiz = ElementTree.parse(relatorio).getroot()
            suites = [raiz] if raiz.tag == "testsuite" else raiz.findall("testsuite")
            totais = [
                sum(int(suite.attrib[campo]) for suite in suites)
                for campo in ("tests", "failures", "errors", "skipped")
            ]
        except (OSError, ElementTree.ParseError, KeyError, ValueError) as erro:
            problemas.append(f"{relatorio.name}: relatório ausente ou inválido ({erro}).")
            continue

        testes, falhas, erros, ignorados = totais
        linhas.append(f"| {relatorio.name} | {testes} | {falhas} | {erros} | {ignorados} |")
        if testes <= 0 or any((falhas, erros, ignorados)):
            problemas.append(f"{relatorio.name}: o gate exige testes executados sem falhas ou skips.")

    resumo = "\n".join([*linhas, "", *[f"- {problema}" for problema in problemas]]) + "\n"
    print(resumo)
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with Path(destino).open("a", encoding="utf-8") as arquivo:
            arquivo.write(resumo)
    return int(bool(problemas))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Informe ao menos um relatório JUnit.")
    raise SystemExit(validar([Path(nome) for nome in sys.argv[1:]]))
