"""Portão de validação contra a literatura (ADR 005).

Segundo modo de protocolo, exclusivo do Estágio 2: reproduz o desenho dos
artigos de referência (divisão fixa do conjunto, Z-score no treino) para
checar implementações contra valores publicados. NUNCA entra na grade
principal nem na decomposição — e a proteção é estrutural, não
disciplinar: `evaluate_against_literature` não tem `seed_split` na
assinatura (não encaixa nos eixos da grade) e devolve `LiteratureResult`,
que o Estágio 7 não aceita no lugar de `Result`.

O núcleo (ajuste do braço, métricas) é compartilhado com `evaluate` via
`protocol._fit_and_score` — mesma lógica, nunca duplicada.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.model_selection import train_test_split

from tcc.arms.base import Arm
from tcc.data import Dataset
from tcc.protocol import DEFAULT_N_SPLITS, _fit_and_score, _make_cv_folds

# Divisão padrão do Tecator: 172 = 129 (treino) + 43 (monitoramento)
# contra os últimos 43 de teste, sequencial na ordem original do conjunto.
# Aprovada em 01/09 para uso uniforme em todos os braços validados contra
# a literatura neste conjunto (ADR 005).
N_TRAIN_TECATOR = 172

# Divisão 48/12 do Gasoline (ADR 010, proposto): o paper só diz "48/12";
# train_test_split(test_size=0.2, random_state=42) reproduz os números
# publicados do PLS (R² 0,975, RMSE 0,145) até a terceira casa, e a
# divisão sequencial não (R² 0,923). Hipótese inferida, não documentada.
GASOLINE_TEST_SIZE = 0.2
GASOLINE_SPLIT_SEED = 42


def _literature_split(dataset: Dataset) -> tuple[np.ndarray, np.ndarray]:
    """Índices (treino, teste) da divisão da literatura de cada conjunto.
    Só Tecator e Gasoline têm divisão definida; os outros dois são
    rejeitados."""
    n = dataset.X.shape[0]
    if dataset.name == "tecator":
        return np.arange(N_TRAIN_TECATOR), np.arange(N_TRAIN_TECATOR, n)
    if dataset.name == "gasoline":
        train_idx, test_idx = train_test_split(
            np.arange(n), test_size=GASOLINE_TEST_SIZE, random_state=GASOLINE_SPLIT_SEED
        )
        return np.sort(train_idx), np.sort(test_idx)
    raise ValueError(
        f"protocolo da literatura só definido para 'tecator' (172/43) e "
        f"'gasoline' (48/12); recebido {dataset.name!r}"
    )

# Sementes fixas e documentadas deste modo: as folds internas e o gerador
# do braço precisam existir pelo contrato de Arm.fit, mas aqui não há eixo
# de semente — braços determinísticos (PLS, iPLS, VIP) as ignoram.
# Provisório: quando um braço estocástico passar pelo portão, a dispersão
# entre sementes vira parte da validação e isto precisa ser revisto.
_LITERATURE_CV_SEED = 0
_LITERATURE_ALGO_SEED = 0


@dataclass(frozen=True, eq=False)
class LiteratureResult:
    """Saída do portão de validação. Deliberadamente NÃO é um `Result`:
    sem seed_split/seed_algo (não existem neste modo) e sem os campos que
    a grade e a decomposição consomem — um LiteratureResult não tem como
    ser agregado junto aos resultados do protocolo único por engano.

    `r2` e `rmsep` estão na escala normalizada (Z-score do treino), como
    os papers reportam; `rmse_original` desfaz a normalização do alvo,
    para leitura em unidades químicas.
    """

    r2: float
    rmsep: float
    rmse_original: float
    hyperparams: dict
    arm_name: str
    dataset_name: str


def evaluate_against_literature(arm: Arm, dataset: Dataset) -> LiteratureResult:
    """Avalia um braço sob o protocolo da literatura: divisão fixa e
    Z-score (espectro e alvo) ajustado só no treino."""
    train_idx, test_idx = _literature_split(dataset)

    X, y = dataset.X, dataset.y
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    # Z-score ajustado SÓ no treino, espectro e alvo — protocolo do paper
    x_mean, x_std = X_train.mean(axis=0), X_train.std(axis=0, ddof=0)
    y_mean, y_std = y_train.mean(), y_train.std(ddof=0)

    Xz_train = (X_train - x_mean) / x_std
    Xz_test = (X_test - x_mean) / x_std
    yz_train = (y_train - y_mean) / y_std
    yz_test = (y_test - y_mean) / y_std

    # A divisão treino/teste é a do artigo (fixa, não agrupável), mas as
    # folds internas são nossas: réplicas do treino ficam no mesmo fold.
    train_groups = None if dataset.groups is None else dataset.groups[train_idx]
    cv_folds = _make_cv_folds(
        len(y_train),
        DEFAULT_N_SPLITS,
        np.random.default_rng(_LITERATURE_CV_SEED),
        groups=train_groups,
    )
    fitted, _, r2, rmsep, _, _ = _fit_and_score(
        arm,
        Xz_train,
        yz_train,
        Xz_test,
        yz_test,
        cv_folds,
        np.random.default_rng(_LITERATURE_ALGO_SEED),
    )

    return LiteratureResult(
        r2=r2,
        rmsep=rmsep,
        rmse_original=rmsep * float(y_std),
        hyperparams=fitted.hyperparams,
        arm_name=arm.name,
        dataset_name=dataset.name,
    )
