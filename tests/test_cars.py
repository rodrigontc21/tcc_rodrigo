"""Braço `cars` (ADR 016)."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds
from tcc.arms.cars import (
    FAITHFUL_CONFIG,
    CARSArm,
    _matlab_round,
    coef_path,
    edf_kept,
    run_cars,
    subset_rmsecv,
)

N_FOLDS = 5


@pytest.fixture(scope="module")
def spectral_problem():
    """Espectros lisos com sinal em 10-14, como o do iPLS, do VIP e do GA."""
    rng = np.random.default_rng(0)
    n, p = 80, 40
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 10:15].sum(axis=1) * 2.0 + 0.1 * rng.normal(size=n)
    folds: CVFolds = []
    for chunk in np.array_split(np.arange(n), N_FOLDS):
        folds.append((np.setdiff1d(np.arange(n), chunk), chunk))
    return X, y, folds


# --- EDF (eqs. 4 a 6 do artigo) ------------------------------------------------


def test_matlab_round_takes_half_up():
    # O round do numpy levaria 2,5 a 2 (metade para o par).
    assert [_matlab_round(x) for x in (2.5, 3.5, 2.49, 0.5)] == [3, 4, 2, 1]


@pytest.mark.parametrize("p, n_runs", [(100, 50), (401, 100), (1870, 50), (40, 10)])
def test_edf_goes_from_all_bands_to_two(p, n_runs):
    # r_1 = 1 e r_N = 2/p. A execução i corta para r_(i+1), então
    # "run = 0" é r_1 (todas) e "run = N-1" é r_N (duas).
    assert edf_kept(p, n_runs, 0) == p
    assert edf_kept(p, n_runs, n_runs - 1) == 2
    kept = [edf_kept(p, n_runs, i) for i in range(1, n_runs + 1)]
    assert all(a >= b for a, b in zip(kept, kept[1:]))


def test_edf_matches_the_carspls_formula():
    # Transcrição direta do carspls.m: b=log(r0/r1)/(num-1); a=r0*exp(b);
    # ratio=a*exp(-b*(iter+1)); K=round(Nx*ratio).
    p, num = 100, 50
    b = np.log(1 / (2 / p)) / (num - 1)
    a = np.exp(b)
    for it in range(1, num + 1):
        assert edf_kept(p, num, it) == max(1, _matlab_round(p * a * np.exp(-b * (it + 1))))


# --- PLS centrado e RMSECV -------------------------------------------------------


def test_coef_path_equals_fitting_each_number_of_components(spectral_problem):
    X, y, _ = spectral_problem
    path = coef_path(PLSRegression(n_components=6, scale=False).fit(X, y))
    for a in range(1, 7):
        direct = np.ravel(PLSRegression(n_components=a, scale=False).fit(X, y).coef_)
        np.testing.assert_allclose(path[:, a - 1], direct, rtol=1e-8, atol=1e-10)


def test_subset_rmsecv_is_pooled_press_of_centered_pls(spectral_problem):
    X, y, folds = spectral_problem
    columns = np.array([2, 10, 11, 12, 13, 14, 30])
    rmsecv, n_comp = subset_rmsecv(
        X=X, y=y, columns=columns, max_ncomp=5, folds=folds, budget=Budget()
    )
    curve = []
    for a in range(1, 6):
        press = 0.0
        for tr, va in folds:
            model = PLSRegression(n_components=a, scale=False).fit(X[tr][:, columns], y[tr])
            press += float(np.sum((y[va] - np.ravel(model.predict(X[va][:, columns]))) ** 2))
        curve.append(np.sqrt(press / len(y)))
    assert rmsecv == pytest.approx(min(curve), rel=1e-9)
    assert n_comp == int(np.argmin(curve)) + 1


def test_subset_rmsecv_caps_components_at_the_number_of_columns(spectral_problem):
    X, y, folds = spectral_problem
    budget = Budget()
    _, n_comp = subset_rmsecv(
        X=X, y=y, columns=np.array([10, 12]), max_ncomp=8, folds=folds, budget=budget
    )
    assert n_comp <= 2
    assert budget.n_fits == 2 * len(folds)


# --- o algoritmo -----------------------------------------------------------------


def _run(spectral_problem, seed, n_runs=30, ratio=0.9):
    X, y, folds = spectral_problem
    return run_cars(
        X=X, y=y, folds=folds, n_runs=n_runs, ratio=ratio, max_ncomp=5,
        rng=np.random.default_rng(seed), budget=Budget(),
    )


@pytest.mark.parametrize("n_runs, ratio", [(1, 0.9), (10, 0.0), (10, 1.5)])
def test_run_cars_refuses_invalid_settings(spectral_problem, n_runs, ratio):
    X, y, folds = spectral_problem
    with pytest.raises(ValueError):
        run_cars(
            X=X, y=y, folds=folds, n_runs=n_runs, ratio=ratio, max_ncomp=3,
            rng=np.random.default_rng(0), budget=Budget(),
        )


def test_first_run_uses_all_bands_and_subsets_only_shrink(spectral_problem):
    run = _run(spectral_problem, 0)
    assert len(run.subsets) == 30
    assert len(run.subsets[0]) == spectral_problem[0].shape[1]
    for a, b in zip(run.subsets, run.subsets[1:]):
        assert set(b) <= set(a)


def test_weight_models_use_a_monte_carlo_sample_of_the_rows(spectral_problem, monkeypatch):
    # Passo 1 do artigo: cada PLS de pesos usa floor(n·razão) linhas
    # sorteadas, e sorteios diferentes a cada execução.
    import tcc.arms.cars as cars

    X, y, folds = spectral_problem
    real = cars._centered_pls
    seen = []

    def spy(Xs, ys, n_components):
        seen.append(ys.copy())
        return real(Xs, ys, n_components)

    monkeypatch.setattr(cars, "_centered_pls", spy)
    run_cars(
        X=X, y=y, folds=folds, n_runs=5, ratio=0.9, max_ncomp=3,
        rng=np.random.default_rng(0), budget=Budget(),
    )
    # 0,9 dá 72 linhas; os ajustes da CV usam 64 (4 de 5 blocos de 16)
    weight_fits = [s for s in seen if len(s) == int(np.floor(len(y) * 0.9))]
    assert len(weight_fits) == 5
    assert len({tuple(np.round(s, 12)) for s in weight_fits}) == 5


def test_each_subset_respects_the_edf_cap(spectral_problem):
    run = _run(spectral_problem, 0)
    p = spectral_problem[0].shape[1]
    for i, subset in enumerate(run.subsets[1:], start=1):
        assert len(subset) <= edf_kept(p, 30, i)


def test_chosen_subset_has_the_lowest_rmsecv(spectral_problem):
    run = _run(spectral_problem, 0)
    assert run.best == int(np.argmin(run.rmsecv))
    assert run.selection == set(run.subsets[run.best].tolist())


def test_same_seed_same_path_and_different_seed_differs(spectral_problem):
    a, b, c = _run(spectral_problem, 0), _run(spectral_problem, 0), _run(spectral_problem, 1)
    assert all(np.array_equal(s, t) for s, t in zip(a.subsets, b.subsets))
    assert not all(np.array_equal(s, t) for s, t in zip(a.subsets, c.subsets))


@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_selection_concentrates_on_the_signal_bands(spectral_problem, sign):
    # O sinal está em 10-14. A seleção tem que ficar majoritariamente perto
    # dele (vizinhas entram por colinearidade dos espectros lisos). Com o
    # sinal negativo, os coeficientes ficam negativos: o peso é |b| (eq. 3).
    X, y, folds = spectral_problem
    for seed in range(5):
        chosen = _run((X, sign * y, folds), seed).selection
        near = {j for j in chosen if 8 <= j <= 16}
        assert len(near) / len(chosen) >= 0.5, (sign, seed, sorted(chosen))


# --- o braço ----------------------------------------------------------------------


def test_protocol_mode_delivers_the_autoscaled_pls(spectral_problem):
    X, y, folds = spectral_problem
    fitted = CARSArm(cars_config=(20, 0.8, 1), n_components=4).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    assert fitted._model.scale is True
    assert len(fitted.cv_selections) == len(folds) and all(fitted.cv_selections)
    assert fitted.hyperparams["mode"] == "protocolo"
    assert (fitted.hyperparams["n_runs"], fitted.hyperparams["ratio"]) == (20, 0.8)
    assert fitted.hyperparams["ncomp_ceiling"] == 4  # fator 1 x n_components 4
    # o modelo final usa os componentes que o CARS escolheu, até o teto
    assert fitted.hyperparams["n_components"] <= 4
    assert fitted.predict(X).shape == (X.shape[0],)


def test_faithful_mode_is_centered_with_fixed_config(spectral_problem):
    X, y, folds = spectral_problem
    arm = CARSArm(mode="fiel", n_components=4)
    fitted = arm.fit(X, y, folds, np.random.default_rng(0), Budget())
    assert fitted._model.scale is False
    n_runs, ratio, factor = FAITHFUL_CONFIG
    assert (fitted.hyperparams["n_runs"], fitted.hyperparams["ratio"]) == (n_runs, ratio)
    assert fitted.hyperparams["ncomp_ceiling"] == factor * 4
    assert fitted.hyperparams["n_components"] <= factor * 4
    assert arm.name == "cars_fiel(n_components=4)"


def test_final_model_uses_the_components_cars_chose_not_the_ceiling(spectral_problem):
    X, y, folds = spectral_problem
    fitted = CARSArm(cars_config=(20, 0.9, 3), n_components=4).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    h = fitted.hyperparams
    assert h["ncomp_ceiling"] == 12
    assert h["n_components"] == min(h["cars_best_ncomp"], h["n_bands"])
    assert h["n_components"] < h["ncomp_ceiling"]


def test_ceiling_is_factor_times_a1_capped_by_the_pls_search(spectral_problem):
    X, y, folds = spectral_problem
    # 40 bandas e folds de 64 linhas: o teto da busca do PLSArm é 40
    assert CARSArm._ceiling(3, 2, X, folds) == 6
    assert CARSArm._ceiling(15, 3, X, folds) == 40


def test_faithful_mode_refuses_a_config():
    with pytest.raises(ValueError, match="fiel"):
        CARSArm(mode="fiel", cars_config=(50, 0.8, 1))
    with pytest.raises(ValueError, match="fator"):
        CARSArm(cars_config=(50, 0.8))
    with pytest.raises(ValueError, match="modo"):
        CARSArm(mode="outro")


def test_search_reports_the_chosen_config(spectral_problem):
    X, y, folds = spectral_problem
    candidates = ((10, 0.8, 1), (20, 0.9, 2))
    fitted = CARSArm(n_components=4, candidates=candidates).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    chosen = (
        fitted.hyperparams["n_runs"],
        fitted.hyperparams["ratio"],
        fitted.hyperparams["ncomp_factor"],
    )
    assert chosen in candidates
    assert fitted.hyperparams["ncomp_ceiling"] == chosen[2] * 4
    assert np.isfinite(fitted.rmse_cv)


def test_same_seed_algo_same_selection_and_different_seed_differs(spectral_problem):
    X, y, folds = spectral_problem

    def fit(seed):
        return CARSArm(cars_config=(20, 0.8, 1), n_components=4).fit(
            X, y, folds, np.random.default_rng(seed), Budget()
        )

    a, b, c = fit(0), fit(0), fit(1)
    assert a.selection == b.selection and a.cv_selections == b.cv_selections
    assert a.cv_selections != c.cv_selections


def test_budget_counts_weight_fits_and_cv_fits(spectral_problem):
    X, y, folds = spectral_problem
    budget = Budget()
    run = run_cars(
        X=X, y=y, folds=folds, n_runs=10, ratio=0.9, max_ncomp=3,
        rng=np.random.default_rng(0), budget=budget,
    )
    # 10 ajustes de peso, e por subconjunto até 3 componentes em cada fold
    upper = 10 + 10 * 3 * len(folds)
    lower = 10 + 10 * len(folds)
    assert lower <= budget.n_fits <= upper
    assert len(run.subsets) == 10


@pytest.mark.parametrize("mode", ["protocolo", "fiel"])
def test_selection_is_fold_local(spectral_problem, mode):
    from tests.test_selection_leakage import assert_selection_is_fold_local

    X, y, folds = spectral_problem
    config = {"cars_config": (20, 0.8, 1)} if mode == "protocolo" else {}
    assert_selection_is_fold_local(
        lambda: CARSArm(mode=mode, n_components=4, **config), X, y, folds
    )


class _LeakyCARSArm(CARSArm):
    """CARS rodado uma vez sobre o treino inteiro e repetido em todos os folds."""

    name = "leaky_cars"

    def _fold_runs(self, X_train, y_train, cv_folds, base, config, seeds, budget):
        run = run_cars(
            X=X_train, y=y_train, folds=cv_folds, n_runs=config[0], ratio=config[1],
            max_ncomp=self._ceiling(base, config[2], X_train, cv_folds),
            rng=np.random.default_rng(seeds[0]), budget=budget,
        )
        return [run for _ in cv_folds]


def test_check_catches_cars_that_sees_the_validation_fold(spectral_problem):
    from tests.test_selection_leakage import assert_selection_is_fold_local

    X, y, folds = spectral_problem
    with pytest.raises(AssertionError, match="vazamento"):
        assert_selection_is_fold_local(
            lambda: _LeakyCARSArm(cars_config=(20, 0.8, 1), n_components=4), X, y, folds
        )
