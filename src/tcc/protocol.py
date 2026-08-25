from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import r2_score

from tcc.arms.base import Arm, Budget, CVFolds
from tcc.data import Dataset

# Provisório: o protocolo congela na semana 11 (ver PROTOCOLO.md). Até lá,
# test_size e n_splits ficam como parâmetros de evaluate() com um default
# razoável, não como constante gravada em pedra.
DEFAULT_TEST_SIZE = 0.25
DEFAULT_N_SPLITS = 5


@dataclass(frozen=True, eq=False)
class Result:
    """Saída única de `evaluate`, igual para qualquer braço.

    `eq=False` pelo mesmo motivo de `Dataset`: há campos array (`y_pred`,
    `test_idx`, `band_scores`) cuja comparação por `==` seria ambígua no
    `__eq__` gerado por padrão.
    """

    r2: float
    rmsep: float
    rmse_cv: float
    y_pred: np.ndarray
    test_idx: np.ndarray
    selection: set[int] | None
    band_scores: np.ndarray | None
    n_fits: int
    wall_time: float
    hyperparams: dict
    arm_name: str
    dataset_name: str
    seed_split: int
    seed_algo: int


class IdentityPreprocessor:
    """Placeholder de pré-processamento espectral.

    O Estágio 1 do pipeline decide o método real (SNV, derivada, ...) e ele
    será único para todos os braços — comparar braços sob pré-processamentos
    diferentes invalidaria o benchmark (ver PROTOCOLO.md). Por ora, a
    identidade mantém o ponto de encaixe "ajustado só no treino" já no
    lugar certo, para que trocar por SNV/derivada depois não exija mexer em
    `evaluate`.
    """

    def fit(self, X_train: np.ndarray) -> "IdentityPreprocessor":
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return X


def _split_train_test(
    n: int, test_size: float, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    permutation = rng.permutation(n)
    n_test = int(round(n * test_size))
    test_idx = np.sort(permutation[:n_test])
    train_idx = np.sort(permutation[n_test:])
    return train_idx, test_idx


def _make_cv_folds(
    n_train: int, n_splits: int, rng: np.random.Generator
) -> CVFolds:
    permutation = rng.permutation(n_train)
    fold_sizes = np.full(n_splits, n_train // n_splits, dtype=int)
    fold_sizes[: n_train % n_splits] += 1

    folds: CVFolds = []
    start = 0
    for size in fold_sizes:
        val_idx = permutation[start : start + size]
        train_idx = np.concatenate([permutation[:start], permutation[start + size :]])
        folds.append((np.sort(train_idx), np.sort(val_idx)))
        start += size
    return folds


def evaluate(
    arm: Arm,
    dataset: Dataset,
    seed_split: int,
    seed_algo: int,
    test_size: float = DEFAULT_TEST_SIZE,
    n_splits: int = DEFAULT_N_SPLITS,
) -> Result:
    """Avalia um braço num conjunto de dados sob a mesma prova para todos.

    Os dois eixos de semente são gerados a partir de `SeedSequence`s
    independentes: um para a partição treino/teste + folds da CV interna
    (deriva só de `seed_split`), outro para a aleatoriedade interna do
    braço (`seed_algo`). O braço nunca recebe `seed_split` nem vê o teste
    externo — só `X_train`/`y_train` e as folds já prontas.
    """
    seed_sequence = np.random.SeedSequence(seed_split)
    split_seed, cv_seed = seed_sequence.spawn(2)
    split_rng = np.random.default_rng(split_seed)
    cv_rng = np.random.default_rng(cv_seed)
    algo_rng = np.random.default_rng(seed_algo)

    train_idx, test_idx = _split_train_test(dataset.X.shape[0], test_size, split_rng)
    X_train, y_train = dataset.X[train_idx], dataset.y[train_idx]
    X_test, y_test = dataset.X[test_idx], dataset.y[test_idx]

    preprocessor = IdentityPreprocessor().fit(X_train)
    X_train = preprocessor.transform(X_train)
    X_test = preprocessor.transform(X_test)

    cv_folds = _make_cv_folds(len(train_idx), n_splits, cv_rng)

    budget = Budget()
    start_time = time.perf_counter()
    fitted = arm.fit(X_train, y_train, cv_folds, algo_rng, budget)
    y_pred = fitted.predict(X_test)
    wall_time = time.perf_counter() - start_time

    r2 = float(r2_score(y_test, y_pred))
    rmsep = float(np.sqrt(np.mean((y_test - y_pred) ** 2)))

    return Result(
        r2=r2,
        rmsep=rmsep,
        rmse_cv=fitted.rmse_cv,
        y_pred=y_pred,
        test_idx=test_idx,
        # Conversão de saída bruta em conjunto de bandas é o Estágio 4;
        # ainda não existe, então fica None até lá.
        selection=None,
        band_scores=fitted.band_scores,
        n_fits=budget.n_fits,
        wall_time=wall_time,
        hyperparams=fitted.hyperparams,
        arm_name=arm.name,
        dataset_name=dataset.name,
        seed_split=seed_split,
        seed_algo=seed_algo,
    )
