"""Braço `vip_threshold` (ADR 014)."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds
from tcc.arms.ipls import _fit_pls
from tcc.arms.vip import VIPArm, vip_scores
from tests.test_selection_leakage import assert_selection_is_fold_local

N_FOLDS = 5


@pytest.fixture(scope="module")
def spectral_problem():
    """Espectros lisos com sinal em 10-14, como o do iPLS."""
    rng = np.random.default_rng(0)
    n, p = 80, 40
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 10:15].sum(axis=1) * 2.0 + 0.1 * rng.normal(size=n)
    folds: CVFolds = []
    for chunk in np.array_split(np.arange(n), N_FOLDS):
        folds.append((np.setdiff1d(np.arange(n), chunk), chunk))
    return X, y, folds


def test_mean_of_squared_vip_is_one(spectral_problem):
    # A propriedade de onde vem a convenção do limiar 1.
    X, y, _ = spectral_problem
    for h in (1, 3, 6):
        vip = vip_scores(PLSRegression(n_components=h).fit(X, y))
        assert vip.shape == (X.shape[1],)
        assert np.mean(vip**2) == pytest.approx(1.0, abs=1e-12)


def test_vip_matches_the_formula_written_by_hand(spectral_problem):
    # Um laço por banda e por componente, sem álgebra matricial: se a versão
    # vetorizada trocar eixo ou normalização, os dois divergem.
    X, y, _ = spectral_problem
    model = PLSRegression(n_components=4).fit(X, y)
    W, T = model.x_weights_, model.x_scores_
    q = np.asarray(model.y_loadings_).ravel()
    p, h = W.shape
    ss = [q[a] ** 2 * float(T[:, a] @ T[:, a]) for a in range(h)]
    expected = []
    for j in range(p):
        num = sum(ss[a] * (W[j, a] / np.linalg.norm(W[:, a])) ** 2 for a in range(h))
        expected.append(np.sqrt(p * num / sum(ss)))
    np.testing.assert_allclose(vip_scores(model), expected, rtol=1e-12)


def test_vip_highlights_the_informative_bands(spectral_problem):
    X, y, _ = spectral_problem
    vip = vip_scores(PLSRegression(n_components=3).fit(X, y))
    assert set(np.argsort(vip)[-5:]) & set(range(10, 15))


def test_fit_produces_selection_scores_and_cv_selections(spectral_problem):
    X, y, folds = spectral_problem
    fitted = VIPArm(threshold=1.0, n_components=3).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    assert len(fitted.cv_selections) == len(folds)
    assert all(fitted.cv_selections)
    assert fitted.band_scores.shape == (X.shape[1],)
    assert fitted.selection == set(np.flatnonzero(fitted.band_scores >= 1.0))
    assert fitted.hyperparams["threshold"] == 1.0
    assert fitted.predict(X).shape == (X.shape[0],)


def test_selection_is_fold_local(spectral_problem):
    X, y, folds = spectral_problem
    assert_selection_is_fold_local(
        lambda: VIPArm(threshold=1.0, n_components=3), X, y, folds
    )


class _LeakyVIPArm(VIPArm):
    """VIP calculado sobre o treino inteiro e repetido em todos os folds."""

    name = "leaky_vip"

    def _fold_vips(self, X_train, y_train, cv_folds, n_components, budget):
        model = PLSRegression(n_components=n_components).fit(X_train, y_train)
        budget.increment()
        return [vip_scores(model) for _ in cv_folds]


def test_check_catches_vip_that_sees_the_validation_fold(spectral_problem):
    # Sem este, o teste acima poderia passar por construção.
    X, y, folds = spectral_problem
    with pytest.raises(AssertionError, match="vazamento"):
        assert_selection_is_fold_local(
            lambda: _LeakyVIPArm(threshold=1.0, n_components=3), X, y, folds
        )


def test_search_takes_the_largest_threshold_within_one_se(spectral_problem):
    # Refaz a curva por fora e confere a regra: entre os limiares dentro de
    # um erro-padrão do mínimo, fica o MAIOR (menos bandas).
    X, y, folds = spectral_problem
    candidates = (0.8, 1.0, 1.2, 1.5)
    h = 3
    vips = [
        vip_scores(PLSRegression(n_components=h).fit(X[tr], y[tr])) for tr, _ in folds
    ]
    means, ses = [], []
    for t in candidates:
        rmses = []
        for (tr, val), vip in zip(folds, vips):
            bands = set(np.flatnonzero(vip >= t).tolist())
            if not bands:
                rmses = None
                break
            model, cols, _ = _fit_pls(X[tr], y[tr], bands, h)
            y_hat = np.asarray(model.predict(X[val][:, cols])).ravel()
            rmses.append(np.sqrt(np.mean((y[val] - y_hat) ** 2)))
        if rmses is None:
            means.append(np.inf)
            ses.append(0.0)
        else:
            means.append(np.mean(rmses))
            ses.append(np.std(rmses, ddof=1) / np.sqrt(len(rmses)))
    means, ses = np.asarray(means), np.asarray(ses)
    i_min = int(np.argmin(means))
    within = [t for t, m in zip(candidates, means) if m <= means[i_min] + ses[i_min]]

    fitted = VIPArm(n_components=h, candidates=candidates).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    assert fitted.hyperparams["threshold"] == max(within)


def test_tie_break_picks_the_largest_threshold_within_the_limit():
    # Curva montada à mão: mínimo no índice 1 (0,50 ± 0,05). Os índices 1,
    # 2 e 3 cabem no limite 0,55; o 4 não; o 0, que é menor, também cabe,
    # mas o desempate vai para o MAIOR limiar que cabe, o índice 3.
    from tcc.arms.vip import _largest_within_one_se

    mean = np.array([0.54, 0.50, 0.52, 0.55, 0.60])
    se = np.array([0.01, 0.05, 0.01, 0.01, 0.01])
    assert _largest_within_one_se(mean, se) == 3
    # descartado (inf) nunca é escolhido, mesmo sendo o último
    assert _largest_within_one_se(np.array([0.5, 0.5, np.inf]), np.zeros(3)) == 1


def test_band_exactly_at_the_threshold_is_selected():
    # O limiar é inclusivo: VIP >= limiar (ADR 014).
    from tcc.arms.vip import _select

    assert _select(np.array([0.5, 1.0, 1.5]), 1.0) == {1, 2}


def test_vip_does_not_depend_on_the_scale_of_each_weight_vector(spectral_problem):
    # A fórmula normaliza cada w_a. O sklearn já entrega norma 1, então a
    # normalização só importa se os pesos vierem de outra fonte; este teste
    # é o que a protege.
    from types import SimpleNamespace

    X, y, _ = spectral_problem
    m = PLSRegression(n_components=3).fit(X, y)
    stretched = SimpleNamespace(
        x_weights_=m.x_weights_ * np.array([3.0, 0.2, 7.0]),
        x_scores_=m.x_scores_,
        y_loadings_=m.y_loadings_,
    )
    np.testing.assert_allclose(vip_scores(stretched), vip_scores(m), rtol=1e-12)


def test_threshold_that_empties_a_fold_is_never_chosen(spectral_problem):
    # Limiar 50 deixa todo fold sem banda: tem que ser descartado, sem quebrar.
    X, y, folds = spectral_problem
    fitted = VIPArm(n_components=3, candidates=(1.0, 50.0)).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    assert fitted.hyperparams["threshold"] == 1.0


def test_budget_counts_every_pls_fit(spectral_problem):
    # Com H fixo: 1 PLS por fold para o VIP, 1 por fold e por limiar na
    # busca, o PLS do VIP final e o PLS entregue.
    X, y, folds = spectral_problem
    budget = Budget()
    VIPArm(n_components=3, candidates=(0.8, 1.0)).fit(
        X, y, folds, np.random.default_rng(0), budget
    )
    assert budget.n_fits == len(folds) + 2 * len(folds) + 1 + 1


def test_searched_n_components_is_the_one_se_value(spectral_problem):
    from tcc.arms.pls import PLSArm

    X, y, folds = spectral_problem
    expected, _ = PLSArm()._search(X, y, folds, Budget())
    fitted = VIPArm(threshold=1.0).fit(X, y, folds, np.random.default_rng(0), Budget())
    assert fitted.hyperparams["vip_ncomp"] == expected
