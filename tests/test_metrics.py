"""Métricas (Estágio 6; ADR 019). Cada uma com entrada sintética de resposta
conhecida, como o pipeline exige."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pytest

from tcc.metrics import (
    cost_summary,
    expected_jaccard,
    fraction_in_windows,
    jaccard,
    mean_pairwise_jaccard,
    performance,
    reproducibility,
)


@dataclass
class R:
    dataset_name: str = "d"
    arm_name: str = "a"
    seed_split: int = 0
    seed_algo: int = 0
    selection: set[int] | None = None
    band_scores: np.ndarray | None = None
    n_fits: int = 1
    wall_time: float = 1.0


# --- desempenho ------------------------------------------------------------------

def test_performance_known_values():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    perfect = performance(y, y)
    assert perfect["r2"] == 1.0 and perfect["rmse"] == 0.0
    mean = performance(y, np.full(4, y.mean()))
    assert mean["r2"] == 0.0
    off = performance(y, y + 2.0)  # erro constante 2
    assert off["rmse"] == pytest.approx(2.0) and off["rmsep"] == off["rmse"]
    assert off["r2"] == pytest.approx(1 - 16 / 5)  # SSres 16, SStot 5


def test_performance_rejects_mismatched_sizes():
    with pytest.raises(ValueError):
        performance(np.arange(3.0), np.arange(4.0))


# --- Jaccard -------------------------------------------------------------------------

def test_jaccard_known_values():
    assert jaccard({1, 2, 3}, {1, 2, 3}) == 1.0
    assert jaccard({1, 2}, {3, 4}) == 0.0
    assert jaccard({1, 2, 3}, {2, 3, 4}) == pytest.approx(2 / 4)
    assert jaccard({1}, {1, 2, 3, 4}) == pytest.approx(1 / 4)  # tamanhos diferentes


def test_jaccard_is_symmetric_and_rejects_two_empty_sets():
    assert jaccard({1, 5}, {5, 7, 9}) == jaccard({5, 7, 9}, {1, 5})
    assert jaccard(set(), {1}) == 0.0
    with pytest.raises(ValueError):
        jaccard(set(), set())


def test_mean_pairwise_jaccard_known_value():
    # pares: (A,B) 2/4, (A,C) 0/6, (B,C) 1/5 -> média 0,7/3
    A, B, C = {1, 2, 3}, {2, 3, 4}, {4, 5, 6}
    assert mean_pairwise_jaccard([A, B, C]) == pytest.approx((0.5 + 0 + 0.2) / 3)
    with pytest.raises(ValueError):
        mean_pairwise_jaccard([A])


def test_expected_jaccard_by_full_enumeration():
    # p = 6, conjuntos de 2 e 3: enumera todos os pares e tira a média exata.
    p, a, b = 6, 2, 3
    vals = [jaccard(set(x), set(y)) for x in combinations(range(p), a)
            for y in combinations(range(p), b)]
    assert expected_jaccard(a, b, p) == pytest.approx(np.mean(vals), abs=1e-12)


def test_expected_jaccard_matches_sampling_and_limits():
    rng = np.random.default_rng(0)
    p, k = 100, 10
    sim = np.mean([jaccard(set(rng.choice(p, k, replace=False)),
                           set(rng.choice(p, k, replace=False))) for _ in range(20000)])
    assert expected_jaccard(k, k, p) == pytest.approx(sim, abs=0.003)
    assert expected_jaccard(5, 5, 5) == 1.0  # todo o espectro: sempre iguais
    with pytest.raises(ValueError):
        expected_jaccard(0, 3, 10)


def test_jaccard_agrees_with_scikit_learn():
    # Conferência contra uma implementação independente: o jaccard_score do
    # scikit-learn sobre os vetores binários de pertença.
    from sklearn.metrics import jaccard_score
    rng = np.random.default_rng(1)
    p = 60
    for _ in range(500):
        a = set(rng.choice(p, rng.integers(1, p), replace=False).tolist())
        b = set(rng.choice(p, rng.integers(1, p), replace=False).tolist())
        va = np.isin(np.arange(p), list(a)).astype(int)
        vb = np.isin(np.arange(p), list(b)).astype(int)
        assert jaccard(a, b) == pytest.approx(jaccard_score(va, vb), abs=1e-15)


def test_expected_jaccard_agrees_with_scipy_hypergeometric():
    # Conferência contra a hipergeométrica do scipy: E[i / (a + b − i)], com i
    # o tamanho da interseção de dois conjuntos sorteados.
    from scipy.stats import hypergeom
    for a, b, p in ((10, 10, 100), (20, 140, 281), (7, 3, 12), (50, 50, 401)):
        i = np.arange(0, min(a, b) + 1)
        pmf = hypergeom(M=p, n=a, N=b).pmf(i)
        assert expected_jaccard(a, b, p) == pytest.approx(np.sum(pmf * i / (a + b - i)), abs=1e-12)


# --- reprodutibilidade nos dois eixos -------------------------------------------------

def _grid():
    """Braço 'estavel' escolhe o mesmo conjunto em toda partição, mas muda com
    a semente do algoritmo; braço 'instavel' é o contrário."""
    rs = []
    for s in range(3):
        for a in range(3):
            rs.append(R(arm_name="estavel_na_particao", seed_split=s, seed_algo=a,
                        selection={a, a + 10}))
            rs.append(R(arm_name="estavel_no_algoritmo", seed_split=s, seed_algo=a,
                        selection={s, s + 10}))
    return rs


def test_reproducibility_separates_the_two_axes():
    rs = _grid()
    split = reproducibility(rs, k=2, axis="seed_split")
    algo = reproducibility(rs, k=2, axis="seed_algo")
    assert split[("d", "estavel_na_particao")] == 1.0
    assert split[("d", "estavel_no_algoritmo")] == 0.0
    assert algo[("d", "estavel_na_particao")] == 0.0
    assert algo[("d", "estavel_no_algoritmo")] == 1.0


def test_reproducibility_uses_the_selection_layer():
    # Escores contínuos: top-k; com k = 1 os dois resultados escolhem a
    # banda 0, com k = 2 divergem na segunda banda.
    rs = [R(seed_split=0, band_scores=np.array([0.9, 0.5, 0.1])),
          R(seed_split=1, band_scores=np.array([0.9, 0.1, 0.5]))]
    assert reproducibility(rs, k=1, axis="seed_split")[("d", "a")] == 1.0
    assert reproducibility(rs, k=2, axis="seed_split")[("d", "a")] == pytest.approx(1 / 3)


def test_reproducibility_skips_arms_without_selection():
    rs = [R(arm_name="pls_full", seed_split=s) for s in range(3)]
    assert reproducibility(rs, k=2, axis="seed_split") == {}


def test_reproducibility_rejects_duplicates_and_unknown_axis():
    rs = [R(seed_split=0, selection={1}), R(seed_split=0, selection={2})]
    with pytest.raises(ValueError):
        reproducibility(rs, k=1, axis="seed_split")
    with pytest.raises(ValueError):
        reproducibility([], k=1, axis="particao")


# --- plausibilidade química --------------------------------------------------------

def test_fraction_in_windows_known_value():
    axis = np.array([850.0, 900.0, 930.0, 1000.0, 1050.0])
    windows = [(925.0, 935.0), (1000.0, 1000.0)]  # limites inclusos
    assert fraction_in_windows({0, 2, 3, 4}, axis, windows) == pytest.approx(2 / 4)
    assert fraction_in_windows({2}, axis, windows) == 1.0
    assert fraction_in_windows({0}, axis, windows) == 0.0


def test_fraction_in_windows_rejects_bad_input():
    with pytest.raises(ValueError):
        fraction_in_windows(set(), np.arange(3.0), [(0, 1)])
    with pytest.raises(ValueError):
        fraction_in_windows({0}, np.arange(3.0), [(2, 1)])


# --- custo -------------------------------------------------------------------------

def test_cost_summary_takes_medians_per_arm():
    # valores assimétricos: a média (40 e 4,0) não coincide com a mediana
    rs = [R(arm_name="a", n_fits=n, wall_time=t) for n, t in ((10, 1.0), (90, 9.0), (20, 2.0))]
    rs.append(R(arm_name="b", n_fits=7, wall_time=0.5))
    out = cost_summary(rs)
    assert out[("d", "a")] == {"n_fits": 20.0, "wall_time": 2.0, "n": 3}
    assert out[("d", "b")] == {"n_fits": 7.0, "wall_time": 0.5, "n": 1}
