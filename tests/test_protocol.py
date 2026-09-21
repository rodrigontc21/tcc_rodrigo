from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pytest

from tcc.arms.base import Budget, CVFolds
from tcc.arms.mean import MeanArm
from tcc.arms.permuted import PermutedYArm
from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.protocol import _make_cv_folds, _split_train_test, evaluate


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


def _result_key(result) -> str:
    """Chave estável de um Result para o teste anti-réplica.

    Deriva de y_pred e test_idx: juntos eles determinam partição e saída
    do braço. Réplicas com a mesma chave indicam propagação de semente
    quebrada (ver checklist do pipeline, Estágio 5)."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(result.test_idx).tobytes())
    h.update(np.ascontiguousarray(result.y_pred).tobytes())
    return h.hexdigest()


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


def test_permuted_y_wrapping_pls_has_no_skill_on_average(tecator):
    """Sonda de vazamento com um braço que usa X: PermutedYArm(PLSArm())
    nas 30 seed_split da faixa exploratória (0-29, PROTOCOLO.md), com
    seed_algo=0 e o pré-processador padrão de evaluate().

    Com y permutado no treino, as predições do teste não têm como carregar
    informação sobre o y verdadeiro do teste — a não ser que ele chegue ao
    modelo por um caminho que não passe pela permutação. Nesse caso o R²
    médio fica positivo.

    Limiar: R² médio ≤ 0. Um preditor sem informação sobre y_test tem R²
    esperado ≤ 0 (o MeanArm já fica em ≈ −1/n_ef; um PLS ajustado a ruído
    fica abaixo disso). Distribuição observada nas 30 partições
    (results/permuted_y_pls_tecator.md, 21/09/2026): média −0,0474, dp
    0,0849, máximo +0,1005. O erro-padrão da média é 0,0849/√30 ≈ 0,0155,
    então o limiar fica ~3 erros-padrão acima do observado. Não se usa
    limiar por partição: R² isolados chegam a +0,10 sem vazamento algum,
    e qualquer corte ali seria arbitrário.

    O que este teste pega e o de MeanArm não pega: y verdadeiro chegando ao
    braço sem passar pela permutação. Verificado em 21/09/2026 com uma
    sonda que não embaralha: R² médio +0,954 com PLS (falha aqui), −0,035
    com MeanArm (cego, porque ignora X). O que ele NÃO pega: vazamento só
    de X, como um pré-processador ajustado em treino+teste. Sem y, esse
    vazamento não dá habilidade ao modelo; verificado por mutação em
    21/09/2026 (autoscaling em treino+teste: resultado idêntico, porque o
    PLSRegression já autoescala; PCA em treino+teste: R² médio −0,074).
    """
    r2 = [
        evaluate(PermutedYArm(PLSArm()), tecator, seed_split=s, seed_algo=0).r2
        for s in range(30)
    ]

    assert np.mean(r2) <= 0.0, f"R² médio {np.mean(r2):+.4f} com y permutado"


def test_no_identical_replicas_across_seed_split(tecator):
    """Anti-réplica no eixo seed_split (checklist do pipeline, Estágio 5).

    Partições diferentes têm que produzir resultados diferentes, para
    qualquer braço — inclusive os determinísticos, porque o que varia é o
    dado, não o algoritmo. Chave repetida entre seed_split distintos
    indica propagação de semente quebrada (ex.: partição congelada num
    valor fixo), que de outro modo passaria silenciosa."""
    keys = [
        _result_key(evaluate(MeanArm(), tecator, seed_split=s, seed_algo=0))
        for s in range(10)
    ]

    assert len(set(keys)) == len(keys)


def test_deterministic_arm_replicas_across_seed_algo_are_identical(tecator):
    """Exceção declarada do anti-réplica: braço determinístico no eixo
    seed_algo.

    PLS, iPLS e limiarização de VIP são determinísticos dado o conjunto
    de treino; o MeanArm representa essa classe aqui. Para eles, variar
    seed_algo com seed_split fixo NÃO muda nada — resultados idênticos
    são o comportamento correto, não réplica quebrada. O pipeline exige
    que essa exceção seja declarada, e este teste é a declaração em
    código, para não virar conhecimento tácito."""
    keys = {
        _result_key(evaluate(MeanArm(), tecator, seed_split=0, seed_algo=a))
        for a in (0, 1, 999)
    }

    assert len(keys) == 1


def test_stochastic_arm_replicas_across_seed_algo_are_distinct(tecator):
    """Contraparte estocástica da exceção acima: para braço que usa
    rng_algo, variar seed_algo TEM que mudar o resultado. Sem isto, a
    exceção dos determinísticos viraria desculpa para mascarar propagação
    quebrada de seed_algo em braços estocásticos."""
    keys = {
        _result_key(evaluate(RandomArm(), tecator, seed_split=0, seed_algo=a))
        for a in (0, 1, 999)
    }

    assert len(keys) == 3


def _paired_groups(n_groups: int, seed: int) -> np.ndarray:
    """Grupos de réplica sintéticos: cada amostra física aparece duas vezes,
    em posições embaralhadas (réplicas não necessariamente vizinhas)."""
    return np.random.default_rng(seed).permutation(np.repeat(np.arange(n_groups), 2))


def test_grouped_split_keeps_replicates_together():
    groups = _paired_groups(100, seed=0)
    for seed in range(50):
        train, test = _split_train_test(len(groups), 0.25, np.random.default_rng(seed), groups)
        assert not set(groups[train]) & set(groups[test]), f"seed={seed}"
        assert len(train) + len(test) == len(groups)


def test_grouped_folds_keep_replicates_together():
    groups = _paired_groups(80, seed=1)
    for seed in range(50):
        folds = _make_cv_folds(len(groups), 5, np.random.default_rng(seed), groups)
        seen = np.zeros(len(groups), dtype=int)
        for fold_train, fold_val in folds:
            assert not set(groups[fold_train]) & set(groups[fold_val]), f"seed={seed}"
            seen[fold_val] += 1
        # cada linha é validação em exatamente um fold
        assert np.all(seen == 1)


def test_singleton_groups_reproduce_ungrouped_partition():
    """Compatibilidade do ADR 009: com grupos unitários, a partição e as
    folds agrupadas são idênticas às não agrupadas — o caminho novo
    generaliza o antigo, não o substitui."""
    n = 215
    singletons = np.arange(n)
    for seed in range(20):
        plain = _split_train_test(n, 0.25, np.random.default_rng(seed))
        grouped = _split_train_test(n, 0.25, np.random.default_rng(seed), singletons)
        np.testing.assert_array_equal(plain[0], grouped[0])
        np.testing.assert_array_equal(plain[1], grouped[1])

        plain_folds = _make_cv_folds(161, 5, np.random.default_rng(seed))
        grouped_folds = _make_cv_folds(161, 5, np.random.default_rng(seed), np.arange(161))
        for (pt, pv), (gt, gv) in zip(plain_folds, grouped_folds):
            np.testing.assert_array_equal(pt, gt)
            np.testing.assert_array_equal(pv, gv)


class _FoldSpyArm:
    """Captura as folds que evaluate() injeta, para conferir a fiação dos
    grupos até a CV interna."""

    name = "fold_spy"

    def __init__(self):
        self.cv_folds = None

    def fit(self, X_train, y_train, cv_folds, rng_algo, budget):
        self.cv_folds = cv_folds
        budget.increment()
        return _FittedZeroArm()


def test_evaluate_keeps_replicates_in_the_same_cv_fold(tecator):
    spy = _FoldSpyArm()
    result = evaluate(spy, tecator, seed_split=0, seed_algo=0)

    in_test = np.zeros(tecator.X.shape[0], dtype=bool)
    in_test[result.test_idx] = True
    train_groups = tecator.groups[~in_test]
    for fold_train, fold_val in spy.cv_folds:
        assert not set(train_groups[fold_train]) & set(train_groups[fold_val])


def test_grouped_split_does_not_favor_large_groups():
    """Regressão do viés de tamanho (ADR 009): ordenar os grupos pela
    primeira aparição de qualquer membro na permutação puxa grupos grandes
    para o teste (no Mango, frutos de 6 leituras ocupavam 54% do teste
    contra 32% do conjunto). Aqui metade das linhas está em grupos de 6; a
    fração delas no teste, na média de 200 sementes, tem que ficar em 1/2.

    Tolerância: a fração por semente tem dp ≈ 0,12 (≈12 grupos de 6 num
    teste de 150 linhas), então o erro-padrão da média de 200 é ≈ 0,009;
    0,03 são ~3 erros-padrão."""
    groups = np.concatenate([np.arange(300), np.repeat(np.arange(300, 350), 6)])
    groups = np.random.default_rng(2).permutation(groups)
    in_big_group = groups >= 300
    fractions = []
    for seed in range(200):
        _, test = _split_train_test(len(groups), 0.25, np.random.default_rng(seed), groups)
        fractions.append(in_big_group[test].mean())
    assert np.mean(fractions) == pytest.approx(0.5, abs=0.03)
