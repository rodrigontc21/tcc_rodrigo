from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

# Índices (relativos a X_train/y_train) de cada fold da CV interna. Gerados
# por evaluate() a partir de seed_split e injetados em fit() — o braço nunca
# constrói suas próprias folds, senão dois braços poderiam ver partições de
# CV diferentes sob a mesma seed_split.
CVFolds = list[tuple[np.ndarray, np.ndarray]]


@dataclass
class Budget:
    """Contador de ajustes de modelo, incrementado pelo próprio braço.

    Existe para que "orçamento equivalente de ajuste" entre braços seja
    verificável (ver PROTOCOLO.md) e não uma alegação. Cada chamada a
    `.increment()` corresponde a um ajuste de modelo consumido (uma
    combinação de hiperparâmetros testada na CV interna, por exemplo).
    """

    n_fits: int = field(default=0)

    def increment(self, k: int = 1) -> None:
        self.n_fits += k


@runtime_checkable
class FittedArm(Protocol):
    """O que sai de `Arm.fit`. Carrega tudo que `evaluate` precisa para
    montar um `Result` sem ter que conhecer detalhes internos do braço."""

    def predict(self, X: np.ndarray) -> np.ndarray: ...

    @property
    def band_scores(self) -> np.ndarray | None:
        """Escore por banda (para seleção, Estágio 4). `None` se o braço não
        produz um ranking de bandas (ex.: PLS completo, MLP completo)."""
        ...

    @property
    def hyperparams(self) -> dict:
        """Hiperparâmetros efetivamente escolhidos na CV interna."""
        ...

    @property
    def rmse_cv(self) -> float:
        """Erro da CV interna para os hiperparâmetros escolhidos. `nan` para
        braços sem busca de hiperparâmetro (nada foi validado internamente)."""
        ...


@runtime_checkable
class Arm(Protocol):
    """Contrato único que todo braço experimental implementa.

    `fit` nunca recebe X_test/y_test — estruturalmente, um braço não tem
    como enxergar o teste externo. `fit` também nunca recebe seed_split:
    só `evaluate` sabe dessa semente, e é ela quem gera `cv_folds` a partir
    dela e os injeta aqui. O braço recebe apenas `rng_algo`, derivado de
    seed_algo, para sua própria aleatoriedade interna (inicialização,
    subamostragem, etc.). Essa separação é o que torna os dois eixos de
    semente (partição vs. instabilidade algorítmica) não confundíveis.
    """

    name: str

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> FittedArm: ...
