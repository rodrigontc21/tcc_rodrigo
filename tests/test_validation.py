from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from tcc.arms.base import Budget, CVFolds
from tcc.arms.pls import PLSArm
from tcc.data import Dataset, load
from tcc.protocol import Result
from tcc.validation import LiteratureResult, evaluate_against_literature


@dataclass(frozen=True)
class _FittedSpy:
    @staticmethod
    def predict(X: np.ndarray) -> np.ndarray:
        return np.zeros(X.shape[0])

    @property
    def band_scores(self) -> np.ndarray | None:
        return None

    @property
    def hyperparams(self) -> dict:
        return {}

    @property
    def rmse_cv(self) -> float:
        return float("nan")


class SpyArm:
    """Captura o que o portão de validação entrega ao braço."""

    name = "spy"

    def __init__(self):
        self.received_X = None
        self.received_y = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedSpy:
        self.received_X = X_train
        self.received_y = y_train
        budget.increment()
        return _FittedSpy()


@pytest.fixture(scope="module")
def tecator():
    return load("tecator")


def test_partition_is_fixed_and_deterministic(tecator):
    # A divisão da literatura não depende de semente nenhuma: duas
    # chamadas entregam ao braço exatamente os mesmos dados, com os 172
    # primeiros espectros no treino (divisão padrão do Tecator).
    spy1, spy2 = SpyArm(), SpyArm()
    evaluate_against_literature(spy1, tecator)
    evaluate_against_literature(spy2, tecator)

    assert spy1.received_X.shape == (172, tecator.X.shape[1])
    np.testing.assert_array_equal(spy1.received_X, spy2.received_X)
    np.testing.assert_array_equal(spy1.received_y, spy2.received_y)


def test_return_type_is_structurally_distinct_from_result(tecator):
    # A proteção prometida pelo ADR 005: o tipo de retorno não é Result
    # nem carrega os campos de semente — um LiteratureResult não encaixa
    # na grade nem na decomposição, por construção.
    r = evaluate_against_literature(SpyArm(), tecator)

    assert isinstance(r, LiteratureResult)
    assert not isinstance(r, Result)
    assert not hasattr(r, "seed_split")
    assert not hasattr(r, "seed_algo")


def test_rejects_datasets_without_defined_literature_split(tecator):
    other = Dataset(
        X=tecator.X, y=tecator.y, axis=tecator.axis, unit="nm",
        name="outro", sha256=tecator.sha256,
    )
    with pytest.raises(ValueError, match="literatura"):
        evaluate_against_literature(SpyArm(), other)


def test_reproduces_paper_validation_numbers(tecator):
    # Regressão do portão: PLS H=10 sob o protocolo do paper tem que
    # reproduzir os números obtidos em 03/09 (script autocontido da
    # época) — é a evidência de que a migração para validation.py não
    # mudou a matemática.
    r = evaluate_against_literature(PLSArm(n_components=10), tecator)

    assert r.arm_name == "pls_full(h=10)"
    assert r.r2 == pytest.approx(0.9604, abs=1e-3)
    assert r.rmsep == pytest.approx(0.2041, abs=1e-3)
