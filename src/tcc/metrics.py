"""Métricas (Estágio 6 do pipeline; ADR 019).

Funções puras sobre resultados já gravados: nada aqui roda dentro do treino.
O pipeline exige que cada métrica tenha teste com entrada sintética de
resposta conhecida (`tests/test_metrics.py`); métrica sem teste não entra
no manuscrito.

- **Desempenho:** R², RMSE e RMSEP no teste externo (`performance`), com a
  mesma conta do `evaluate()`.
- **Reprodutibilidade da seleção:** Jaccard médio par a par entre conjuntos
  de bandas, separado pelos dois eixos de semente (`reproducibility`), e a
  referência do acaso para conjuntos dos mesmos tamanhos
  (`expected_jaccard`).
- **Plausibilidade química:** fração das bandas selecionadas que caem em
  janelas de atribuição espectroscópica (`fraction_in_windows`). A tabela
  de janelas, com as fontes, ainda não existe; a função recebe as janelas.
- **Custo:** `n_fits` e `wall_time` por braço (`cost_summary`).

Os "resultados" são objetos com os campos de `tcc.protocol.Result` que cada
função usa; os testes usam objetos sintéticos com esses campos.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from itertools import combinations
from math import comb

import numpy as np
from sklearn.metrics import r2_score

from tcc.selection import to_selection

AXES = ("seed_split", "seed_algo")


# --- desempenho ----------------------------------------------------------------

def performance(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """R² e RMSEP no teste externo, como no `evaluate()`.

    RMSE e RMSEP são a mesma conta (raiz do erro quadrático médio no teste
    externo); o pipeline lista os dois nomes, e aqui ficam os dois campos.
    """
    y_true, y_pred = np.ravel(y_true), np.ravel(y_pred)
    if y_true.shape != y_pred.shape or y_true.size < 2:
        raise ValueError("y_true e y_pred precisam ter o mesmo tamanho, pelo menos 2")
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return {"r2": float(r2_score(y_true, y_pred)), "rmse": rmse, "rmsep": rmse}


# --- reprodutibilidade da seleção ----------------------------------------------------

def jaccard(a: set[int], b: set[int]) -> float:
    """|A ∩ B| / |A ∪ B|. Recusa dois conjuntos vazios (0/0)."""
    a, b = set(a), set(b)
    union = a | b
    if not union:
        raise ValueError("Jaccard de dois conjuntos vazios não é definido")
    return len(a & b) / len(union)


def mean_pairwise_jaccard(sets: Sequence[set[int]]) -> float:
    """Média do Jaccard sobre todos os pares não ordenados."""
    if len(sets) < 2:
        raise ValueError("são precisos pelo menos dois conjuntos")
    return float(np.mean([jaccard(a, b) for a, b in combinations(sets, 2)]))


def expected_jaccard(a: int, b: int, p: int) -> float:
    """Jaccard esperado entre um conjunto de tamanho a e um de tamanho b
    sorteados ao acaso entre p bandas: a interseção é hipergeométrica."""
    if not (0 < a <= p and 0 < b <= p):
        raise ValueError("tamanhos devem estar em [1, p]")
    total = comb(p, b)
    e = 0.0
    for i in range(max(0, a + b - p), min(a, b) + 1):
        e += comb(a, i) * comb(p - a, b - i) / total * i / (a + b - i)
    return e


def reproducibility(results: Iterable, k: int, axis: str) -> dict:
    """Jaccard médio par a par, num eixo de semente.

    Agrupa por (conjunto, braço) e pela semente do **outro** eixo, que fica
    fixa: no eixo `seed_split`, compara partições com a mesma `seed_algo`;
    no eixo `seed_algo`, compara sementes do algoritmo na mesma partição.
    Converte cada resultado em conjunto com `to_selection(result, k)`.
    Braços sem seleção (PLS completo, MLP sem porta) ficam de fora.

    Devolve {(conjunto, braço): Jaccard médio}, com a média dos grupos
    quando há mais de um valor da semente fixa.
    """
    if axis not in AXES:
        raise ValueError(f"eixo deve ser um de {AXES}")
    fixed = "seed_algo" if axis == "seed_split" else "seed_split"
    groups: dict = defaultdict(dict)
    for r in results:
        sel = to_selection(r, k)
        if sel is None:
            continue
        key = (r.dataset_name, r.arm_name, getattr(r, fixed))
        varying = getattr(r, axis)
        if varying in groups[key]:
            raise ValueError(f"resultado repetido: {key} com {axis} = {varying}")
        groups[key][varying] = sel
    per_arm: dict = defaultdict(list)
    for (dataset, arm, _), sels in groups.items():
        if len(sels) >= 2:
            per_arm[(dataset, arm)].append(mean_pairwise_jaccard(list(sels.values())))
    return {key: float(np.mean(v)) for key, v in per_arm.items()}


# --- plausibilidade química ------------------------------------------------------

def fraction_in_windows(selection: set[int], axis: np.ndarray,
                        windows: Sequence[tuple[float, float]]) -> float:
    """Fração das bandas selecionadas cujo valor no eixo espectral cai em
    alguma janela [início, fim], limites inclusos."""
    if not selection:
        raise ValueError("seleção vazia")
    axis = np.asarray(axis, dtype=float)
    for lo, hi in windows:
        if lo > hi:
            raise ValueError(f"janela invertida: ({lo}, {hi})")
    inside = [any(lo <= axis[j] <= hi for lo, hi in windows) for j in selection]
    return float(np.mean(inside))


# --- custo ---------------------------------------------------------------------------

def cost_summary(results: Iterable) -> dict:
    """Mediana de `n_fits` e de `wall_time` por (conjunto, braço), com o
    número de execuções."""
    acc: dict = defaultdict(lambda: ([], []))
    for r in results:
        fits, times = acc[(r.dataset_name, r.arm_name)]
        fits.append(r.n_fits)
        times.append(r.wall_time)
    return {key: {"n_fits": float(np.median(f)), "wall_time": float(np.median(t)),
                  "n": len(f)}
            for key, (f, t) in acc.items()}
