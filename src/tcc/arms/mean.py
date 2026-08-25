from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tcc.arms.base import Budget, CVFolds


@dataclass(frozen=True)
class _FittedMeanArm:
    _mean: float

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(X.shape[0], self._mean)

    @property
    def band_scores(self) -> np.ndarray | None:
        return None

    @property
    def hyperparams(self) -> dict:
        return {}

    @property
    def rmse_cv(self) -> float:
        # Não há hiperparâmetro para validar, então não há CV interna.
        return float("nan")


class MeanArm:
    """Braço trivial: prediz a média de y_train, ignora X inteiramente.

    Existe só para provar que o encanamento do Estágio 0 (evaluate, Result,
    os dois eixos de semente) funciona de ponta a ponta antes de qualquer
    modelo de verdade entrar em cena.
    """

    name = "mean"

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedMeanArm:
        budget.increment()
        return _FittedMeanArm(_mean=float(np.mean(y_train)))
