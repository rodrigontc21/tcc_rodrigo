from __future__ import annotations

import numpy as np
import pytest

from tcc.arms.mean import MeanArm
from tcc.data import load
from tcc.protocol import DEFAULT_TEST_SIZE, _split_train_test, evaluate

ALL_DATASETS = ["gasoline", "tecator", "mango", "bioprocess"]

# Pinos por dataset: (n, p, unit, y_min, y_max) conferidos contra as
# fontes na ingestão de 14/09 (gasoline: 60/401 e octanagem 83,4-89,6 do
# artigo; mango: CSV v3 traz 12.011 (safras 1-5), cortado para 11.691
# (safras 1-4) pelo ADR 006, e 306 bandas menos 25 constantes (adendo de
# 28/10 ao ADR 006); bioprocess: 6.960 espectros menos 488 sem rótulo de
# glicose)
EXPECTED = {
    "gasoline": (60, 401, "nm", 83.4, 89.6),
    "tecator": (215, 100, "nm", 0.9, 49.1),
    "mango": (11691, 281, "nm", 9.46, 24.58),
    "bioprocess": (6472, 1870, "cm-1", 0.0, 19.99),
}

# Número de amostras físicas por conjunto (ADR 009), conferido na
# identificação de réplicas: tecator 148 únicas + 30 pares + 1 trio + 1
# quarteto, pela regra decidida em 09/11/2026 (eram 208 grupos só com as
# vizinhas); mango em geral 2 leituras por fruto (até 6); bioprocess toda
# amostra medida 2+ vezes.
# None = sem evidência de réplicas.
EXPECTED_GROUPS = {
    "gasoline": None,
    "tecator": 180,
    "mango": 4677,
    "bioprocess": 3191,
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


def test_tecator_axis_is_850_to_1048_in_2nm_steps():
    # ADR 004: eixo por indicação da orientação, não o linspace do fda.usc.
    # O canal 40 é a "banda de 931 nm" do paper (pgsg_0), que neste eixo
    # fica em 930 nm — comparações com o paper se ancoram no índice do canal.
    axis = load("tecator").axis
    np.testing.assert_array_equal(axis, 850.0 + 2.0 * np.arange(100))
    assert axis[40] == 930.0


def test_expected_shape_unit_and_target_range(any_dataset):
    n, p, unit, y_min, y_max = EXPECTED[any_dataset.name]
    assert any_dataset.X.shape == (n, p)
    assert any_dataset.unit == unit
    assert any_dataset.y.min() == pytest.approx(y_min, abs=0.01)
    assert any_dataset.y.max() == pytest.approx(y_max, abs=0.01)


def test_no_constant_band(any_dataset):
    # Canal com o mesmo valor em todas as amostras não carrega informação e
    # quebrou o iPLS no Mango (adendo de 28/10 ao ADR 006).
    X = any_dataset.X
    assert not np.any(np.all(X == X[0], axis=0))


def test_load_is_deterministic(any_dataset):
    # Segunda carga do mesmo dataset produz o mesmo hash de conteúdo
    assert load(any_dataset.name).sha256 == any_dataset.sha256


def _effective_n(groups: np.ndarray | None, mask: np.ndarray) -> float:
    """Tamanho efetivo de Kish, (Σm)²/Σm²: número de observações
    independentes quando réplicas repetem o mesmo y. Sem grupos, cada linha
    é independente e o tamanho efetivo é o número de linhas."""
    if groups is None:
        return float(mask.sum())
    sizes = np.bincount(np.unique(groups[mask], return_inverse=True)[1])
    return float(sizes.sum() ** 2 / (sizes**2).sum())


def test_mean_arm_r2_offset_matches_theory(any_dataset):
    """Propriedade do Estágio 0 (protocolo), verificada nos 4 conjuntos:
    para o MeanArm, a média do R² sobre muitas seed_split é ≈ -1/n_ef, com
    n_ef o tamanho efetivo do teste, nunca 0 — R² igual a zero indicaria
    média calculada no teste (vazamento na métrica, diagnóstico da
    orientação de 27/08).

    n_ef e não n_test: réplicas da mesma amostra têm o mesmo y, então não
    são observações independentes (ADR 009). Sem grupos, n_ef = n_test.

    Tolerância, termo a termo (nada arbitrário):
    - o alvo -1/n_ef do teste é o termo dominante da esperança teórica
      E[R²] ≈ -(1/n_ef_teste + 1/n_ef_treino); o termo do treino fica
      deliberadamente fora do alvo e entra como folga de viés;
    - 3 erros-padrão da média (dp/sqrt(N)) cobrem o ruído amostral de
      estimar essa média com N sementes.
    Apertar além disso exigiria modelar o viés de razão do R² e a
    assimetria de y, que variam por conjunto."""
    n_seeds = 100  # mesma escala do run_mean_baseline.py
    n = any_dataset.X.shape[0]
    r2_values, n_ef_test, n_ef_train = [], [], []
    for seed_split in range(n_seeds):
        result = evaluate(MeanArm(), any_dataset, seed_split=seed_split, seed_algo=0)
        r2_values.append(result.r2)
        in_test = np.zeros(n, dtype=bool)
        in_test[result.test_idx] = True
        n_ef_test.append(_effective_n(any_dataset.groups, in_test))
        n_ef_train.append(_effective_n(any_dataset.groups, ~in_test))

    mean_r2 = float(np.mean(r2_values))
    std_error = float(np.std(r2_values, ddof=1) / np.sqrt(n_seeds))

    expected = -1.0 / np.mean(n_ef_test)
    tolerance = 1.0 / np.mean(n_ef_train) + 3.0 * std_error
    assert mean_r2 == pytest.approx(expected, abs=tolerance)


def test_partition_is_deterministic_given_seed_split(any_dataset):
    # Mesma derivação de semente usada em evaluate(): partição depende só
    # de seed_split, para qualquer tamanho de conjunto — inclusive no
    # caminho agrupado, com os grupos de réplica do próprio conjunto
    n = any_dataset.X.shape[0]
    idx = []
    for _ in range(2):
        split_seed, _ = np.random.SeedSequence(7).spawn(2)
        rng = np.random.default_rng(split_seed)
        idx.append(_split_train_test(n, DEFAULT_TEST_SIZE, rng, groups=any_dataset.groups))
    np.testing.assert_array_equal(idx[0][0], idx[1][0])
    np.testing.assert_array_equal(idx[0][1], idx[1][1])


def test_replicate_groups_match_expected(any_dataset):
    expected = EXPECTED_GROUPS[any_dataset.name]
    if expected is None:
        assert any_dataset.groups is None
        return
    assert len(any_dataset.groups) == any_dataset.X.shape[0]
    assert len(np.unique(any_dataset.groups)) == expected


def test_replicates_never_straddle_train_test(any_dataset):
    """Guarda do ADR 009: medições da mesma amostra física nunca ficam uma
    no treino e outra no teste — o modelo veria a resposta de graça."""
    if any_dataset.groups is None:
        pytest.skip("conjunto sem réplicas identificadas")
    n = any_dataset.X.shape[0]
    for seed_split in range(10):
        result = evaluate(MeanArm(), any_dataset, seed_split=seed_split, seed_algo=0)
        in_test = np.zeros(n, dtype=bool)
        in_test[result.test_idx] = True
        shared = set(any_dataset.groups[in_test]) & set(any_dataset.groups[~in_test])
        assert not shared, f"seed_split={seed_split}: {len(shared)} grupos dos dois lados"


@pytest.mark.parametrize(
    "name",
    [
        "gasoline",
        # Era falha esperada estrita até a correção de 09/11/2026 (ADR 009):
        # 20 dos 22 pares de espectros idênticos do Tecator ficavam em grupos
        # diferentes.
        "tecator",
        "mango",
        "bioprocess",
    ],
)
def test_identical_spectra_with_identical_target_share_a_group(name):
    """Espectro idêntico, bit a bit, com o mesmo alvo é a mesma amostra
    medida duas vezes, e não pode cair em grupos diferentes. Num conjunto
    sem grupos, não pode haver nenhum par assim."""
    ds = load(name)
    blocks: dict[tuple[bytes, float], list[int]] = {}
    for i, (x, y) in enumerate(zip(ds.X, ds.y)):
        blocks.setdefault((x.tobytes(), float(y)), []).append(i)
    replicated = [rows for rows in blocks.values() if len(rows) > 1]
    if ds.groups is None:
        assert not replicated, f"{len(replicated)} réplicas num conjunto sem grupos"
        return
    split = [rows for rows in replicated if len({ds.groups[j] for j in rows}) > 1]
    assert not split, f"{len(split)} de {len(replicated)} réplicas em grupos diferentes"


def test_replicate_rule_links_neighbours_identical_and_close_spectra():
    """Regra do ADR 009 para o Tecator (09/11/2026): alvo idêntico e, além
    disso, vizinhança (A), espectro idêntico (B) ou espectro próximo (C)."""
    from tcc.data import _tecator_replicate_groups

    X = np.array([
        [0.0, 0.0],   # 0 ┐ A: vizinhas, alvo igual
        [5.0, 5.0],   # 1 ┘
        [1.0, 1.0],   # 2 ┐ B: espectro idêntico, alvo igual
        [9.0, 9.0],   # 3   isolada
        [1.0, 1.0],   # 4 ┘
        [2.0, 2.0],   # 5 ┐ C: espectro a 0,1, alvo igual
        [7.0, 7.0],   # 6   isolada
        [2.1, 2.0],   # 7 ┘
        [3.0, 3.0],   # 8   espectro idêntico ao 9, alvo diferente: não junta
        [3.0, 3.0],   # 9
        [4.0, 4.0],   # 10  alvo igual ao 11, espectro longe e não vizinho
        [6.0, 6.0],   # 11
        [8.0, 8.0],   # 12
    ])
    targets = np.array(
        [[1.0], [1.0], [2.0], [99.0], [2.0], [3.0], [98.0], [3.0],
         [4.0], [5.0], [6.0], [97.0], [6.0]]
    )
    # 10 e 12: mesmo alvo, não vizinhas, espectros a 4,0: não juntam
    g = _tecator_replicate_groups(X, targets, threshold=0.30)
    assert g[0] == g[1]
    assert g[2] == g[4]
    assert g[5] == g[7]
    assert g[8] != g[9]
    assert g[10] != g[12]
    assert len(np.unique(g)) == 10
    # rótulos na ordem da primeira linha de cada grupo
    assert g.tolist()[:4] == [0, 0, 1, 2]


def test_replicate_rule_uses_connected_components_not_pairs():
    """Cadeia 0—1 (vizinhas), 1—5 (espectro idêntico): 0 e 5 não se ligam
    diretamente, mas são a mesma amostra (nota (a) da orientação)."""
    from tcc.data import _tecator_replicate_groups

    X = np.array([[0.0], [1.0], [5.0], [6.0], [7.0], [1.0]])
    targets = np.array([[1.0], [1.0], [2.0], [3.0], [4.0], [1.0]])
    g = _tecator_replicate_groups(X, targets, threshold=0.30)
    assert g[0] == g[1] == g[5]
    assert len(np.unique(g)) == 4

    # Linhas 0, 2 e 4, não vizinhas: 0—4 e 2—4 a 0,2 de distância, 0—2 a
    # 0,4. A ligação 0—4 põe o 4 sob o 0; a 2—4 chega depois e, sem subir
    # até a raiz, sobrescreveria esse vínculo e soltaria o 0.
    X = np.array([[0.0], [9.0], [0.4], [8.0], [0.2]])
    targets = np.array([[1.0], [2.0], [1.0], [3.0], [1.0]])
    g = _tecator_replicate_groups(X, targets, threshold=0.30)
    assert g[0] == g[2] == g[4]


@pytest.fixture(scope="module")
def tecator_targets():
    import skfda.datasets

    _, frame = skfda.datasets.fetch_tecator(return_X_y=True, as_frame=True)
    return frame[["fat", "water", "protein"]].to_numpy(dtype=float)


def test_tecator_groups_match_the_09_11_decision(tecator_targets):
    """Os números de `verify_tecator_replicates.py` (orientação, 09/11/2026),
    reproduzidos nos dados do loader, que são os mesmos do pgsg linha a
    linha: 180 grupos, com um quarteto e um trio."""
    ds = load("tecator")
    _, sizes = np.unique(ds.groups, return_counts=True)
    assert dict(zip(*np.unique(sizes, return_counts=True))) == {1: 148, 2: 30, 3: 1, 4: 1}
    g = ds.groups
    assert g[57] == g[58] == g[134] == g[191]
    assert g[63] == g[149] == g[177]
    # os outros 7 pares da relação C (os 5 restantes estão no quarteto e
    # no trio acima), da tabela da orientação
    for i, j in [(10, 131), (113, 166), (7, 174), (114, 209), (4, 173), (3, 130), (101, 162)]:
        assert g[i] == g[j], (i, j)
    # alvo idêntico por acaso, espectros longe (percentis 37 a 40): não juntam
    for i, j in [(122, 169), (39, 169), (19, 152)]:
        assert g[i] != g[j], (i, j)
    # limitação declarada: espectro muito próximo, alvo diferente
    assert g[60] != g[68] and g[61] != g[68]


@pytest.mark.parametrize("threshold, n_groups", [(0.10, 182), (0.15, 180), (0.40, 180), (0.45, 179)])
def test_tecator_threshold_plateau(tecator_targets, threshold, n_groups):
    """Qualquer limite de 0,15 a 0,40 dá os mesmos 180 grupos; fora dessa
    faixa, a contagem muda. É o platô que justifica o 0,30 declarado."""
    from tcc.data import TECATOR_SPECTRAL_THRESHOLD, _tecator_replicate_groups

    ds = load("tecator")
    g = _tecator_replicate_groups(ds.X, tecator_targets, threshold=threshold)
    assert len(np.unique(g)) == n_groups
    if n_groups == 180:
        assert np.array_equal(g, ds.groups)
    assert TECATOR_SPECTRAL_THRESHOLD == 0.30


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
