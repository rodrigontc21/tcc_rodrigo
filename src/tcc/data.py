from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

Unit = Literal["nm", "cm-1"]


@dataclass(frozen=True, eq=False)
class Dataset:
    """Um conjunto espectral no formato comum a todos os braços.

    `eq=False`: a comparação elemento-a-elemento de arrays numpy quebraria o
    `__eq__` gerado por padrão pelo dataclass (ambiguidade de verdade em
    array). Ninguém precisa comparar dois Dataset por igualdade; identidade
    de objeto é suficiente.
    """

    X: np.ndarray
    y: np.ndarray
    axis: np.ndarray
    unit: Unit
    name: str


def load(name: str) -> Dataset:
    if name == "tecator":
        return _load_tecator()
    raise ValueError(f"dataset desconhecido: {name!r}. Disponível: 'tecator'.")


def _load_tecator() -> Dataset:
    import skfda.datasets

    curves, targets = skfda.datasets.fetch_tecator(return_X_y=True)

    # targets tem 3 colunas (fat, water, protein) nessa ordem fixa da API do
    # skfda; o alvo do protocolo é teor de gordura, coluna 0.
    X = np.asarray(curves.data_matrix[..., 0], dtype=float)
    axis = np.asarray(curves.grid_points[0], dtype=float)
    y = np.asarray(targets[:, 0], dtype=float)

    return Dataset(X=X, y=y, axis=axis, unit="nm", name="tecator")
