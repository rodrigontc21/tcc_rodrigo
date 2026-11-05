"""Fábricas do projeto são chamadas com argumento nomeado.

Argumento posicional que cai no parâmetro errado não levanta exceção nem
deixa rastro: a reprodução da orientação passou o caminho do prior como
terceiro argumento posicional de `create_model`, onde ele virou
`prior_type`, e a Plain CNN treinou sem prior (relatório 3, 29/10). É o
mesmo gênero do cabeçalho trocado do `targets.csv`.

Regra, sugerida pela orientação em 30/10: nenhuma fábrica deste projeto é
chamada com mais de dois argumentos posicionais. Fábrica, aqui, é uma
classe definida em `src/tcc` (o construtor dela) ou um classmethod dela, e
também as fábricas do código do artigo que os scripts de verificação usam
(`PGSG_FACTORIES`), que são justamente as do erro de 29/10. O teste varre
`src`, `scripts` e `tests`.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ("src", "scripts", "tests")
MAX_POSITIONAL = 2

# Fábricas do código do artigo (docs/fontes/prior-guided-spectral-gating-main,
# não versionado), chamadas pelos scripts de verificação. Ficam listadas à
# mão porque o código não está no repositório para ser varrido.
PGSG_FACTORIES = {
    "BandSelectNet",
    "BandSelectNetLight",
    "SpectralGatingLayer",
    "create_model",
    "create_model_light",
}


def _factories(source_dir: Path) -> tuple[set[str], set[tuple[str, str]]]:
    """Nomes de classe, e pares (classe, classmethod), definidos em source_dir."""
    classes: set[str] = set()
    classmethods: set[tuple[str, str]] = set()
    for path in source_dir.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ClassDef):
                continue
            classes.add(node.name)
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and any(
                    isinstance(d, ast.Name) and d.id == "classmethod"
                    for d in item.decorator_list
                ):
                    classmethods.add((node.name, item.name))
    return classes, classmethods


def _factory_name(call: ast.Call, classes, classmethods) -> str | None:
    func = call.func
    if isinstance(func, ast.Name) and func.id in classes:
        return func.id
    if isinstance(func, ast.Attribute):
        if func.attr in classes:
            return func.attr
        if isinstance(func.value, ast.Name) and (func.value.id, func.attr) in classmethods:
            return f"{func.value.id}.{func.attr}"
    return None


def _violations(source: str, classes, classmethods) -> list[tuple[int, str, int]]:
    """(linha, fábrica, nº de posicionais) de cada chamada acima do limite.

    Argumento com `*` conta como acima do limite: o tamanho é desconhecido.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = _factory_name(node, classes, classmethods)
        if name is None:
            continue
        starred = any(isinstance(a, ast.Starred) for a in node.args)
        if len(node.args) > MAX_POSITIONAL or starred:
            found.append((node.lineno, name, len(node.args)))
    return found


def test_checker_flags_positional_factory_calls():
    classes, classmethods = {"Model"}, {("Model", "of")}
    source = (
        "Model(a, b)\n"
        "Model(a, b, c)\n"
        "pkg.Model(a, b, c=c)\n"
        "pkg.Model(a, b, c, d)\n"
        "Model.of(a, b, c)\n"
        "Model(*args)\n"
        "other(a, b, c)\n"
    )
    assert _violations(source, classes, classmethods) == [
        (2, "Model", 3),
        (4, "Model", 4),
        (5, "Model.of", 3),
        (6, "Model", 1),
    ]


def test_factories_are_found_in_the_project():
    classes, classmethods = _factories(ROOT / "src" / "tcc")
    assert {"Dataset", "PLSArm", "IPLSArm", "VIPArm", "GAPLSArm"} <= classes
    assert ("_CrossProducts", "of") in classmethods


def test_pgsg_factories_are_checked():
    source = (
        "BandSelectNetLight(100, 1, prior, 16, 0.5)\n"
        "v.BandSelectNetLight(n_bands=100, n_outputs=1, prior_scores=prior)\n"
        "create_model(100, 1, path)\n"
    )
    assert _violations(source, PGSG_FACTORIES, set()) == [
        (1, "BandSelectNetLight", 5),
        (3, "create_model", 3),
    ]


def test_no_factory_is_called_with_more_than_two_positional_arguments():
    classes, classmethods = _factories(ROOT / "src" / "tcc")
    classes |= PGSG_FACTORIES
    found = []
    for folder in SCANNED:
        for path in sorted((ROOT / folder).rglob("*.py")):
            for line, name, n in _violations(
                path.read_text(encoding="utf-8"), classes, classmethods
            ):
                found.append(f"{path.relative_to(ROOT)}:{line} {name}, {n} posicionais")
    assert not found, "chame por nome:\n" + "\n".join(found)
