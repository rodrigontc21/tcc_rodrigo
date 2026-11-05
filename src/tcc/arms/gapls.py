"""Braço `ga_pls`: PLS sobre as bandas escolhidas por algoritmo genético
(ADR 015).

O motor genético é o `GA::ga` do R (Scrucca 2013), via `rpy2`. A avaliação
de cada cromossomo é deste módulo, e não a do `plsVarSel::ga_pls`, que tem
os defeitos registrados no DIARIO de 29/10 (`scripts/verificar_ga_pls_plsvarsel.py`).

A avaliação usa kernel PLS (Dayal e MacGregor 1997) sobre os produtos
cruzados X'X e X'y de cada fold, calculados uma vez com todas as bandas.
Avaliar um subconjunto vira recortar essas matrizes, e o custo deixa de
depender do número de amostras. O resultado é o mesmo do `PLSRegression`
autoescalado do A1 (conferido em `tests/test_gapls.py`). O modelo entregue
continua sendo o `PLSRegression`, pelo mesmo `_fit_pls` do iPLS e do VIP.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds
from tcc.arms.ipls import _fit_pls, _inner_folds
from tcc.arms.pls import PLSArm

# (tamanho da população, máximo de gerações), declarados a priori no ADR 015.
# O segundo é o padrão do pacote GA; o primeiro, uma busca menor.
DEFAULT_GA_CANDIDATES = ((30, 50), (50, 100))

# Chance de cada banda começar selecionada. O padrão do GA é 0,5, e com ele
# o braço terminava com 38 a 49% das bandas nos quatro conjuntos (DIARIO de
# 29/10): a mutação troca um bit por vez e não consegue descer. 0,1 fica
# entre o padrão do plsVarSel (1 para 10, ~9%) e o valor ajustado em Mehmood
# et al. 2020 (~11%). ADR 015.
DEFAULT_INITIAL_DENSITY = 0.1


def _r():
    """Importa o GA sob demanda, como o `_r` do iPLS."""
    import rpy2.rinterface as ri
    import rpy2.robjects as ro
    from rpy2.robjects.packages import importr

    importr("GA")
    return ri, ro


@dataclass(frozen=True)
class _CrossProducts:
    """Produtos cruzados de um fold, com todas as bandas.

    Treino autoescalado com a média e o desvio do próprio treino, como o
    `PLSRegression`; a validação usa os mesmos parâmetros do treino.
    """

    C: np.ndarray  # Z_tr' Z_tr
    c: np.ndarray  # Z_tr' y_tr
    G: np.ndarray  # Z_va' Z_va
    g: np.ndarray  # Z_va' (y_va - média de y_tr)
    s: float  # ||y_va - média de y_tr||²
    n_train: int
    n_val: int

    @classmethod
    def of(cls, X_tr, y_tr, X_va, y_va) -> _CrossProducts:
        mean, std = X_tr.mean(axis=0), X_tr.std(axis=0, ddof=1)
        std = np.where(std == 0, 1.0, std)
        y_mean = y_tr.mean()
        Z_tr, Z_va = (X_tr - mean) / std, (X_va - mean) / std
        e_tr, e_va = y_tr - y_mean, y_va - y_mean
        return cls(
            C=Z_tr.T @ Z_tr,
            c=Z_tr.T @ e_tr,
            G=Z_va.T @ Z_va,
            g=Z_va.T @ e_va,
            s=float(e_va @ e_va),
            n_train=len(y_tr),
            n_val=len(y_va),
        )


def kernel_pls_rmse(P: _CrossProducts, columns: np.ndarray, n_components: int) -> float:
    """RMSE de validação de um PLS de resposta única ajustado só em `columns`.

    Kernel PLS, algoritmo 1 de Dayal e MacGregor (1997): pesos e rotações
    saem de X'X e X'y, sem deflacionar X. O número de componentes é
    recortado como no `_fit_pls`.
    """
    C = P.C[np.ix_(columns, columns)]
    c = P.c[columns].copy()
    h = max(1, min(n_components, len(columns), P.n_train - 1))
    R = np.empty((len(columns), h))
    loadings = np.empty((len(columns), h))
    q = np.empty(h)
    for a in range(h):
        w = c / np.linalg.norm(c)
        r = w - R[:, :a] @ (loadings[:, :a].T @ w)
        Cr = C @ r
        tt = r @ Cr
        loadings[:, a] = Cr / tt
        q[a] = (c @ r) / tt
        c = c - loadings[:, a] * q[a] * tt
        R[:, a] = r
    B = R @ q
    G = P.G[np.ix_(columns, columns)]
    sse = P.s - 2.0 * B @ P.g[columns] + B @ G @ B
    return float(np.sqrt(max(sse, 0.0) / P.n_val))


@dataclass(frozen=True)
class _FittedGAPLSArm:
    _model: PLSRegression
    _columns: np.ndarray
    _hyperparams: dict
    _rmse_cv: float
    _cv_selections: list[set[int]]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X[:, self._columns])).ravel()

    @property
    def band_scores(self) -> np.ndarray | None:
        # O GA devolve um conjunto, não um ranking (como o iPLS).
        return None

    @property
    def hyperparams(self) -> dict:
        return self._hyperparams

    @property
    def rmse_cv(self) -> float:
        return self._rmse_cv

    @property
    def cv_selections(self) -> list[set[int]] | None:
        return self._cv_selections

    @property
    def selection(self) -> set[int]:
        """Bandas do ajuste final, para o Estágio 4."""
        return {int(j) for j in self._columns}


class GAPLSArm:
    """Braço `ga_pls`.

    `ga_config=None` (padrão) escolhe (população, gerações) por validação
    cruzada entre `candidates`. `n_components=None` busca o número de
    componentes pela regra de um erro-padrão do `PLSArm`, como o iPLS e o
    VIP. Os dois vão fixos no verificador anti-vazamento (ADR 011).

    A seleção é aninhada: em cada fold, o GA só vê `fold_train`, e a
    avaliação interna usa os outros blocos do protocolo (`_inner_folds`),
    que respeitam os grupos do ADR 009.
    """

    def __init__(
        self,
        ga_config: tuple[int, int] | None = None,
        n_components: int | None = None,
        candidates: tuple[tuple[int, int], ...] = DEFAULT_GA_CANDIDATES,
        initial_density: float = DEFAULT_INITIAL_DENSITY,
    ):
        self._fixed_config = ga_config
        self._fixed_n_components = n_components
        self._candidates = candidates
        self._initial_density = initial_density
        parts = []
        if ga_config is not None:
            parts.append(f"ga_config={ga_config}")
        if n_components is not None:
            parts.append(f"n_components={n_components}")
        self.name = "ga_pls" if not parts else f"ga_pls({', '.join(parts)})"

    def _ga_ncomp(self, X_train, y_train, cv_folds, budget) -> int:
        if self._fixed_n_components is not None:
            return self._fixed_n_components
        n_components, _ = PLSArm()._search(X_train, y_train, cv_folds, budget)
        return n_components

    def _run_ga(
        self,
        X: np.ndarray,
        y: np.ndarray,
        inner_folds: CVFolds,
        n_components: int,
        config: tuple[int, int],
        seed: int,
        budget: Budget,
    ) -> set[int]:
        """Uma execução do GA sobre (X, y), avaliando nas `inner_folds`.

        Fitness = menos o RMSE médio das folds internas. Cromossomo vazio
        recebe -inf. Devolve o melhor cromossomo da execução (o `@solution`
        do GA; em empate, o primeiro).
        """
        ri, ro = _r()
        products = [
            _CrossProducts.of(X_tr=X[tr], y_tr=y[tr], X_va=X[va], y_va=y[va])
            for tr, va in inner_folds
        ]
        n_evaluations = [0]

        @ri.rternalize
        def fitness(bits):
            columns = np.flatnonzero(np.asarray(bits) > 0.5)
            if len(columns) == 0:
                return -np.inf
            n_evaluations[0] += 1
            return -float(
                np.mean([kernel_pls_rmse(P, columns, n_components) for P in products])
            )

        pop_size, max_iter = config
        # Substitui o gabin_Population do GA (cada bit com chance 0,5). Roda
        # depois do set.seed que o próprio ga() faz com `seed`.
        population = ro.r(
            f"function(object) matrix(as.integer(runif(object@popSize * object@nBits)"
            f" < {self._initial_density!r}), nrow = object@popSize)"
        )
        ga = ro.r("GA::ga")(
            "binary",
            fitness=fitness,
            nBits=X.shape[1],
            population=population,
            popSize=pop_size,
            maxiter=max_iter,
            monitor=False,
            seed=seed,
        )
        solution = np.asarray(ro.r("function(g) g@solution")(ga))
        # Cada avaliação ajusta um PLS por fold interna.
        budget.increment(n_evaluations[0] * len(inner_folds))
        return {int(j) for j in np.flatnonzero(solution[0] > 0.5)}

    def _fold_selections(self, X_train, y_train, cv_folds, n_components, config, seeds, budget):
        selections = []
        for index, (fold_train, _fold_val) in enumerate(cv_folds):
            selections.append(
                self._run_ga(
                    X_train[fold_train],
                    y_train[fold_train],
                    _inner_folds(cv_folds, index),
                    n_components,
                    config,
                    seeds[index],
                    budget,
                )
            )
        return selections

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedGAPLSArm:
        n_components = self._ga_ncomp(X_train, y_train, cv_folds, budget)
        # Uma semente do R por execução do GA: uma por fold e a do ajuste
        # final, tiradas de `seed_algo` (ADR 008). As mesmas para todos os
        # candidatos, para a comparação entre eles não depender da sorte.
        seeds = [int(s) for s in rng_algo.integers(1, 2**31 - 1, size=len(cv_folds) + 1)]

        if self._fixed_config is not None:
            config = tuple(self._fixed_config)
            rmse_cv = float("nan")
            selections = self._fold_selections(
                X_train, y_train, cv_folds, n_components, config, seeds, budget
            )
        else:
            config, rmse_cv, selections = self._search(
                X_train, y_train, cv_folds, n_components, seeds, budget
            )

        final_bands = self._run_ga(
            X_train, y_train, cv_folds, n_components, config, seeds[-1], budget
        )
        model, columns, refit_ncomp = _fit_pls(X_train, y_train, final_bands, n_components)
        budget.increment()

        return _FittedGAPLSArm(
            _model=model,
            _columns=columns,
            _hyperparams={
                "pop_size": config[0],
                "max_iter": config[1],
                "ga_ncomp": n_components,
                "n_components": refit_ncomp,
                "n_bands": len(columns),
            },
            _rmse_cv=rmse_cv,
            _cv_selections=selections,
        )

    def _search(self, X_train, y_train, cv_folds, n_components, seeds, budget):
        """Escolhe (população, gerações) pela regra de um erro-padrão. Entre
        os candidatos dentro do limite, fica o de MENOS bandas em média nos
        folds: o mesmo critério de parcimônia do VIP (ADR 014, ADR 015)."""
        mean_rmse = np.empty(len(self._candidates))
        se_rmse = np.empty(len(self._candidates))
        mean_bands = np.empty(len(self._candidates))
        per_candidate = []

        for i, config in enumerate(self._candidates):
            selections = self._fold_selections(
                X_train, y_train, cv_folds, n_components, config, seeds, budget
            )
            fold_rmses = []
            for (fold_train, fold_val), bands in zip(cv_folds, selections):
                model, columns, _ = _fit_pls(
                    X_train[fold_train], y_train[fold_train], bands, n_components
                )
                budget.increment()
                y_hat = np.asarray(model.predict(X_train[fold_val][:, columns])).ravel()
                fold_rmses.append(float(np.sqrt(np.mean((y_train[fold_val] - y_hat) ** 2))))
            fold_rmses = np.asarray(fold_rmses)
            mean_rmse[i] = fold_rmses.mean()
            se_rmse[i] = (
                fold_rmses.std(ddof=1) / np.sqrt(len(fold_rmses)) if len(fold_rmses) > 1 else 0.0
            )
            mean_bands[i] = np.mean([len(s) for s in selections])
            per_candidate.append(selections)

        i_chosen = _fewest_bands_within_one_se(mean_rmse, se_rmse, mean_bands)
        return tuple(self._candidates[i_chosen]), float(mean_rmse[i_chosen]), per_candidate[i_chosen]


def _fewest_bands_within_one_se(mean_rmse, se_rmse, mean_bands) -> int:
    """Entre os candidatos com RMSE médio dentro de um erro-padrão do
    mínimo, o de menos bandas em média; em empate, o primeiro."""
    i_min = int(np.argmin(mean_rmse))
    within = np.flatnonzero(mean_rmse <= mean_rmse[i_min] + se_rmse[i_min])
    return int(within[np.argmin(mean_bands[within])])
