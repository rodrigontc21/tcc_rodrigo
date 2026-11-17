"""Escolha na borda da grade declarada (orientação, 16/11/2026).

Todo hiperparâmetro escolhido de uma grade declarada avisa quando a escolha
cai num extremo, e a borda fica registrada em `hyperparams` (`*_edge`):
limiar do VIP, `int_num` do iPLS, (população, gerações) do GA-PLS, número de
componentes do PLS (só a borda de cima) e a receita das redes.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pytest

from tcc.arms.base import Budget, CVFolds, GridEdgeWarning, grid_edge, warn_edge
from tcc.arms.pls import PLSArm
from tcc.arms.vip import VIPArm
from tcc.metrics import edge_summary


@pytest.fixture(scope="module")
def problem():
    rng = np.random.default_rng(0)
    n, p = 80, 40
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 10:15].sum(axis=1) * 2.0 + 0.1 * rng.normal(size=n)
    folds: CVFolds = [(np.setdiff1d(np.arange(n), c), c) for c in np.array_split(np.arange(n), 5)]
    return X, y, folds


def fit(arm, problem):
    X, y, folds = problem
    return arm.fit(X, y, folds, np.random.default_rng(0), Budget())


def r_package(name):
    try:
        from rpy2.robjects.packages import importr
        importr(name)
        return True
    except Exception:  # noqa: BLE001
        return False


# --- a regra ---------------------------------------------------------------------------

def test_grid_edge_on_both_ends_and_in_the_middle():
    assert grid_edge(0.2, (0.2, 0.4, 0.6)) == "inferior"
    assert grid_edge(0.6, (0.2, 0.4, 0.6)) == "superior"
    assert grid_edge(0.4, (0.2, 0.4, 0.6)) is None
    assert grid_edge((50, 100), [(30, 50), (50, 100)]) == "superior"
    assert grid_edge(10, (10,)) is None  # um candidato só: não houve busca


def test_warning_only_when_on_an_edge():
    with pytest.warns(GridEdgeWarning, match="limiar = 0.2, na borda inferior"):
        warn_edge("vip", "limiar", 0.2, "inferior")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_edge("vip", "limiar", 0.4, None)


# --- VIP ---------------------------------------------------------------------------------

def test_vip_records_and_warns_an_edge_choice(problem):
    # Limiar 50 esvazia todo fold e sai da disputa: fica o 1,0, a borda de baixo.
    with pytest.warns(GridEdgeWarning, match="limiar"):
        f = fit(VIPArm(n_components=3, candidates=(1.0, 50.0)), problem)
    assert f.hyperparams["threshold"] == 1.0
    assert f.hyperparams["threshold_edge"] == "inferior"


def test_vip_fixed_threshold_has_no_edge(problem):
    with warnings.catch_warnings():
        warnings.simplefilter("error", GridEdgeWarning)
        f = fit(VIPArm(threshold=1.0, n_components=3), problem)
    assert f.hyperparams["threshold_edge"] is None


# --- PLS ---------------------------------------------------------------------------------

def test_pls_records_the_upper_edge(problem, monkeypatch):
    import tcc.arms.pls as pls
    monkeypatch.setattr(pls, "MAX_COMPONENTS", 1)  # teto de 1: a busca só pode ficar nele
    with pytest.warns(RuntimeWarning):
        f = fit(PLSArm(), problem)
    assert f.hyperparams["n_components_edge"] == "superior"


def test_pls_inside_the_grid_or_fixed_has_no_edge(problem):
    assert fit(PLSArm(), problem).hyperparams["n_components_edge"] is None
    assert fit(PLSArm(n_components=40), problem).hyperparams["n_components_edge"] is None


# --- iPLS e GA-PLS (R) ----------------------------------------------------------------------

@pytest.mark.skipif(not r_package("mdatools"), reason="pacote R mdatools indisponível")
def test_ipls_records_and_warns_an_edge_choice(problem):
    from tcc.arms.ipls import IPLSArm
    with pytest.warns(GridEdgeWarning, match="int_num"):
        f = fit(IPLSArm(glob_ncomp=3, candidates=(4, 8)), problem)
    h = f.hyperparams
    assert h["int_num_edge"] == grid_edge(h["int_num"], (4, 8))
    assert h["int_num_edge"] in ("inferior", "superior")
    assert fit(IPLSArm(int_num=4, glob_ncomp=3), problem).hyperparams["int_num_edge"] is None


@pytest.mark.skipif(not r_package("GA"), reason="pacote R GA indisponível")
def test_gapls_records_and_warns_an_edge_choice(problem):
    from tcc.arms.gapls import GAPLSArm
    cands = ((10, 5), (12, 6))
    with pytest.warns(GridEdgeWarning, match="população"):
        f = fit(GAPLSArm(n_components=3, candidates=cands), problem)
    h = f.hyperparams
    assert h["ga_config_edge"] == grid_edge((h["pop_size"], h["max_iter"]), cands)
    fixo = fit(GAPLSArm(ga_config=(10, 5), n_components=3), problem)
    assert fixo.hyperparams["ga_config_edge"] is None


# --- receita ----------------------------------------------------------------------------

def test_recipe_choice_records_its_edges():
    from tcc.arms.gate import ARTICLE
    from tcc.recipe_selection import CANDIDATES, CandidateResult, choose
    longa = next(c for c in CANDIDATES if c.max_epochs == 2000 and c.lr == 0.003)
    bom = CandidateResult(stop_rmse=[0.30, 0.31], dsg=[0.02, 0.03], best_epochs=[900, 1500])
    with pytest.warns(GridEdgeWarning):
        out = choose({longa: bom})
    assert out["edge"] == {"max_epochs": "superior", "lr": "superior"}
    with pytest.warns(GridEdgeWarning):
        out = choose({ARTICLE: CandidateResult(stop_rmse=[0.3, 0.3], dsg=[0.02, 0.03],
                                               best_epochs=[100, 150])})
    assert out["edge"] == {"max_epochs": "inferior", "lr": "inferior"}
    nada = choose({ARTICLE: CandidateResult(stop_rmse=[0.3, 0.3], dsg=[0.001, 0.1],
                                            best_epochs=[100, 150])})
    assert nada["edge"] is None


# --- o resumo ---------------------------------------------------------------------------

@dataclass
class R:
    dataset_name: str
    arm_name: str
    hyperparams: dict


def test_edge_summary_counts_edges_per_arm_and_key():
    rs = [R("mango", "vip_threshold", {"threshold_edge": "inferior", "n_bands": 140}),
          R("mango", "vip_threshold", {"threshold_edge": "inferior"}),
          R("mango", "vip_threshold", {"threshold_edge": None}),
          R("mango", "pls_full", {"n_components_edge": None}),
          R("tecator", "ipls", {"int_num_edge": "superior"})]
    assert edge_summary(rs) == {
        ("mango", "vip_threshold", "threshold_edge"): {"inferior": 2, "superior": 0, "total": 3},
        ("tecator", "ipls", "int_num_edge"): {"inferior": 0, "superior": 1, "total": 1},
    }
