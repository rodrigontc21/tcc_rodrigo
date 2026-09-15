from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds

# Teto da busca por número de componentes latentes. O limite real é o
# posto do bloco de treino, então a grade efetiva é recortada em fit().
MAX_COMPONENTS = 20


@dataclass(frozen=True)
class _FittedPLSArm:
    _model: PLSRegression
    _hyperparams: dict
    _rmse_cv: float

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X)).ravel()

    @property
    def band_scores(self) -> np.ndarray | None:
        # Estágio 4 decide como converter coeficientes/VIP em escore por
        # banda; até lá o PLS completo não entra nas métricas de seleção.
        return None

    @property
    def hyperparams(self) -> dict:
        return self._hyperparams

    @property
    def rmse_cv(self) -> float:
        return self._rmse_cv


class PLSArm:
    """Braço A1: PLS sobre o espectro completo.

    `n_components=None` (padrão) escolhe o número de componentes latentes
    por validação cruzada nas `cv_folds` injetadas por `evaluate` — o
    braço nunca constrói as próprias folds. Um valor fixo pula a busca,
    para reproduzir protocolos externos que já declaram H.
    """

    def __init__(self, n_components: int | None = None):
        self._fixed_n_components = n_components
        self.name = "pls_full" if n_components is None else f"pls_full(h={n_components})"

    def _candidates(self, X_train: np.ndarray, cv_folds: CVFolds) -> list[int]:
        # Nenhum fold pode pedir mais componentes do que suas próprias
        # linhas/colunas suportam, senão o PLS degenera no menor fold.
        min_fold_train = min(len(fold_train) for fold_train, _ in cv_folds)
        upper = min(MAX_COMPONENTS, X_train.shape[1], min_fold_train - 1)
        return list(range(1, max(upper, 1) + 1))

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedPLSArm:
        if self._fixed_n_components is not None:
            n_components = self._fixed_n_components
            # Sem busca interna, não há erro de CV a reportar.
            rmse_cv = float("nan")
            budget.increment()
        else:
            n_components, rmse_cv = self._search(X_train, y_train, cv_folds, budget)
            budget.increment()

        model = PLSRegression(n_components=n_components).fit(X_train, y_train)
        return _FittedPLSArm(
            _model=model,
            _hyperparams={"n_components": n_components},
            _rmse_cv=rmse_cv,
        )

    def _search(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        budget: Budget,
    ) -> tuple[int, float]:
        """Escolhe o número de componentes pela REGRA DE UM ERRO-PADRÃO.

        Convenção de Hastie, Tibshirani & Friedman, "The Elements of
        Statistical Learning" (2ª ed., §7.10) — a mesma família de
        convenção do `selectNcomp(method="onesigma")` do pacote R `pls`,
        usada no artigo de referência. Em vez do argmin puro:

        1. RMSE por fold (não agregado), para ter variabilidade entre
           folds e poder estimar o erro-padrão;
        2. por candidato: média dos RMSEs por fold e erro-padrão
           (desvio-padrão amostral ÷ raiz do nº de folds);
        3. n_min = candidato de menor RMSE médio;
        4. limiar = RMSE médio de n_min + erro-padrão de n_min;
        5. escolhido = MENOR candidato com RMSE médio ≤ limiar.

        Ou seja: o modelo mais simples ainda estatisticamente
        indistinguível do melhor. A curva de erro do PLS é plana perto do
        mínimo, então o argmin puro persegue ruído — era a causa da
        instabilidade de 6 a 10 componentes entre `seed_split`.
        """
        candidates = self._candidates(X_train, cv_folds)
        mean_rmse = np.empty(len(candidates))
        se_rmse = np.empty(len(candidates))

        for i, n_components in enumerate(candidates):
            fold_rmses = []
            for fold_train, fold_val in cv_folds:
                model = PLSRegression(n_components=n_components).fit(
                    X_train[fold_train], y_train[fold_train]
                )
                budget.increment()
                y_hat = np.asarray(model.predict(X_train[fold_val])).ravel()
                fold_rmses.append(
                    float(np.sqrt(np.mean((y_train[fold_val] - y_hat) ** 2)))
                )

            fold_rmses = np.asarray(fold_rmses)
            mean_rmse[i] = fold_rmses.mean()
            # Com um único fold não há dispersão a estimar; o erro-padrão
            # zero degenera a regra em argmin puro, que é o comportamento
            # correto nesse caso limite.
            se_rmse[i] = (
                fold_rmses.std(ddof=1) / np.sqrt(len(fold_rmses))
                if len(fold_rmses) > 1
                else 0.0
            )

        i_min = int(np.argmin(mean_rmse))
        threshold = mean_rmse[i_min] + se_rmse[i_min]
        # argmax no vetor booleano devolve o PRIMEIRO True: como
        # `candidates` é crescente, esse é o menor n dentro do limiar
        # (n_min sempre satisfaz, então a busca nunca fica vazia).
        i_chosen = int(np.argmax(mean_rmse <= threshold))

        # rmse_cv passa a ser a média dos RMSEs por fold do candidato
        # escolhido — coerente com a estatística que decidiu a escolha.
        # Difere marginalmente do RMSE agregado de antes (a média de
        # raízes não é a raiz da média).
        return candidates[i_chosen], float(mean_rmse[i_chosen])
