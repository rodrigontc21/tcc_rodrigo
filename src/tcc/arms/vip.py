"""Braço `vip_threshold`: PLS sobre as bandas com VIP acima de um limiar
(ADR 014).

O VIP é fórmula fechada sobre pesos, escores e loadings de y do PLS (ADR
008), então fica em Python, sem atravessar a ponte para o R. A fórmula foi
conferida contra o `plsVarSel::VIP` e o `mdatools::vipscores` em
`scripts/verificar_vip.py`.

Como no iPLS, a regressão é o mesmo `PLSRegression` do `PLSArm`: o braço
difere do A1 só pelo subconjunto de bandas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds
from tcc.arms.ipls import _fit_pls
from tcc.arms.pls import PLSArm

# Faixa declarada a priori no ADR 014, igual nos quatro conjuntos. O 1,0 é
# a convenção da literatura (a média dos VIP² é 1); 0,8 e os valores acima
# de 1 cobrem os dois lados dela.
DEFAULT_THRESHOLD_CANDIDATES = (0.8, 1.0, 1.2, 1.5)


def vip_scores(model: PLSRegression) -> np.ndarray:
    """VIP de Wold para resposta única, sobre um `PLSRegression` ajustado.

    VIP_j = sqrt(p * sum_a SS_a (w_ja / ||w_a||)^2 / sum_a SS_a),
    com SS_a = q_a^2 * t_a't_a, a variância de y explicada pelo componente a.

    Por construção, a média dos VIP² é 1, e daí vem a convenção do limiar 1.
    """
    W = model.x_weights_
    T = model.x_scores_
    q = np.asarray(model.y_loadings_).ravel()
    ss = q**2 * np.sum(T**2, axis=0)
    w2 = (W / np.linalg.norm(W, axis=0)) ** 2
    return np.sqrt(W.shape[0] * (w2 @ ss) / ss.sum())


def _select(vip: np.ndarray, threshold: float) -> set[int]:
    return {int(j) for j in np.flatnonzero(vip >= threshold)}


@dataclass(frozen=True)
class _FittedVIPArm:
    _model: PLSRegression
    _columns: np.ndarray
    _vip: np.ndarray
    _hyperparams: dict
    _rmse_cv: float
    _cv_selections: list[set[int]]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X[:, self._columns])).ravel()

    @property
    def band_scores(self) -> np.ndarray | None:
        # O VIP do modelo ajustado no treino inteiro: ao contrário do iPLS,
        # este braço tem um escore contínuo por banda.
        return self._vip

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


class VIPArm:
    """Braço `vip_threshold`.

    `threshold=None` (padrão) escolhe o limiar por validação cruzada nas
    folds injetadas. `n_components=None` busca o número de componentes do
    modelo que calcula o VIP pela regra de um erro-padrão do `PLSArm`.

    Os dois têm que ir fixos no verificador anti-vazamento (ADR 011): o
    número de componentes buscado agrega todas as folds e entra no VIP de
    cada uma, como o `glob_ncomp` do iPLS.
    """

    def __init__(
        self,
        threshold: float | None = None,
        n_components: int | None = None,
        candidates: tuple[float, ...] = DEFAULT_THRESHOLD_CANDIDATES,
    ):
        self._fixed_threshold = threshold
        self._fixed_n_components = n_components
        self._candidates = tuple(sorted(candidates))
        parts = []
        if threshold is not None:
            parts.append(f"threshold={threshold}")
        if n_components is not None:
            parts.append(f"n_components={n_components}")
        self.name = "vip_threshold" if not parts else f"vip_threshold({', '.join(parts)})"

    def _vip_ncomp(self, X_train, y_train, cv_folds, budget) -> int:
        if self._fixed_n_components is not None:
            return self._fixed_n_components
        n_components, _ = PLSArm()._search(X_train, y_train, cv_folds, budget)
        return n_components

    def _fold_vips(self, X_train, y_train, cv_folds, n_components, budget):
        """Seleção aninhada: o VIP de cada fold vem de um PLS ajustado só
        em `fold_train`. Um ajuste por fold serve a todos os limiares."""
        vips = []
        for fold_train, _fold_val in cv_folds:
            model = PLSRegression(n_components=n_components).fit(
                X_train[fold_train], y_train[fold_train]
            )
            budget.increment()
            vips.append(vip_scores(model))
        return vips

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedVIPArm:
        n_components = self._vip_ncomp(X_train, y_train, cv_folds, budget)
        vips = self._fold_vips(X_train, y_train, cv_folds, n_components, budget)

        if self._fixed_threshold is not None:
            threshold = self._fixed_threshold
            rmse_cv = float("nan")
        else:
            threshold, rmse_cv = self._search(
                X_train, y_train, cv_folds, vips, n_components, budget
            )
        selections = [_select(vip, threshold) for vip in vips]

        full = PLSRegression(n_components=n_components).fit(X_train, y_train)
        budget.increment()
        vip = vip_scores(full)
        final_bands = _select(vip, threshold)
        if not final_bands:
            raise ValueError(
                f"nenhuma banda com VIP >= {threshold} no treino inteiro "
                f"(maior VIP {vip.max():.3f})"
            )
        model, columns, refit_ncomp = _fit_pls(
            X_train, y_train, final_bands, n_components
        )
        budget.increment()

        return _FittedVIPArm(
            _model=model,
            _columns=columns,
            _vip=vip,
            _hyperparams={
                "threshold": threshold,
                "vip_ncomp": n_components,
                "n_components": refit_ncomp,
                "n_bands": len(columns),
            },
            _rmse_cv=rmse_cv,
            _cv_selections=selections,
        )

    def _search(self, X_train, y_train, cv_folds, vips, n_components, budget):
        """Escolhe o limiar pela regra de um erro-padrão, com o desempate
        para o MAIOR limiar dentro do limite: menos bandas, o modelo mais
        parcimonioso em variáveis (ADR 014). É o sentido oposto ao do
        `int_num` do iPLS, cujo sinal invertido é a pergunta 12.

        Um limiar que deixe algum fold sem banda nenhuma fica de fora. Isso
        só pode acontecer acima de 1: como a média dos VIP² é 1, o maior VIP
        é sempre >= 1, e 0,8 e 1,0 nunca esvaziam.
        """
        mean_rmse = np.full(len(self._candidates), np.inf)
        se_rmse = np.zeros(len(self._candidates))

        for i, threshold in enumerate(self._candidates):
            selections = [_select(vip, threshold) for vip in vips]
            if not all(selections):
                continue
            fold_rmses = []
            for (fold_train, fold_val), bands in zip(cv_folds, selections):
                model, columns, _ = _fit_pls(
                    X_train[fold_train], y_train[fold_train], bands, n_components
                )
                budget.increment()
                y_hat = np.asarray(model.predict(X_train[fold_val][:, columns])).ravel()
                fold_rmses.append(
                    float(np.sqrt(np.mean((y_train[fold_val] - y_hat) ** 2)))
                )
            fold_rmses = np.asarray(fold_rmses)
            mean_rmse[i] = fold_rmses.mean()
            se_rmse[i] = (
                fold_rmses.std(ddof=1) / np.sqrt(len(fold_rmses))
                if len(fold_rmses) > 1
                else 0.0
            )

        i_chosen = _largest_within_one_se(mean_rmse, se_rmse)
        return self._candidates[i_chosen], float(mean_rmse[i_chosen])


def _largest_within_one_se(mean_rmse: np.ndarray, se_rmse: np.ndarray) -> int:
    """Índice do último candidato (candidatos em ordem crescente) com RMSE
    médio dentro de um erro-padrão do mínimo: o maior limiar, o que fica
    com menos bandas."""
    i_min = int(np.argmin(mean_rmse))
    limit = mean_rmse[i_min] + se_rmse[i_min]
    return int(np.flatnonzero(mean_rmse <= limit)[-1])
