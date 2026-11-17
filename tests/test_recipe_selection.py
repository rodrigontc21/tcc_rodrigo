"""A escolha da receita de treino (src/tcc/recipe_selection.py)."""

from __future__ import annotations

import pytest

from tcc.arms.gate import ARTICLE, TrainRecipe
from tcc.recipe_selection import (
    CANDIDATES,
    CandidateResult,
    admissible,
    choose,
    cost_key,
)

BOM_DSG = [0.02, 0.03, 0.04]          # faixa 2×
EPOCAS_BOAS = [120, 150, 180]
EPOCAS_LONGAS = [800, 1200, 1500]  # passam da paciência de qualquer candidato


def cand(lr, e, p):
    return next(c for c in CANDIDATES if (c.lr, c.max_epochs, c.patience) == (lr, e, p))


def res(rmse, dsg=BOM_DSG, epocas=EPOCAS_BOAS):
    return CandidateResult(stop_rmse=rmse, dsg=dsg, best_epochs=epocas)


# --- os candidatos declarados ------------------------------------------------------

def test_candidates_are_the_declared_single_batch_grid():
    assert len(CANDIDATES) == 8
    assert CANDIDATES[0] is ARTICLE
    assert all(c.batch_size is None for c in CANDIDATES)  # só lote único
    assert {(c.max_epochs, c.patience) for c in CANDIDATES} == {
        (200, 30), (500, 50), (1000, 100), (2000, 200)}
    assert {c.lr for c in CANDIDATES} == {0.01, 0.003}
    assert all(c.patience == max(30, c.max_epochs // 10) for c in CANDIDATES)
    assert len({c.name for c in CANDIDATES}) == 8


def test_cost_order_is_budget_then_patience_then_article_rate():
    ordem = sorted(CANDIDATES, key=cost_key)
    assert ordem[0] is ARTICLE
    assert ordem[1] == cand(0.003, 200, 30)
    assert [c.max_epochs for c in ordem] == [200, 200, 500, 500, 1000, 1000, 2000, 2000]


# --- admissibilidade ---------------------------------------------------------------

def test_dsg_range_up_to_five_times_is_admissible():
    assert admissible(ARTICLE, res([1, 1], dsg=[0.01, 0.05]))[0]
    ok, motivos = admissible(ARTICLE, res([1, 1], dsg=[0.01, 0.0501]))
    assert not ok and "faixa" in motivos[0]


def test_mango_like_dsg_range_is_rejected():
    ok, motivos = admissible(ARTICLE, res([1, 1], dsg=[0.0008, 0.0559]))
    assert not ok and "69.9×" in motivos[0]


def test_best_epoch_inside_the_patience_window_is_rejected():
    # A melhor época igual à paciência ainda é "dentro da janela".
    assert not admissible(ARTICLE, res([1, 1], epocas=[150, 30]))[0]
    assert admissible(ARTICLE, res([1, 1], epocas=[150, 31]))[0]
    longa = cand(0.01, 1000, 100)
    ok, motivos = admissible(longa, res([1, 1], epocas=[500, 100, 99]))
    assert not ok and "2 treino(s)" in motivos[0]


def test_missing_or_bad_dsg_is_rejected():
    for dsg in ([], [0.01, float("nan")], [0.0, 0.02]):
        assert not admissible(ARTICLE, res([1, 1], dsg=dsg))[0]


# --- a escolha -----------------------------------------------------------------------

def test_cheapest_within_one_se_wins_over_the_best():
    longa = cand(0.01, 2000, 200)
    media = cand(0.01, 500, 50)
    out = choose({
        longa: res([0.30, 0.32, 0.34], epocas=EPOCAS_LONGAS),   # melhor: média 0,32, erro-padrão ~0,0115
        media: res([0.31, 0.33, 0.35], epocas=EPOCAS_LONGAS),   # 0,33: dentro do limite e mais barato
        ARTICLE: res([0.50, 0.52, 0.54]),  # fora do limite
    })
    assert out["chosen"] == media
    assert out["limit"] == pytest.approx(0.32 + 0.02 / 3 ** 0.5)


def test_an_inadmissible_candidate_never_wins_nor_sets_the_limit():
    longa = cand(0.01, 2000, 200)
    out = choose({
        ARTICLE: res([0.10, 0.10, 0.10], epocas=[10, 150, 150]),  # o melhor, mas parou cedo
        longa: res([0.40, 0.42, 0.44], epocas=EPOCAS_LONGAS),
    })
    assert out["chosen"] == longa
    assert not out["table"][ARTICLE]["admissible"]
    assert out["limit"] == pytest.approx(0.42 + 0.02 / 3 ** 0.5)


def test_no_admissible_candidate_returns_none():
    out = choose({ARTICLE: res([0.1, 0.1], dsg=[0.001, 0.07])})
    assert out["chosen"] is None and out["limit"] is None


def test_same_budget_prefers_the_article_rate():
    lenta = cand(0.003, 200, 30)
    out = choose({lenta: res([0.30, 0.31]), ARTICLE: res([0.30, 0.31])})
    assert out["chosen"] is ARTICLE


def test_one_partition_is_not_enough():
    with pytest.raises(ValueError):
        choose({ARTICLE: res([0.3])})


def test_recipe_name_is_kept_for_the_article_and_set_for_the_others():
    # A receita do artigo deixa o nome do braço sem sufixo (ADR 017).
    assert ARTICLE.name == "artigo"
    assert cand(0.003, 1000, 100).name == "lr0.003_e1000_p100"
    assert isinstance(cand(0.003, 1000, 100), TrainRecipe)


def test_same_budget_prefers_the_smaller_patience():
    curta = TrainRecipe(name="p50", max_epochs=500, patience=50, lr=0.003)
    longa = TrainRecipe(name="p100", max_epochs=500, patience=100, lr=0.01)
    assert sorted([longa, curta], key=cost_key) == [curta, longa]
