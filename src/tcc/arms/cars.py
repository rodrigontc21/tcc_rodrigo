"""Braço `cars`: PLS sobre as bandas escolhidas pelo CARS (ADR 016).

CARS, de Li, Liang, Xu e Cao (2009), *Anal. Chim. Acta* 648(1):77–84,
implementado aqui a partir do artigo e conferido linha a linha contra o
`carspls.m` dos autores (versão 1.50 e libPLS 1.95 com `originalVersion =
1`). Nenhum código deles é executado (adendo de 05/11/2026 do ADR 008).

Em cada uma das N execuções (Seções 2.2 a 2.6 do artigo):

1. Monte Carlo: um PLS só centrado com uma fração das amostras, sorteadas;
2. peso de cada banda = |coeficiente| desse PLS;
3. EDF: mantém as K bandas de maior peso, com K tirado da curva
   exponencial que vai de todas as bandas a 2;
4. ARS: p sorteios com reposição, com chance proporcional ao peso; seguem
   as bandas sorteadas ao menos uma vez.

No fim, entre os N subconjuntos (as bandas de cada execução), fica o de
menor RMSECV nas folds recebidas. Os dois sorteios saem do gerador
recebido, então a mesma semente dá a mesma seleção.

Dois modos (ADR 016): `protocolo`, que escolhe N, a razão de amostragem e
o fator do teto de componentes na CV interna e entrega o `PLSRegression`
autoescalado dos outros braços; e `fiel`, com essa configuração fixa e o
modelo só centrado, como no `carspls.m`, para medir o efeito das
adaptações e para o portão contra o artigo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds
from tcc.arms.gapls import _fewest_bands_within_one_se
from tcc.arms.ipls import _fit_pls, _inner_folds
from tcc.arms.pls import PLSArm

# (N, razão de amostragem, fator do teto), declarados a priori no ADR 016.
# N = 50 é o padrão dos códigos dos autores, 100 o do artigo (Seção 4.1);
# 0,8 e 0,9 são as pontas do "usually 80–90%" da Seção 2.2. O teto de
# componentes do CARS é o fator vezes o número de componentes do A1: nos
# dados de milho do artigo, com teto 2 o CARS não acha as bandas do artigo
# em nenhuma de 30 repetições, e com 10 acha em todas
# (`scripts/verificar_cars_milho.py`, DIARIO de 05/11).
DEFAULT_CARS_CANDIDATES = tuple(
    (n_runs, ratio, factor)
    for n_runs in (50, 100)
    for ratio in (0.8, 0.9)
    for factor in (1, 2, 3)
)

# Modo `fiel`: N do artigo, a razão dos códigos (`ratio=0.9`) e o maior
# teto da grade, dentro do qual o CARS escolhe pelo menor RMSECV.
FAITHFUL_CONFIG = (100, 0.9, 3)

MODES = ("protocolo", "fiel")


def _matlab_round(x: float) -> int:
    """`round` do MATLAB para x >= 0: metade arredonda para cima. O
    `round` do numpy arredonda metade para o par."""
    return int(np.floor(x + 0.5))


def edf_kept(n_bands: int, n_runs: int, run: int) -> int:
    """Quantas bandas a EDF mantém ao fim da execução `run` (1, ..., N).

    Eqs. 4 a 6 do artigo: r_i = a·exp(-k·i), com a = (p/2)^(1/(N-1)) e
    k = ln(p/2)/(N-1), o que dá r_1 = 1 e r_N = 2/p. Como no `carspls.m`,
    a execução i, que ajusta com as bandas que sobraram da anterior, corta
    para r_(i+1): `ratio = a*exp(-b*(iter+1))`, `K = round(Nx*ratio)`.

    O piso de 1 banda é nosso. Só pesa num caso degenerado (N muito pequeno
    para o p), em que o `carspls.m` pararia com todos os pesos zerados.
    """
    k = np.log(n_bands / 2) / (n_runs - 1)
    a = np.exp(k)
    return max(1, _matlab_round(n_bands * a * np.exp(-k * (run + 1))))


def coef_path(model: PLSRegression) -> np.ndarray:
    """Coeficientes de um PLS de resposta única com 1, ..., h componentes,
    a partir de um ajuste com h (colunas 0, ..., h-1).

    O NIPALS extrai os componentes em sequência, então os a primeiros de um
    ajuste com h são os de um ajuste com a: B_a = W_a (P_a' W_a)^-1 q_a.
    Assim um ajuste dá a curva de RMSECV inteira. Só para `scale=False`:
    com autoescala, os coeficientes ainda teriam de ser reescalados.
    """
    W, P = model.x_weights_, model.x_loadings_
    q = np.asarray(model.y_loadings_).ravel()
    h = W.shape[1]
    path = np.empty((W.shape[0], h))
    for a in range(1, h + 1):
        R = W[:, :a] @ np.linalg.inv(P[:, :a].T @ W[:, :a])
        path[:, a - 1] = R @ q[:a]
    return path


def _centered_pls(X: np.ndarray, y: np.ndarray, n_components: int) -> PLSRegression:
    return PLSRegression(n_components=n_components, scale=False).fit(X, y)


def subset_rmsecv(
    X: np.ndarray,
    y: np.ndarray,
    columns: np.ndarray,
    max_ncomp: int,
    folds: CVFolds,
    budget: Budget,
) -> tuple[float, int]:
    """RMSECV de um subconjunto de bandas e o número de componentes que o
    alcança, entre 1 e o teto. PLS só centrado, como o `plscvfold` do
    `carspls.m`; RMSECV = raiz do PRESS somado nas folds sobre o total de
    linhas de validação.

    Conta um ajuste por componente por fold, como o `PLSArm`, embora um só
    ajuste com h componentes dê a curva inteira.
    """
    press = None
    n_val = 0
    for fold_train, fold_val in folds:
        X_tr, y_tr = X[np.ix_(fold_train, columns)], y[fold_train]
        h = max(1, min(max_ncomp, len(columns), len(fold_train) - 1))
        if press is None:
            press = np.zeros(h)
        h = min(h, len(press))
        model = _centered_pls(X_tr, y_tr, h)
        budget.increment(h)
        B = coef_path(model)[:, :h]
        x_mean, y_mean = X_tr.mean(axis=0), y_tr.mean()
        y_hat = (X[np.ix_(fold_val, columns)] - x_mean) @ B + y_mean
        press = press[:h] + ((y[fold_val][:, None] - y_hat) ** 2).sum(axis=0)
        n_val += len(fold_val)
    rmsecv = np.sqrt(press / n_val)
    best = int(np.argmin(rmsecv))
    return float(rmsecv[best]), best + 1


@dataclass(frozen=True)
class CARSRun:
    """Uma execução completa do CARS."""

    subsets: list[np.ndarray]  # bandas de cada uma das N execuções
    rmsecv: np.ndarray  # RMSECV de cada subconjunto
    n_components: np.ndarray  # componentes que alcançam esse RMSECV
    best: int  # índice do subconjunto escolhido

    @property
    def selection(self) -> set[int]:
        return {int(j) for j in self.subsets[self.best]}


def run_cars(
    X: np.ndarray,
    y: np.ndarray,
    folds: CVFolds,
    n_runs: int,
    ratio: float,
    max_ncomp: int,
    rng: np.random.Generator,
    budget: Budget,
) -> CARSRun:
    """O CARS do artigo sobre (X, y), escolhendo o subconjunto nas `folds`."""
    if n_runs < 2:
        raise ValueError(f"N = {n_runs}: a EDF precisa de pelo menos 2 execuções")
    if not 0 < ratio <= 1:
        raise ValueError(f"razão de amostragem {ratio} fora de (0, 1]")
    n, p = X.shape
    n_sampled = int(np.floor(n * ratio))  # Q = floor(Mx*ratio)
    vsel = np.arange(p)
    subsets = []

    for run in range(1, n_runs + 1):
        # 1. Monte Carlo
        rows = rng.permutation(n)[:n_sampled]
        h = max(1, min(max_ncomp, len(vsel), n_sampled - 1))
        model = _centered_pls(X[np.ix_(rows, vsel)], y[rows], h)
        budget.increment()

        # 2. pesos; as bandas da execução são as de coeficiente não nulo,
        # como `find(W(:,i)~=0)` no `carspls.m`
        w = np.zeros(p)
        w[vsel] = np.abs(np.ravel(model.coef_))
        subsets.append(np.flatnonzero(w))

        # 3. EDF: zera as de menor peso. `sort(-w)` do MATLAB é estável.
        order = np.argsort(-w, kind="stable")
        w[order[edf_kept(p, n_runs, run):]] = 0.0

        # 4. ARS: p sorteios com reposição, `randsample(Nx,Nx,true,w)`
        vsel = np.unique(rng.choice(p, size=p, replace=True, p=w / w.sum()))

    scores = [
        subset_rmsecv(X=X, y=y, columns=s, max_ncomp=max_ncomp, folds=folds, budget=budget)
        for s in subsets
    ]
    rmsecv = np.array([s[0] for s in scores])
    n_components = np.array([s[1] for s in scores])
    # `min` do MATLAB devolve o primeiro em empate, como o argmin
    return CARSRun(
        subsets=subsets, rmsecv=rmsecv, n_components=n_components, best=int(np.argmin(rmsecv))
    )


@dataclass(frozen=True)
class _FittedCARSArm:
    _model: PLSRegression
    _columns: np.ndarray
    _hyperparams: dict
    _rmse_cv: float
    _cv_selections: list[set[int]]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X[:, self._columns])).ravel()

    @property
    def band_scores(self) -> np.ndarray | None:
        # O CARS devolve um conjunto, não um ranking (como o iPLS e o GA).
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


class CARSArm:
    """Braço `cars` (ADR 016).

    `mode="protocolo"` (padrão) escolhe (N, razão, fator do teto) na CV
    interna entre `candidates`, a menos que `cars_config` os fixe, e
    entrega o `PLSRegression` autoescalado do A1. `mode="fiel"` usa
    `FAITHFUL_CONFIG` e entrega o PLS só centrado, como o `carspls.m`. Nos
    dois, o modelo final tem o número de componentes que o CARS escolheu
    para o subconjunto vencedor (o de menor RMSECV, até o teto).

    O teto é o fator vezes o número de componentes do A1, buscado pela
    regra de um erro-padrão do `PLSArm` (ou `n_components`, se fixo), e
    recortado pelo teto da busca do `PLSArm`. Para o verificador
    anti-vazamento (ADR 011), configuração e `n_components` vão fixos.

    A seleção é aninhada: em cada fold externo, o CARS só vê `fold_train`,
    e escolhe o subconjunto nas folds internas (`_inner_folds`), que
    respeitam os grupos do ADR 009.
    """

    def __init__(
        self,
        mode: str = "protocolo",
        cars_config: tuple[int, float, int] | None = None,
        n_components: int | None = None,
        candidates: tuple[tuple[int, float, int], ...] = DEFAULT_CARS_CANDIDATES,
    ):
        if mode not in MODES:
            raise ValueError(f"modo {mode!r}; os modos são {MODES}")
        if mode == "fiel" and cars_config is not None:
            raise ValueError("o modo 'fiel' tem configuração fixa (ADR 016)")
        if cars_config is not None and len(cars_config) != 3:
            raise ValueError("cars_config = (N, razão, fator do teto)")
        self._mode = mode
        self._fixed_config = FAITHFUL_CONFIG if mode == "fiel" else cars_config
        self._fixed_n_components = n_components
        self._candidates = candidates
        base = "cars" if mode == "protocolo" else "cars_fiel"
        parts = []
        if cars_config is not None:
            parts.append(f"cars_config={cars_config}")
        if n_components is not None:
            parts.append(f"n_components={n_components}")
        self.name = base if not parts else f"{base}({', '.join(parts)})"

    def _base_ncomp(self, X_train, y_train, cv_folds, budget) -> int:
        if self._fixed_n_components is not None:
            return self._fixed_n_components
        n_components, _ = PLSArm()._search(X_train, y_train, cv_folds, budget)
        return n_components

    @staticmethod
    def _ceiling(base: int, factor: int, X_train, cv_folds) -> int:
        return max(1, min(factor * base, PLSArm()._candidates(X_train, cv_folds)[-1]))

    def _fold_runs(self, X_train, y_train, cv_folds, base, config, seeds, budget):
        n_runs, ratio, factor = config
        max_ncomp = self._ceiling(base, factor, X_train, cv_folds)
        return [
            run_cars(
                X=X_train[fold_train],
                y=y_train[fold_train],
                folds=_inner_folds(cv_folds, index),
                n_runs=n_runs,
                ratio=ratio,
                max_ncomp=max_ncomp,
                rng=np.random.default_rng(seeds[index]),
                budget=budget,
            )
            for index, (fold_train, _fold_val) in enumerate(cv_folds)
        ]

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedCARSArm:
        base = self._base_ncomp(X_train, y_train, cv_folds, budget)
        # Uma semente por execução do CARS: uma por fold e a do ajuste final,
        # tiradas de `seed_algo`. As mesmas para todos os candidatos, para a
        # comparação entre eles não depender da sorte (como no GA-PLS).
        seeds = rng_algo.integers(0, 2**63 - 1, size=len(cv_folds) + 1)

        if self._fixed_config is not None:
            config = tuple(self._fixed_config)
            rmse_cv = float("nan")
            runs = self._fold_runs(X_train, y_train, cv_folds, base, config, seeds, budget)
        else:
            config, rmse_cv, runs = self._search(X_train, y_train, cv_folds, base, seeds, budget)
        selections = [r.selection for r in runs]
        max_ncomp = self._ceiling(base, config[2], X_train, cv_folds)

        final = run_cars(
            X=X_train,
            y=y_train,
            folds=cv_folds,
            n_runs=config[0],
            ratio=config[1],
            max_ncomp=max_ncomp,
            rng=np.random.default_rng(seeds[-1]),
            budget=budget,
        )
        cars_ncomp = int(final.n_components[final.best])
        if self._mode == "fiel":
            columns = np.sort(final.subsets[final.best])
            refit_ncomp = cars_ncomp
            model = _centered_pls(X_train[:, columns], y_train, refit_ncomp)
        else:
            model, columns, refit_ncomp = _fit_pls(
                X_train, y_train, final.selection, cars_ncomp
            )
        budget.increment()

        return _FittedCARSArm(
            _model=model,
            _columns=columns,
            _hyperparams={
                "mode": self._mode,
                "n_runs": config[0],
                "ratio": config[1],
                "ncomp_factor": config[2],
                "a1_ncomp": base,
                "ncomp_ceiling": max_ncomp,
                "cars_rmsecv": float(final.rmsecv[final.best]),
                "cars_best_run": final.best + 1,
                "cars_best_ncomp": cars_ncomp,
                "n_components": refit_ncomp,
                "n_bands": len(columns),
            },
            _rmse_cv=rmse_cv,
            _cv_selections=selections,
        )

    def _search(self, X_train, y_train, cv_folds, base, seeds, budget):
        """Escolhe (N, razão, fator do teto) pela regra de um erro-padrão;
        entre os candidatos dentro do limite, o de menos bandas em média nos
        folds, o mesmo critério do VIP e do GA-PLS (ADR 016). Cada fold é
        avaliado com o PLS do protocolo e o número de componentes que o
        CARS daquele fold escolheu."""
        mean_rmse = np.empty(len(self._candidates))
        se_rmse = np.empty(len(self._candidates))
        mean_bands = np.empty(len(self._candidates))
        per_candidate = []

        for i, config in enumerate(self._candidates):
            runs = self._fold_runs(X_train, y_train, cv_folds, base, config, seeds, budget)
            fold_rmses = []
            for (fold_train, fold_val), run in zip(cv_folds, runs):
                model, columns, _ = _fit_pls(
                    X_train[fold_train],
                    y_train[fold_train],
                    run.selection,
                    int(run.n_components[run.best]),
                )
                budget.increment()
                y_hat = np.asarray(model.predict(X_train[fold_val][:, columns])).ravel()
                fold_rmses.append(float(np.sqrt(np.mean((y_train[fold_val] - y_hat) ** 2))))
            fold_rmses = np.asarray(fold_rmses)
            mean_rmse[i] = fold_rmses.mean()
            se_rmse[i] = (
                fold_rmses.std(ddof=1) / np.sqrt(len(fold_rmses)) if len(fold_rmses) > 1 else 0.0
            )
            mean_bands[i] = np.mean([len(r.selection) for r in runs])
            per_candidate.append(runs)

        i_chosen = _fewest_bands_within_one_se(mean_rmse, se_rmse, mean_bands)
        return tuple(self._candidates[i_chosen]), float(mean_rmse[i_chosen]), per_candidate[i_chosen]
