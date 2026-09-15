from __future__ import annotations

import numpy as np
import pytest
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds
from tcc.arms.pls import PLSArm


def _make_folds(n: int, k: int, seed: int) -> CVFolds:
    """Folds no mesmo formato que `evaluate` injeta no braço."""
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(n)
    sizes = np.full(k, n // k, dtype=int)
    sizes[: n % k] += 1

    folds: CVFolds = []
    start = 0
    for size in sizes:
        val_idx = permutation[start : start + size]
        train_idx = np.concatenate([permutation[:start], permutation[start + size :]])
        folds.append((np.sort(train_idx), np.sort(val_idx)))
        start += size
    return folds


@pytest.fixture
def flat_curve_problem():
    """Dados com 2 fatores latentes reais e ruído: a curva de erro da CV
    fica plana depois do 2º componente, que é justamente o regime em que
    argmin puro e regra de um erro-padrão divergem."""
    rng = np.random.default_rng(0)
    n, p = 60, 30
    scores = rng.normal(size=(n, 2))
    loadings = rng.normal(size=(2, p))
    X = scores @ loadings + 0.35 * rng.normal(size=(n, p))
    y = 3.0 * scores[:, 0] - 1.5 * scores[:, 1] + 0.6 * rng.normal(size=n)
    return X, y, _make_folds(n, 5, seed=0)


def _argmin_choice(X, y, folds, candidates) -> tuple[int, float]:
    """Reimplementa o critério ANTIGO (argmin puro do RMSE médio) para
    servir de referência na comparação — o teste compara as duas regras
    sobre exatamente a mesma curva."""
    means = []
    for n_components in candidates:
        fold_rmses = [
            float(
                np.sqrt(
                    np.mean(
                        (
                            y[val]
                            - np.asarray(
                                PLSRegression(n_components=n_components)
                                .fit(X[tr], y[tr])
                                .predict(X[val])
                            ).ravel()
                        )
                        ** 2
                    )
                )
            )
            for tr, val in folds
        ]
        means.append(float(np.mean(fold_rmses)))
    means = np.asarray(means)
    i = int(np.argmin(means))
    return candidates[i], float(means[i])


def test_one_se_rule_picks_simpler_model_than_argmin(flat_curve_problem):
    """A regra de um erro-padrão escolhe um modelo ESTRITAMENTE mais
    simples que o argmin puro quando a curva de erro é plana perto do
    mínimo. Sem isso, o PLS persegue ruído (sintoma: n_components
    oscilando entre seed_split) e deixa de ser o mesmo objeto que o PLS
    do artigo de referência."""
    X, y, folds = flat_curve_problem
    arm = PLSArm()

    chosen, rmse_cv = arm._search(X, y, folds, Budget())
    argmin_n, argmin_rmse = _argmin_choice(X, y, folds, arm._candidates(X, folds))

    # O cenário precisa de fato discriminar as duas regras...
    assert argmin_n > chosen, (
        f"cenário não discrimina: argmin={argmin_n}, um-erro-padrão={chosen}"
    )
    # ...e o modelo mais simples continua dentro de um erro-padrão do
    # melhor, ou seja, não foi escolhido por ser pior.
    assert rmse_cv >= argmin_rmse
    assert chosen >= 1


def test_one_se_choice_stays_within_one_standard_error(flat_curve_problem):
    """O candidato escolhido respeita o limiar da regra: RMSE médio dele
    ≤ RMSE médio do mínimo + erro-padrão do mínimo."""
    X, y, folds = flat_curve_problem
    arm = PLSArm()
    candidates = arm._candidates(X, folds)

    per_candidate = []
    for n_components in candidates:
        fold_rmses = np.asarray(
            [
                float(
                    np.sqrt(
                        np.mean(
                            (
                                y[val]
                                - np.asarray(
                                    PLSRegression(n_components=n_components)
                                    .fit(X[tr], y[tr])
                                    .predict(X[val])
                                ).ravel()
                            )
                            ** 2
                        )
                    )
                )
                for tr, val in folds
            ]
        )
        per_candidate.append(
            (fold_rmses.mean(), fold_rmses.std(ddof=1) / np.sqrt(len(fold_rmses)))
        )

    means = np.asarray([m for m, _ in per_candidate])
    ses = np.asarray([s for _, s in per_candidate])
    i_min = int(np.argmin(means))
    threshold = means[i_min] + ses[i_min]

    chosen, rmse_cv = arm._search(X, y, folds, Budget())
    assert rmse_cv <= threshold + 1e-12
    # e é o MENOR candidato que cabe no limiar
    smallest_within = candidates[int(np.argmax(means <= threshold))]
    assert chosen == smallest_within


def test_fixed_n_components_skips_search(flat_curve_problem):
    """Com H fixo não há busca: rmse_cv é nan e o orçamento gasta 1 ajuste
    (o modo usado pelo portão de validação contra a literatura)."""
    X, y, folds = flat_curve_problem
    budget = Budget()
    fitted = PLSArm(n_components=3).fit(X, y, folds, np.random.default_rng(0), budget)

    assert fitted.hyperparams == {"n_components": 3}
    assert np.isnan(fitted.rmse_cv)
    assert budget.n_fits == 1
