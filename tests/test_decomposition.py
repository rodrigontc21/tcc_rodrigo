"""Decomposição pareada e equivalência (Estágio 7; ADR 020)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from tcc.decomposition import (
    ARMS,
    additive_identity_gap,
    decompose,
    friedman,
    holm,
    paired_differences,
    posthoc_wilcoxon_holm,
    tost,
)


@dataclass
class R:
    dataset_name: str
    seed_split: int
    arm_name: str
    r2: float
    rmsep: float = 0.0


def grid(rng, datasets=("d1", "d2"), seeds=range(10)):
    rs = []
    for d in datasets:
        for s in seeds:
            for arm in ARMS.values():
                rs.append(R(d, s, arm, float(rng.uniform(0.5, 1.0)), float(rng.uniform(0, 2))))
    return rs


# --- decomposição ------------------------------------------------------------------

def test_additive_identity_holds_in_every_partition():
    # Pipeline: teste que verifique a identidade aditiva por (conjunto, semente).
    dec = decompose(grid(np.random.default_rng(0)))
    assert len(dec["total"]) == 20
    assert additive_identity_gap(dec) < 1e-12
    for metric in ("r2", "rmsep"):
        assert additive_identity_gap(decompose(grid(np.random.default_rng(1)), metric)) < 1e-12


def test_terms_known_values():
    vals = {"pls_full": 0.90, "mlp_full": 0.80, "mlp_weighted": 0.85,
            "gate_uniform": 0.70, "gate_prior": 0.86}
    dec = decompose([R("d", 0, a, v) for a, v in vals.items()])
    k = ("d", 0)
    assert dec["nao_lin"][k] == pytest.approx(-0.10)
    assert dec["ponderacao"][k] == pytest.approx(0.05)
    assert dec["aprendizado"][k] == pytest.approx(0.01)
    assert dec["prior"][k] == pytest.approx(0.16)
    assert dec["total"][k] == pytest.approx(-0.04)


def test_incomplete_partition_leaves_every_term():
    # Sem o B3 na partição 3, ela sai também dos termos que não usam o B3:
    # todos os termos ficam sobre as mesmas partições.
    rs = [r for r in grid(np.random.default_rng(2), datasets=("d",))
          if not (r.seed_split == 3 and r.arm_name == "gate_uniform")]
    dec = decompose(rs)
    assert dec["excluidas"] == [("d", 3)]
    for term in ("nao_lin", "ponderacao", "aprendizado", "prior", "total"):
        assert ("d", 3) not in dec[term] and len(dec[term]) == 9


def test_marginal_means_break_the_pairing():
    # Com uma partição faltando num braço, a diferença das médias marginais não
    # é a média das diferenças pareadas; a decomposição usa a pareada.
    rs = grid(np.random.default_rng(3), datasets=("d",))
    rs = [r for r in rs if not (r.seed_split == 0 and r.arm_name == "pls_full")]
    pareada = np.mean(list(paired_differences(rs, "mlp_full", "pls_full").values()))
    marg = (np.mean([r.r2 for r in rs if r.arm_name == "mlp_full"])
            - np.mean([r.r2 for r in rs if r.arm_name == "pls_full"]))
    assert pareada == pytest.approx(np.mean(list(decompose(rs)["nao_lin"].values())))
    assert pareada != pytest.approx(marg)


def test_repeated_cell_is_an_error():
    rs = [R("d", 0, "pls_full", 0.9), R("d", 0, "pls_full", 0.8)]
    with pytest.raises(ValueError):
        decompose(rs)


# --- TOST --------------------------------------------------------------------------------

def test_tost_matches_statsmodels():
    from statsmodels.stats.weightstats import ttost_paired
    rng = np.random.default_rng(4)
    for mean, sd, n, delta in ((0.0, 0.01, 30, 0.01), (0.008, 0.01, 30, 0.01),
                               (0.02, 0.01, 10, 0.01), (-0.003, 0.02, 100, 0.005)):
        d = rng.normal(mean, sd, n)
        ours = tost(d, delta)
        p_sm, _, _ = ttost_paired(d, np.zeros(n), -delta, delta)
        assert ours["p"] == pytest.approx(p_sm, rel=1e-10, abs=1e-15)


def test_tost_equivalence_is_the_ci_inside_the_margin():
    # Equivalente se e só se o intervalo de 1 − 2α cabe em (−δ, δ).
    rng = np.random.default_rng(5)
    for _ in range(300):
        d = rng.normal(rng.uniform(-0.02, 0.02), rng.uniform(0.001, 0.03), 20)
        r = tost(d, 0.01)
        assert r["equivalent"] == (-0.01 < r["ci_low"] and r["ci_high"] < 0.01)


def test_tost_known_cases():
    rng = np.random.default_rng(6)
    assert tost(rng.normal(0, 0.001, 30), 0.01)["equivalent"]       # colado no zero
    assert not tost(rng.normal(0.05, 0.001, 30), 0.01)["equivalent"]  # longe, fora da margem
    assert not tost(rng.normal(0, 0.05, 5), 0.01)["equivalent"]       # sem dados para afirmar
    with pytest.raises(ValueError):
        tost([0.1], 0.01)
    with pytest.raises(ValueError):
        tost([0.1, 0.2], 0.0)


# --- conferência contra o R base (implementação independente, outra linguagem) ------

def _r():
    ro = pytest.importorskip("rpy2.robjects")
    return ro


def _rvec(ro, x):
    return ro.FloatVector([float(v) for v in np.ravel(x)])


def test_tost_matches_two_one_sided_t_tests_in_r():
    # O TOST são dois t.test unilaterais do R base: H0 média ≤ −δ e média ≥ +δ.
    # O intervalo de 1 − 2α é o do t.test bilateral com conf.level = 1 − 2α.
    ro = _r()
    rng = np.random.default_rng(10)
    for mean, sd, n, delta in ((0.0, 0.01, 30, 0.01), (0.012, 0.01, 15, 0.01),
                               (-0.002, 0.03, 60, 0.005)):
        d = rng.normal(mean, sd, n)
        ours = tost(d, delta)
        x = _rvec(ro, d)
        tt = ro.r["t.test"]
        p_low = tt(x, mu=-delta, alternative="greater").rx2("p.value")[0]
        p_high = tt(x, mu=delta, alternative="less").rx2("p.value")[0]
        ci = tt(x, **{"conf.level": 0.90}).rx2("conf.int")
        assert ours["p_low"] == pytest.approx(p_low, rel=1e-10, abs=1e-15)
        assert ours["p_high"] == pytest.approx(p_high, rel=1e-10, abs=1e-15)
        assert ours["ci_low"] == pytest.approx(ci[0], rel=1e-10)
        assert ours["ci_high"] == pytest.approx(ci[1], rel=1e-10)


def test_holm_matches_p_adjust_in_r():
    ro = _r()
    rng = np.random.default_rng(11)
    for _ in range(20):
        p = rng.uniform(0, 0.3, rng.integers(2, 12))
        r_adj = np.array(ro.r["p.adjust"](_rvec(ro, p), method="holm"))
        np.testing.assert_allclose(holm(p), r_adj, rtol=1e-12)


def test_friedman_matches_friedman_test_in_r():
    ro = _r()
    rng = np.random.default_rng(12)
    for blocks, arms in ((10, 3), (30, 5), (8, 12)):
        table = rng.normal(size=(blocks, arms)) + np.linspace(0, 0.5, arms)
        m = ro.r["matrix"](_rvec(ro, table.T), nrow=blocks)  # R preenche por coluna
        r = ro.r["friedman.test"](m)
        ours = friedman(table)
        assert ours["statistic"] == pytest.approx(r.rx2("statistic")[0], rel=1e-10)
        assert ours["p"] == pytest.approx(r.rx2("p.value")[0], rel=1e-8)


def test_posthoc_wilcoxon_matches_wilcox_test_in_r():
    # Sem empates e com n pequeno, os dois usam a distribuição exata.
    ro = _r()
    rng = np.random.default_rng(13)
    table = rng.normal(size=(12, 3)) + np.array([0, 0.3, 1.0])
    out = posthoc_wilcoxon_holm(table, ["a", "b", "c"])
    for (i, j), key in (((0, 1), ("a", "b")), ((0, 2), ("a", "c")), ((1, 2), ("b", "c"))):
        r = ro.r["wilcox.test"](_rvec(ro, table[:, i]), _rvec(ro, table[:, j]), paired=True)
        assert out[key]["p"] == pytest.approx(r.rx2("p.value")[0], rel=1e-10)


# --- Holm, Friedman e pós-teste ----------------------------------------------------

def test_holm_matches_statsmodels():
    from statsmodels.stats.multitest import multipletests
    rng = np.random.default_rng(7)
    for _ in range(50):
        p = rng.uniform(0, 0.2, rng.integers(2, 15))
        np.testing.assert_allclose(holm(p), multipletests(p, method="holm")[1], rtol=1e-12)


def test_holm_known_values():
    # três p: o menor vezes 3, o seguinte vezes 2 (e nunca abaixo do anterior)
    np.testing.assert_allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])


def test_friedman_detects_a_consistent_ranking():
    rng = np.random.default_rng(8)
    base = rng.normal(size=(12, 1))
    table = base + np.array([0.0, 0.5, 1.0]) + rng.normal(0, 0.01, (12, 3))
    assert friedman(table)["p"] < 0.001
    noise = rng.normal(size=(12, 3))
    assert friedman(noise)["p"] > 0.01
    with pytest.raises(ValueError):
        friedman(np.ones((5, 2)))


def test_posthoc_covers_every_pair_with_holm():
    rng = np.random.default_rng(9)
    table = rng.normal(size=(15, 4)) + np.array([0, 0, 1, 2])
    out = posthoc_wilcoxon_holm(table, ["a", "b", "c", "d"])
    assert len(out) == 6
    raw = [v["p"] for v in out.values()]
    np.testing.assert_allclose([v["p_holm"] for v in out.values()], holm(raw))
    assert out[("a", "d")]["p_holm"] < 0.01
