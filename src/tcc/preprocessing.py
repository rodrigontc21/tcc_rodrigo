from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter


class SNVPreprocessor:
    """Standard Normal Variate: centra e escala cada espectro (linha).

    Transformação por amostra — cada linha usa só a própria média e o
    próprio desvio, então não há estatística de treino a reter e o
    transform do teste é estruturalmente incapaz de vazar. O par
    fit/transform existe mesmo assim, para o contrato ser o mesmo de
    qualquer pré-processador que evaluate() receba.
    """

    def fit(self, X_train: np.ndarray) -> "SNVPreprocessor":
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        mean = X.mean(axis=1, keepdims=True)
        std = X.std(axis=1, keepdims=True)
        return (X - mean) / std


class DerivativePreprocessor:
    """Primeira derivada de Savitzky-Golay, por espectro.

    janela=11 e polyorder=2 são o padrão mais comum na literatura de NIR
    (ver Rinnan et al. 2009, revisão de pré-processamento) — registrados
    como hiperparâmetros escolhidos, não como achismo. Também é
    transformação por amostra: nada do treino é retido.
    """

    def __init__(self, window_length: int = 11, polyorder: int = 2):
        self.window_length = window_length
        self.polyorder = polyorder

    def fit(self, X_train: np.ndarray) -> "DerivativePreprocessor":
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return savgol_filter(
            X, self.window_length, self.polyorder, deriv=1, axis=1
        )


class ChainPreprocessor:
    """Composição sequencial de pré-processadores, na ordem dada.

    fit ajusta cada etapa sobre a saída da anterior (sempre só com dados
    de treino); transform aplica a cadeia na mesma ordem.
    """

    def __init__(self, steps: list):
        self.steps = steps

    def fit(self, X_train: np.ndarray) -> "ChainPreprocessor":
        current = X_train
        for step in self.steps:
            step.fit(current)
            current = step.transform(current)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        current = X
        for step in self.steps:
            current = step.transform(current)
        return current


def snv_derivative() -> ChainPreprocessor:
    """SNV seguido de primeira derivada — a combinação citada na reunião
    de 01/09 como candidata a vencer as duas isoladas."""
    return ChainPreprocessor([SNVPreprocessor(), DerivativePreprocessor()])
