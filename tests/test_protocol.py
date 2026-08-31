from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from tcc.arms.base import Budget, CVFolds
from tcc.arms.mean import MeanArm
from tcc.arms.permuted import PermutedYArm
from tcc.data import load
from tcc.protocol import evaluate


@dataclass(frozen=True)
class _FittedZeroArm:
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


class ZeroArm:
    """Segundo braço trivial, só para os testes de encanamento: prediz
    sempre zero, ignorando X e y. Serve para provar que a partição
    treino/teste independe de qual braço a consome."""

    name = "zero"

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedZeroArm:
        budget.increment()
        return _FittedZeroArm()


@dataclass(frozen=True)
class _FittedRandomArm:
    _offset: float

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(X.shape[0], self._offset)

    @property
    def band_scores(self) -> np.ndarray | None:
        return None

    @property
    def hyperparams(self) -> dict:
        return {}

    @property
    def rmse_cv(self) -> float:
        return float("nan")


class RandomArm:
    """Braço-sonda estocástico, só para os testes: prediz um valor tirado
    de `rng_algo`, ignorando X e y. Serve para provar que `rng_algo` deriva
    de seed_algo e de nada mais — um braço determinístico como MeanArm
    passaria pelos testes de invariância mesmo com os eixos de semente
    trocados dentro de evaluate (achado crítico da auditoria de 2026-08-25)."""

    name = "random"

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedRandomArm:
        budget.increment()
        return _FittedRandomArm(_offset=float(rng_algo.normal()))


@pytest.fixture(scope="module")
def tecator():
    return load("tecator")


def test_mean_arm_produces_valid_result(tecator):
    result = evaluate(MeanArm(), tecator, seed_split=0, seed_algo=0)

    assert np.isfinite(result.r2)
    assert abs(result.r2) < 0.2  # média não explica variância -> R² ~ 0
    assert np.isfinite(result.rmsep)
    assert result.y_pred.shape == result.test_idx.shape
    assert result.selection is None
    assert result.band_scores is None
    assert result.n_fits == 1
    assert result.wall_time >= 0
    assert result.hyperparams == {}
    assert result.arm_name == "mean"
    assert result.dataset_name == "tecator"
    assert result.seed_split == 0
    assert result.seed_algo == 0


def test_same_seed_split_gives_identical_partition_across_arms(tecator):
    r_mean = evaluate(MeanArm(), tecator, seed_split=42, seed_algo=1)
    r_zero = evaluate(ZeroArm(), tecator, seed_split=42, seed_algo=2)

    np.testing.assert_array_equal(r_mean.test_idx, r_zero.test_idx)


def test_deterministic_arm_is_invariant_to_seed_algo(tecator):
    r1 = evaluate(MeanArm(), tecator, seed_split=7, seed_algo=1)
    r2 = evaluate(MeanArm(), tecator, seed_split=7, seed_algo=999)

    assert r1.r2 == r2.r2
    assert r1.rmsep == r2.rmsep
    np.testing.assert_array_equal(r1.test_idx, r2.test_idx)
    np.testing.assert_array_equal(r1.y_pred, r2.y_pred)


def test_stochastic_arm_is_reproducible_with_same_seeds(tecator):
    r1 = evaluate(RandomArm(), tecator, seed_split=7, seed_algo=3)
    r2 = evaluate(RandomArm(), tecator, seed_split=7, seed_algo=3)

    np.testing.assert_array_equal(r1.test_idx, r2.test_idx)
    np.testing.assert_array_equal(r1.y_pred, r2.y_pred)
    assert r1.r2 == r2.r2
    assert r1.rmsep == r2.rmsep


def test_seed_algo_varies_predictions_without_touching_partition(tecator):
    # O invariante central dos dois eixos: se evaluate passasse split_rng ou
    # cv_rng (derivados de seed_split) no lugar de algo_rng para arm.fit,
    # y_pred ficaria idêntico entre seed_algo distintos e este teste falharia.
    r1 = evaluate(RandomArm(), tecator, seed_split=7, seed_algo=1)
    r2 = evaluate(RandomArm(), tecator, seed_split=7, seed_algo=999)

    np.testing.assert_array_equal(r1.test_idx, r2.test_idx)
    assert not np.array_equal(r1.y_pred, r2.y_pred)


def test_seed_split_varies_partition_with_fixed_seed_algo(tecator):
    r1 = evaluate(RandomArm(), tecator, seed_split=7, seed_algo=3)
    r2 = evaluate(RandomArm(), tecator, seed_split=8, seed_algo=3)

    assert not np.array_equal(r1.test_idx, r2.test_idx)


class SpyArm:
    """Braço-espião: captura os argumentos que recebeu em fit, para
    inspecionar o que um decorador de fato entrega ao braço interno."""

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
    ) -> _FittedZeroArm:
        self.received_X = X_train
        self.received_y = y_train
        budget.increment()
        return _FittedZeroArm()


@dataclass(frozen=True)
class _FittedFirstYArm:
    _first: float

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(X.shape[0], self._first)

    @property
    def band_scores(self) -> np.ndarray | None:
        return None

    @property
    def hyperparams(self) -> dict:
        return {}

    @property
    def rmse_cv(self) -> float:
        return float("nan")


class FirstYArm:
    """Braço sensível à ordem: prediz y_train[0]. Ao contrário do MeanArm
    (média é invariante a permutação), este muda de saída se y_train for
    embaralhado — sonda direta de que a permutação acontece."""

    name = "first_y"

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedFirstYArm:
        budget.increment()
        return _FittedFirstYArm(_first=float(y_train[0]))


def test_permuted_y_delivers_shuffled_y_with_same_values(tecator):
    spy = SpyArm()
    result = evaluate(PermutedYArm(spy), tecator, seed_split=0, seed_algo=0)

    n_train = len(spy.received_y)
    # train_idx é sorted em evaluate, então o y de treino na ordem
    # original é o y completo sem os índices de teste
    y_original = np.delete(tecator.y, result.test_idx)

    # Mesma multiset de valores (nada perdido nem inventado)...
    np.testing.assert_array_equal(np.sort(spy.received_y), np.sort(y_original))
    # ...mas em ordem diferente: a permutação de fato aconteceu
    assert not np.array_equal(spy.received_y, y_original)
    # X_train fica intacto — é por ele que vazamento apareceria
    assert spy.received_X.shape == (n_train, tecator.X.shape[1])


def test_permuted_y_changes_output_of_order_sensitive_arm(tecator):
    r_plain = evaluate(FirstYArm(), tecator, seed_split=0, seed_algo=0)
    r_wrapped = evaluate(PermutedYArm(FirstYArm()), tecator, seed_split=0, seed_algo=0)

    np.testing.assert_array_equal(r_plain.test_idx, r_wrapped.test_idx)
    assert not np.array_equal(r_plain.y_pred, r_wrapped.y_pred)


def test_permuted_y_wrapping_mean_arm_keeps_r2_near_zero(tecator):
    # Guarda de regressão da sonda de vazamento: com y permutado não há
    # relação X→y a aprender, então R² apreciavelmente acima de zero
    # denunciaria vazamento no caminho de X. Para o MeanArm em particular
    # a permutação preserva a média, logo y_pred é idêntico ao do braço
    # sem decorador — o teste ganha força quando braços que usam X
    # entrarem no lugar do MeanArm.
    r_permuted = evaluate(PermutedYArm(MeanArm()), tecator, seed_split=0, seed_algo=0)
    r_plain = evaluate(MeanArm(), tecator, seed_split=0, seed_algo=0)

    assert r_permuted.arm_name == "permuted_y(mean)"
    assert abs(r_permuted.r2) < 0.2
    np.testing.assert_allclose(r_permuted.y_pred, r_plain.y_pred)
