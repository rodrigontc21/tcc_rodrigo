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


# Tamanho do treino da divisão da literatura de cada conjunto: 172/43 no
# Tecator (ADR 005), 48/12 no Gasoline (ADR 010)
LITERATURE_N_TRAIN = {"tecator": 172, "gasoline": 48}


@pytest.fixture(scope="module")
def tecator():
    return load("tecator")


@pytest.fixture(scope="module")
def gasoline():
    return load("gasoline")


@pytest.fixture(scope="module", params=sorted(LITERATURE_N_TRAIN))
def literature_dataset(request):
    return load(request.param)


def test_partition_is_fixed_and_deterministic(literature_dataset):
    # A divisão da literatura não depende de semente nenhuma do protocolo:
    # duas chamadas entregam ao braço exatamente os mesmos dados, com o
    # tamanho de treino da divisão publicada.
    spy1, spy2 = SpyArm(), SpyArm()
    evaluate_against_literature(spy1, literature_dataset)
    evaluate_against_literature(spy2, literature_dataset)

    n_train = LITERATURE_N_TRAIN[literature_dataset.name]
    assert spy1.received_X.shape == (n_train, literature_dataset.X.shape[1])
    np.testing.assert_array_equal(spy1.received_X, spy2.received_X)
    np.testing.assert_array_equal(spy1.received_y, spy2.received_y)


def test_return_type_is_structurally_distinct_from_result(literature_dataset):
    # A proteção prometida pelo ADR 005: o tipo de retorno não é Result
    # nem carrega os campos de semente — um LiteratureResult não encaixa
    # na grade nem na decomposição, por construção.
    r = evaluate_against_literature(SpyArm(), literature_dataset)

    assert isinstance(r, LiteratureResult)
    assert not isinstance(r, Result)
    assert not hasattr(r, "seed_split")
    assert not hasattr(r, "seed_algo")


@pytest.mark.parametrize("name", ["mango", "bioprocess", "outro"])
def test_rejects_datasets_without_defined_literature_split(tecator, name):
    # Os arrays são do Tecator de propósito: a rejeição depende só do nome,
    # e carregar Mango/bioprocess de verdade só deixaria o teste lento.
    other = Dataset(
        X=tecator.X, y=tecator.y, axis=tecator.axis, unit="nm",
        name=name, sha256=tecator.sha256,
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


def test_reproduces_published_gasoline_pls(gasoline):
    # Portão de validação no Gasoline (ADR 010): PLS H=5, o H que o paper
    # obteve pela regra de um erro-padrão, contra os números publicados
    # (pgsg_0, Seção 4.2 e Tabela 1: R² = 0,975, RMSE = 0,145, escala
    # normalizada). A divisão sequencial 48/12 daria R² 0,923; este teste
    # falha se alguém trocar a divisão sem revisar o ADR 010.
    #
    # Tolerância 5e-4 = meia unidade da 3ª casa publicada, a precisão real
    # do paper. A tolerância anterior (1e-3) aceitava 34 das 20000 sementes
    # da auditoria; 5e-4 aceita 9, e rejeita a 239, que passava antes
    # (verificação por mutação no adendo do ADR 010).
    r = evaluate_against_literature(PLSArm(n_components=5), gasoline)

    assert r.arm_name == "pls_full(h=5)"
    assert r.dataset_name == "gasoline"
    assert r.r2 == pytest.approx(0.975, abs=5e-4)
    assert r.rmsep == pytest.approx(0.145, abs=5e-4)
