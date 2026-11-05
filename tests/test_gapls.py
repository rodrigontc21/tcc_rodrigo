"""Braço `ga_pls` (ADR 015)."""

from __future__ import annotations

import numpy as np
import pytest

from tcc.arms.base import Budget, CVFolds
from tcc.arms.gapls import (
    GAPLSArm,
    _CrossProducts,
    _fewest_bands_within_one_se,
    kernel_pls_rmse,
)
from tcc.arms.ipls import _fit_pls

N_FOLDS = 5


@pytest.fixture(scope="module")
def spectral_problem():
    """Espectros lisos com sinal em 10-14, como o do iPLS e o do VIP."""
    rng = np.random.default_rng(0)
    n, p = 80, 40
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 10:15].sum(axis=1) * 2.0 + 0.1 * rng.normal(size=n)
    folds: CVFolds = []
    for chunk in np.array_split(np.arange(n), N_FOLDS):
        folds.append((np.setdiff1d(np.arange(n), chunk), chunk))
    return X, y, folds


def _sklearn_rmse(X, y, tr, va, columns, h):
    model, cols, _ = _fit_pls(X[tr], y[tr], set(columns.tolist()), h)
    return float(np.sqrt(np.mean((y[va] - np.asarray(model.predict(X[va][:, cols])).ravel()) ** 2)))


# --- kernel PLS: sem R --------------------------------------------------------


@pytest.mark.parametrize("h", [1, 3, 6])
def test_kernel_rmse_equals_the_project_pls(spectral_problem, h):
    # A avaliação do GA tem que dar o mesmo RMSE do PLSRegression do A1.
    X, y, folds = spectral_problem
    rng = np.random.default_rng(1)
    tr, va = folds[2]
    P = _CrossProducts.of(X_tr=X[tr], y_tr=y[tr], X_va=X[va], y_va=y[va])
    for _ in range(10):
        columns = np.sort(rng.choice(X.shape[1], rng.integers(2, 30), replace=False))
        assert kernel_pls_rmse(P, columns, h) == pytest.approx(
            _sklearn_rmse(X, y, tr, va, columns, h), rel=1e-9
        )


def test_kernel_caps_components_at_the_number_of_columns(spectral_problem):
    X, y, folds = spectral_problem
    tr, va = folds[0]
    P = _CrossProducts.of(X_tr=X[tr], y_tr=y[tr], X_va=X[va], y_va=y[va])
    columns = np.array([3, 11, 12])
    assert kernel_pls_rmse(P, columns, 10) == pytest.approx(
        _sklearn_rmse(X, y, tr, va, columns, 3), rel=1e-9
    )


def test_tie_break_takes_fewest_bands_within_one_se():
    # Mínimo no índice 0 (0,50 ± 0,05): 0, 1 e 2 cabem; o 2 tem menos bandas.
    mean = np.array([0.50, 0.53, 0.54, 0.60])
    se = np.array([0.05, 0.01, 0.01, 0.01])
    bands = np.array([30.0, 20.0, 12.0, 5.0])
    assert _fewest_bands_within_one_se(mean, se, bands) == 2


# --- braço completo: precisa do R com o pacote GA -----------------------------


def _ga_available() -> bool:
    try:
        from rpy2.robjects.packages import importr

        importr("GA")
        return True
    except Exception:
        return False


needs_ga = pytest.mark.skipif(not _ga_available(), reason="pacote R 'GA' indisponível (ADR 015)")


@needs_ga
def test_fit_produces_selection_and_cv_selections(spectral_problem):
    X, y, folds = spectral_problem
    fitted = GAPLSArm(ga_config=(20, 10), n_components=3).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    assert len(fitted.cv_selections) == len(folds)
    assert all(fitted.cv_selections)
    assert fitted.selection
    assert fitted.hyperparams["pop_size"] == 20
    assert fitted.predict(X).shape == (X.shape[0],)


@needs_ga
def test_same_seed_algo_same_selection_and_different_seed_differs(spectral_problem):
    X, y, folds = spectral_problem

    def run(seed):
        return GAPLSArm(ga_config=(20, 10), n_components=3).fit(
            X, y, folds, np.random.default_rng(seed), Budget()
        )

    a, b, c = run(0), run(0), run(1)
    assert a.selection == b.selection and a.cv_selections == b.cv_selections
    assert a.cv_selections != c.cv_selections


@needs_ga
def test_final_selection_is_the_best_chromosome(spectral_problem, monkeypatch):
    # O defeito do plsVarSel::ga_pls: lá sai o cromossomo com mais bandas.
    # Aqui, o fitness da seleção devolvida tem que ser o melhor da execução
    # (o @fitnessValue do GA).
    import rpy2.robjects as ro

    X, y, folds = spectral_problem
    real = ro.r
    captured = {}

    def spy(code):
        fn = real(code)
        if code != "GA::ga":
            return fn

        def wrapper(*args, **kwargs):
            captured["ga"] = fn(*args, **kwargs)
            return captured["ga"]

        return wrapper

    monkeypatch.setattr(ro, "r", spy)
    bands = GAPLSArm()._run_ga(X, y, folds, 3, (20, 10), 11, Budget())
    best = float(np.asarray(real("function(g) g@fitnessValue")(captured["ga"]))[0])
    products = [
        _CrossProducts.of(X_tr=X[tr], y_tr=y[tr], X_va=X[va], y_va=y[va])
        for tr, va in folds
    ]
    ours = -np.mean([kernel_pls_rmse(P, np.array(sorted(bands)), 3) for P in products])
    assert ours == pytest.approx(best, rel=1e-9)


@needs_ga
def test_initial_population_starts_with_about_ten_percent_of_the_bands(monkeypatch):
    # Com maxiter = 1 o GA devolve a população inicial (sem operadores
    # genéticos). O padrão do pacote seria ~50%; o do braço é 10% (ADR 015).
    import rpy2.robjects as ro

    rng = np.random.default_rng(3)
    n, p = 60, 400
    X = rng.normal(size=(n, p))
    y = X[:, :5].sum(axis=1)
    folds = [(np.setdiff1d(np.arange(n), c), c) for c in np.array_split(np.arange(n), 4)]
    real = ro.r
    captured = {}

    def spy(code):
        fn = real(code)
        if code != "GA::ga":
            return fn

        def wrapper(*args, **kwargs):
            captured["ga"] = fn(*args, **kwargs)
            return captured["ga"]

        return wrapper

    monkeypatch.setattr(ro, "r", spy)
    GAPLSArm()._run_ga(X, y, folds, 2, (50, 1), 4, Budget())
    population = np.asarray(real("function(g) g@population")(captured["ga"]))
    assert population.shape == (50, p)
    assert population.mean() == pytest.approx(0.10, abs=0.01)


@needs_ga
def test_selection_is_fold_local(spectral_problem):
    from tests.test_selection_leakage import assert_selection_is_fold_local

    X, y, folds = spectral_problem
    assert_selection_is_fold_local(
        lambda: GAPLSArm(ga_config=(20, 10), n_components=3), X, y, folds
    )


class _LeakyGAPLSArm(GAPLSArm):
    """GA rodado uma vez sobre o treino inteiro e repetido em todos os folds."""

    name = "leaky_ga_pls"

    def _fold_selections(self, X_train, y_train, cv_folds, n_components, config, seeds, budget):
        bands = self._run_ga(X_train, y_train, cv_folds, n_components, config, seeds[0], budget)
        return [set(bands) for _ in cv_folds]


@needs_ga
def test_check_catches_ga_that_sees_the_validation_fold(spectral_problem):
    from tests.test_selection_leakage import assert_selection_is_fold_local

    X, y, folds = spectral_problem
    with pytest.raises(AssertionError, match="vazamento"):
        assert_selection_is_fold_local(
            lambda: _LeakyGAPLSArm(ga_config=(20, 10), n_components=3), X, y, folds
        )


@needs_ga
def test_budget_counts_one_pls_per_inner_fold_per_evaluation(spectral_problem):
    X, y, folds = spectral_problem
    budget = Budget()
    GAPLSArm()._run_ga(X, y, folds, 3, (20, 10), 5, budget)
    # no máximo popSize x maxiter avaliações, cada uma com len(folds) PLS
    assert 0 < budget.n_fits <= 20 * 10 * len(folds)
    assert budget.n_fits % len(folds) == 0


@needs_ga
def test_search_reports_the_chosen_config(spectral_problem):
    X, y, folds = spectral_problem
    fitted = GAPLSArm(n_components=3, candidates=((10, 5), (20, 10))).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    assert (fitted.hyperparams["pop_size"], fitted.hyperparams["max_iter"]) in {(10, 5), (20, 10)}
    assert np.isfinite(fitted.rmse_cv)
