from __future__ import annotations

import numpy as np

from tcc.arms.base import Arm, Budget, CVFolds, FittedArm


class PermutedYArm:
    """Decorador de sonda de vazamento: embaralha y_train antes do fit.

    Com o alvo permutado, não existe relação real entre X e y — qualquer
    R² apreciavelmente acima de zero no teste externo só pode vir de
    vazamento em algum ponto do caminho de X (pré-processamento ajustado
    com dados de teste, seleção de variáveis vendo a validação, etc.).
    Complementa o MeanArm, que valida o lado do y mas nunca toca em X.

    A permutação usa `rng_algo`: reprodutível por seed_algo, sem acesso a
    seed_split, e nunca uma fonte global. X_train fica intacto — é
    justamente por ele que o vazamento apareceria.
    """

    def __init__(self, inner: Arm):
        self._inner = inner
        self.name = f"permuted_y({inner.name})"

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> FittedArm:
        y_permuted = y_train[rng_algo.permutation(len(y_train))]
        # O FittedArm do braço interno é devolvido como está: predict,
        # band_scores, hyperparams e rmse_cv já são os dele.
        return self._inner.fit(X_train, y_permuted, cv_folds, rng_algo, budget)
