"""Camada de seleção (Estágio 4; ADR 018)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from tcc.arms.gate import gate_prior, mlp_full
from tcc.arms.pls import PLSArm
from tcc.arms.vip import VIPArm
from tcc.data import load
from tcc.protocol import evaluate
from tcc.selection import CLASSICAL_SELECTION_ARMS, k_grid, paired_k, to_selection, top_k


@dataclass
class R:
    """O que a camada de seleção lê de um `Result`."""
    band_scores: np.ndarray | None = None
    selection: set[int] | None = None
    arm_name: str = "x"


# --- top-k -------------------------------------------------------------------

def test_top_k_picks_the_highest_scores():
    assert top_k(np.array([0.1, 0.9, 0.3, 0.8, 0.2]), 2) == {1, 3}


def test_top_k_breaks_ties_by_lowest_index():
    # Quatro bandas empatadas no topo, k = 2: ficam as de menor índice.
    s = np.array([0.0, 1.0, 1.0, 0.5, 1.0, 1.0])
    assert top_k(s, 2) == {1, 2}
    assert top_k(s, 4) == {1, 2, 4, 5}
    # e não depende da ordem em que os empates aparecem
    assert top_k(s[::-1], 2) == {0, 1}


def test_top_k_is_invariant_to_monotone_transforms():
    # A seleção é por ordem: escalar ou somar constante não muda nada.
    s = np.random.default_rng(0).uniform(size=50)
    assert top_k(s, 7) == top_k(3 * s + 2, 7) == top_k(np.exp(s), 7)


@pytest.mark.parametrize("k", [0, 6, -1])
def test_top_k_rejects_k_out_of_range(k):
    with pytest.raises(ValueError):
        top_k(np.arange(5.0), k)


def test_top_k_rejects_nan():
    with pytest.raises(ValueError):
        top_k(np.array([0.1, np.nan, 0.3]), 1)


# --- a regra do pipeline -------------------------------------------------------

def test_continuous_scores_use_top_k():
    # VIP e portas: escore contínuo -> top-k.
    assert to_selection(R(band_scores=np.array([0.2, 0.7, 0.1, 0.9])), 2) == {1, 3}


def test_scores_win_over_explicit_selection():
    # O VIP tem as duas coisas; o pipeline manda usar o escore.
    r = R(band_scores=np.array([0.2, 0.7, 0.1, 0.9]), selection={0, 2})
    assert to_selection(r, 2) == {1, 3}


def test_explicit_selection_is_kept_whatever_k():
    # iPLS, GA-PLS e CARS: o conjunto que o método escolheu, do tamanho dele.
    r = R(selection={3, 5, 8})
    assert to_selection(r, 1) == {3, 5, 8}
    assert to_selection(r, 10) == {3, 5, 8}


def test_arms_without_selection_are_excluded():
    assert to_selection(R(), 5) is None


def test_to_selection_does_not_alias_the_result():
    sel = {1, 2}
    out = to_selection(R(selection=sel), 3)
    out.add(99)
    assert sel == {1, 2}


# --- k pareado e faixa de sensibilidade ------------------------------------------

def test_paired_k_is_the_rounded_mean_of_classical_sizes():
    rs = [R(selection=set(range(10)), arm_name="ipls"),
          R(selection=set(range(5)), arm_name="cars"),
          R(selection=set(range(100)), arm_name="pls_full"),  # fora da conta
          R(band_scores=np.ones(4), arm_name="gate_prior")]   # fora da conta
    assert paired_k(rs) == 8  # (10 + 5) / 2 = 7,5 -> 8, e não 8 por acaso do banqueiro


def test_paired_k_rounds_half_up():
    rs = [R(selection=set(range(n)), arm_name="vip_threshold") for n in (2, 3)]
    assert paired_k(rs) == 3  # 2,5 -> 3 (round() do Python daria 2)


def test_paired_k_requires_classical_results():
    with pytest.raises(ValueError):
        paired_k([R(selection={1}, arm_name="gate_prior")])


def test_classical_arm_names_match_the_arms():
    # Se um braço mudar de nome, o k pareado deixaria de contá-lo em silêncio.
    from tcc.arms.cars import CARSArm
    from tcc.arms.gapls import GAPLSArm
    from tcc.arms.ipls import IPLSArm
    names = {IPLSArm().name, VIPArm().name, GAPLSArm().name, CARSArm().name}
    assert names == set(CLASSICAL_SELECTION_ARMS)
    assert CARSArm(mode="fiel").name not in CLASSICAL_SELECTION_ARMS  # ADR 016


def test_k_grid_spans_half_to_one_and_a_half():
    assert k_grid(20, 100) == [10, 15, 20, 25, 30]
    assert k_grid(3, 100) == [2, 3, 4, 5]  # 1,5 e 2,25 arredondam para 2
    assert k_grid(90, 100) == [45, 68, 90, 100]  # recortado em p


# --- o evaluate grava a seleção explícita --------------------------------------

@pytest.fixture(scope="module")
def tecator():
    return load("tecator")


def test_evaluate_records_the_explicit_selection(tecator):
    r = evaluate(VIPArm(), tecator, seed_split=0, seed_algo=0)
    assert isinstance(r.selection, set) and r.selection
    assert len(r.selection) == r.hyperparams["n_bands"]
    assert r.band_scores is not None


def test_evaluate_records_none_for_arms_that_do_not_select(tecator):
    for arm in (PLSArm(), mlp_full()):
        assert evaluate(arm, tecator, seed_split=0, seed_algo=0).selection is None


def test_gate_selection_is_the_top_k_of_the_final_gate(tecator):
    r = evaluate(gate_prior(), tecator, seed_split=0, seed_algo=0)
    assert r.selection is None and r.band_scores is not None
    sel = to_selection(r, 10)
    assert len(sel) == 10
    assert min(r.band_scores[list(sel)]) >= max(np.delete(r.band_scores, list(sel)))
