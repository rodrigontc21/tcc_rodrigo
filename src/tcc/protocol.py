from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import r2_score

from tcc.arms.base import Arm, Budget, CVFolds
from tcc.data import Dataset
from tcc.preprocessing import SNVPreprocessor

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
    """Pré-processamento nulo: devolve o espectro como veio.

    Foi o default de `evaluate` durante os Estágios 0 e 1, enquanto a
    escolha do pré-processamento não estava fechada; desde o início do
    Estágio 2 o default é o `SNVPreprocessor` (ver PROTOCOLO.md,
    "Pré-processamento"). Permanece como o nível "sem pré-processamento"
    de qualquer comparação que precise dele — inclusive para reproduzir
    resultados dos Estágios 0 e 1 — e nunca como escolha de um braço
    isolado: comparar braços sob pré-processamentos diferentes invalida o
    benchmark.
    """

    def fit(self, X_train: np.ndarray) -> "IdentityPreprocessor":
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return X


def _groups_in_permutation_order(
    permutation: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ordem aleatória dos grupos, derivada da permutação das linhas.

    Cada grupo é representado por UMA linha fixa (a primeira dele na ordem
    original), e os grupos são ordenados pela posição desse representante
    na permutação. Assim todo grupo tem a mesma chance de vir cedo,
    qualquer que seja o tamanho. Ordenar pela primeira aparição de qualquer
    membro favoreceria grupos grandes (mais membros, mais chances de
    aparecer cedo) e enviesaria o teste para eles.

    Devolve (ordem dos grupos, grupo de cada linha, tamanho de cada grupo).
    Com grupos unitários, a ordem dos grupos é a própria permutação — é o
    que faz a partição agrupada reproduzir exatamente a não agrupada.
    """
    _, representative, inverse = np.unique(
        groups, return_index=True, return_inverse=True
    )
    inverse = inverse.ravel()
    position = np.empty(len(permutation), dtype=int)
    position[permutation] = np.arange(len(permutation))
    order = np.argsort(position[representative], kind="stable")
    return order, inverse, np.bincount(inverse)


def _split_train_test(
    n: int,
    test_size: float,
    rng: np.random.Generator,
    groups: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Partição treino/teste. Com `groups`, réplicas da mesma amostra física
    caem inteiras de um lado só (ADR 009): o teste recebe grupos inteiros,
    na ordem da permutação, até atingir `test_size` — podendo passar do
    alvo por no máximo o tamanho de um grupo menos um."""
    permutation = rng.permutation(n)
    n_test = int(round(n * test_size))
    if groups is None:
        test_idx = np.sort(permutation[:n_test])
        train_idx = np.sort(permutation[n_test:])
        return train_idx, test_idx

    if n_test == 0:
        return np.arange(n), np.array([], dtype=int)
    order, inverse, sizes = _groups_in_permutation_order(permutation, groups)
    n_test_groups = int(np.searchsorted(np.cumsum(sizes[order]), n_test)) + 1
    in_test = np.isin(inverse, order[:n_test_groups])
    return np.flatnonzero(~in_test), np.flatnonzero(in_test)


def _make_cv_folds(
    n_train: int,
    n_splits: int,
    rng: np.random.Generator,
    groups: np.ndarray | None = None,
) -> CVFolds:
    """Folds da CV interna. Com `groups`, réplicas nunca ficam em folds
    diferentes (ADR 009): cada fold é preenchido com grupos inteiros, na
    ordem da permutação, até atingir seu tamanho-alvo."""
    permutation = rng.permutation(n_train)
    fold_sizes = np.full(n_splits, n_train // n_splits, dtype=int)
    fold_sizes[: n_train % n_splits] += 1

    folds: CVFolds = []
    if groups is None:
        start = 0
        for size in fold_sizes:
            val_idx = permutation[start : start + size]
            train_idx = np.concatenate([permutation[:start], permutation[start + size :]])
            folds.append((np.sort(train_idx), np.sort(val_idx)))
            start += size
        return folds

    order, inverse, sizes = _groups_in_permutation_order(permutation, groups)
    fold_of_group = np.empty(len(order), dtype=int)
    fold, filled = 0, 0
    for group in order:
        fold_of_group[group] = fold
        filled += sizes[group]
        if filled >= fold_sizes[fold] and fold < n_splits - 1:
            fold, filled = fold + 1, 0

    fold_of_row = fold_of_group[inverse]
    for f in range(n_splits):
        val_idx = np.flatnonzero(fold_of_row == f)
        if len(val_idx) == 0:
            raise ValueError(
                f"fold {f} vazio: grupos grandes demais para {n_splits} folds"
            )
        folds.append((np.flatnonzero(fold_of_row != f), val_idx))
    return folds


def _fit_and_score(
    arm: Arm,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    cv_folds: CVFolds,
    algo_rng: np.random.Generator,
):
    """Núcleo comum de `evaluate` e do portão de validação (ADR 005):
    ajuste do braço, predição e métricas no teste. Fatorado para que os
    dois modos de protocolo compartilhem exatamente a mesma lógica em vez
    de duplicá-la."""
    budget = Budget()
    start_time = time.perf_counter()
    fitted = arm.fit(X_train, y_train, cv_folds, algo_rng, budget)
    y_pred = fitted.predict(X_test)
    wall_time = time.perf_counter() - start_time

    r2 = float(r2_score(y_test, y_pred))
    rmsep = float(np.sqrt(np.mean((y_test - y_pred) ** 2)))
    return fitted, y_pred, r2, rmsep, budget, wall_time


def _selection_of(fitted) -> set[int] | None:
    """Bandas do ajuste final, se o braço seleciona; senão None."""
    selection = getattr(fitted, "selection", None)
    return None if selection is None else {int(j) for j in selection}


def evaluate(
    arm: Arm,
    dataset: Dataset,
    seed_split: int,
    seed_algo: int,
    test_size: float = DEFAULT_TEST_SIZE,
    n_splits: int = DEFAULT_N_SPLITS,
    preprocessor=None,
) -> Result:
    """Avalia um braço num conjunto de dados sob a mesma prova para todos.

    Os dois eixos de semente são gerados a partir de `SeedSequence`s
    independentes: um para a partição treino/teste + folds da CV interna
    (deriva só de `seed_split`), outro para a aleatoriedade interna do
    braço (`seed_algo`). O braço nunca recebe `seed_split` nem vê o teste
    externo — só `X_train`/`y_train` e as folds já prontas.

    Se o conjunto tem réplicas (`dataset.groups`), partição e folds são
    agrupadas: medições da mesma amostra física nunca ficam em lados
    diferentes (ADR 009).
    """
    seed_sequence = np.random.SeedSequence(seed_split)
    split_seed, cv_seed = seed_sequence.spawn(2)
    split_rng = np.random.default_rng(split_seed)
    cv_rng = np.random.default_rng(cv_seed)
    algo_rng = np.random.default_rng(seed_algo)

    train_idx, test_idx = _split_train_test(
        dataset.X.shape[0], test_size, split_rng, groups=dataset.groups
    )
    X_train, y_train = dataset.X[train_idx], dataset.y[train_idx]
    X_test, y_test = dataset.X[test_idx], dataset.y[test_idx]

    # SNV puro, único para todos os braços (PROTOCOLO.md,
    # "Pré-processamento"): escolhido com evidência no Tecator, aprovado
    # pela orientação em 17/09/2026 e aplicado a partir do Estágio 2. É
    # transformação por amostra, então o ajuste nesta posição — antes das
    # folds da CV interna — não vaza. O parâmetro continua existindo para
    # o experimento de comparação injetar os candidatos sem furar o
    # protocolo, nunca para um braço escolher o seu.
    if preprocessor is None:
        preprocessor = SNVPreprocessor()
    preprocessor = preprocessor.fit(X_train)
    X_train = preprocessor.transform(X_train)
    X_test = preprocessor.transform(X_test)

    train_groups = None if dataset.groups is None else dataset.groups[train_idx]
    cv_folds = _make_cv_folds(len(train_idx), n_splits, cv_rng, groups=train_groups)

    fitted, y_pred, r2, rmsep, budget, wall_time = _fit_and_score(
        arm, X_train, y_train, X_test, y_test, cv_folds, algo_rng
    )

    return Result(
        r2=r2,
        rmsep=rmsep,
        rmse_cv=fitted.rmse_cv,
        y_pred=y_pred,
        test_idx=test_idx,
        # A seleção explícita do braço (iPLS, VIP, GA-PLS, CARS), ou None
        # para quem não seleciona. Converter em conjunto comparável, com o
        # k pareado, é a camada de seleção (`tcc.selection`, ADR 018).
        selection=_selection_of(fitted),
        band_scores=fitted.band_scores,
        n_fits=budget.n_fits,
        wall_time=wall_time,
        hyperparams=fitted.hyperparams,
        arm_name=arm.name,
        dataset_name=dataset.name,
        seed_split=seed_split,
        seed_algo=seed_algo,
    )
