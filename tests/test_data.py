from __future__ import annotations

import numpy as np
import pytest

from tcc.arms.mean import MeanArm
from tcc.data import load
from tcc.protocol import DEFAULT_TEST_SIZE, _split_train_test, evaluate

ALL_DATASETS = ["gasoline", "tecator", "mango", "bioprocess"]

# Pinos por dataset: (n, p, unit, y_min, y_max) conferidos contra as
# fontes na ingestão de 14/09 (gasoline: 60/401 e octanagem 83,4-89,6 do
# artigo; mango: CSV v3 atualizado em 2024, com a safra 5 extra; bioprocess:
# 6.960 espectros menos 488 sem rótulo de glicose)
EXPECTED = {
    "gasoline": (60, 401, "nm", 83.4, 89.6),
    "tecator": (215, 100, "nm", 0.9, 49.1),
    "mango": (12011, 306, "nm", 9.46, 24.58),
    "bioprocess": (6472, 1870, "cm-1", 0.0, 19.99),
}


@pytest.fixture(scope="module", params=ALL_DATASETS)
def any_dataset(request):
    return load(request.param)


def test_shapes_are_coherent(any_dataset):
    d = any_dataset
    assert d.X.ndim == 2
    assert d.y.ndim == 1
    assert d.X.shape[0] == len(d.y)


def test_no_nan_in_X_or_y(any_dataset):
    assert not np.isnan(any_dataset.X).any()
    assert not np.isnan(any_dataset.y).any()


def test_axis_matches_number_of_bands(any_dataset):
    assert len(any_dataset.axis) == any_dataset.X.shape[1]


def test_expected_shape_unit_and_target_range(any_dataset):
    n, p, unit, y_min, y_max = EXPECTED[any_dataset.name]
    assert any_dataset.X.shape == (n, p)
    assert any_dataset.unit == unit
    assert any_dataset.y.min() == pytest.approx(y_min, abs=0.01)
    assert any_dataset.y.max() == pytest.approx(y_max, abs=0.01)


def test_load_is_deterministic(any_dataset):
    # Segunda carga do mesmo dataset produz o mesmo hash de conteúdo
    assert load(any_dataset.name).sha256 == any_dataset.sha256


def test_mean_arm_r2_offset_matches_theory(any_dataset):
    """Propriedade do Estágio 0 (protocolo), verificada nos 4 conjuntos:
    para o MeanArm, a média do R² sobre muitas seed_split é ≈ -1/n_test,
    nunca 0 — R² igual a zero indicaria média calculada no teste
    (vazamento na métrica, diagnóstico da orientação de 27/08).

    Tolerância, termo a termo (nada arbitrário):
    - o alvo -1/n_test é o termo dominante da esperança teórica
      E[R²] ≈ -(1/n_test + 1/n_train); o termo seguinte, 1/n_train, fica
      deliberadamente fora do alvo e entra como folga de viés;
    - 3 erros-padrão da média (dp/sqrt(N)) cobrem o ruído amostral de
      estimar essa média com N sementes.
    Apertar além disso exigiria modelar o viés de razão do R² e a
    assimetria de y, que variam por conjunto."""
    n_seeds = 100  # mesma escala do run_mean_baseline.py
    r2_values = []
    for seed_split in range(n_seeds):
        result = evaluate(MeanArm(), any_dataset, seed_split=seed_split, seed_algo=0)
        r2_values.append(result.r2)

    n_test = len(result.test_idx)
    n_train = any_dataset.X.shape[0] - n_test
    mean_r2 = float(np.mean(r2_values))
    std_error = float(np.std(r2_values, ddof=1) / np.sqrt(n_seeds))

    expected = -1.0 / n_test
    tolerance = 1.0 / n_train + 3.0 * std_error
    assert mean_r2 == pytest.approx(expected, abs=tolerance)


def test_partition_is_deterministic_given_seed_split(any_dataset):
    # Mesma derivação de semente usada em evaluate(): partição depende só
    # de seed_split, para qualquer tamanho de conjunto
    n = any_dataset.X.shape[0]
    idx = []
    for _ in range(2):
        split_seed, _ = np.random.SeedSequence(7).spawn(2)
        rng = np.random.default_rng(split_seed)
        idx.append(_split_train_test(n, DEFAULT_TEST_SIZE, rng))
    np.testing.assert_array_equal(idx[0][0], idx[1][0])
    np.testing.assert_array_equal(idx[0][1], idx[1][1])


@pytest.fixture(scope="module")
def tecator():
    return load("tecator")


def test_tecator_target_matches_known_fat_values(tecator):
    """Guarda de regressão do ADR 004: o alvo carregado é a coluna fat.

    Os valores de referência são os do fda.usc, confirmados equivalentes
    aos do OpenML 505 usado pelo paper (min 0,9 / max 49,1 / média 18,14).
    Se a seleção por nome regredir para outra coluna — water tem faixa
    39,3-76,6, protein 11,0-21,8 — os três limites falham juntos."""
    y = tecator.y

    assert y.min() == pytest.approx(0.9, abs=0.01)
    assert y.max() == pytest.approx(49.1, abs=0.01)
    assert y.mean() == pytest.approx(18.14, abs=0.01)
