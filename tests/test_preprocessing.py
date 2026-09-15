from __future__ import annotations

import numpy as np
import pytest

from tcc.preprocessing import (
    ChainPreprocessor,
    DerivativePreprocessor,
    SNVPreprocessor,
    snv_derivative,
)


@pytest.fixture
def spectra():
    rng = np.random.default_rng(0)
    # Espectros sintéticos: curva lisa + nível DC + ganho, por amostra
    base = np.sin(np.linspace(0, 3 * np.pi, 100))
    offsets = rng.normal(0, 5, size=(20, 1))
    gains = rng.uniform(0.5, 2.0, size=(20, 1))
    return gains * base + offsets + rng.normal(0, 0.01, size=(20, 100))


@pytest.mark.parametrize(
    "make",
    [SNVPreprocessor, DerivativePreprocessor, snv_derivative],
    ids=["snv", "derivative", "snv_derivative"],
)
def test_transform_does_not_depend_on_training_data(make, spectra):
    # Anti-vazamento: ajustado em treinos diferentes, o transform do
    # MESMO teste tem que sair idêntico — prova que nenhuma estatística
    # do treino participa. Para transformações por amostra é trivial por
    # construção, mas o teste guarda o invariante caso um pré-processador
    # entre-amostras entre na cadeia no futuro.
    X_train_a, X_train_b = spectra[:10], spectra[10:]
    X_test = spectra[5:8] + 1.23

    out_a = make().fit(X_train_a).transform(X_test)
    out_b = make().fit(X_train_b).transform(X_test)

    np.testing.assert_array_equal(out_a, out_b)


def test_snv_normalizes_each_row(spectra):
    out = SNVPreprocessor().fit(spectra).transform(spectra)

    np.testing.assert_allclose(out.mean(axis=1), 0.0, atol=1e-12)
    np.testing.assert_allclose(out.std(axis=1), 1.0, atol=1e-12)


def test_derivative_removes_dc_level(spectra):
    # Derivada é invariante a deslocamento constante: somar um nível DC
    # por amostra não pode mudar a saída.
    prep = DerivativePreprocessor()
    shifted = spectra + np.full((spectra.shape[0], 1), 7.5)

    np.testing.assert_allclose(
        prep.fit(spectra).transform(spectra),
        prep.fit(shifted).transform(shifted),
        atol=1e-10,
    )


def test_derivative_of_linear_ramp_is_constant():
    # Primeira derivada de uma rampa linear é constante = inclinação
    # (em unidades de índice de canal, o passo que o savgol assume).
    ramp = np.tile(2.0 * np.arange(100.0), (3, 1))
    out = DerivativePreprocessor().fit(ramp).transform(ramp)

    np.testing.assert_allclose(out, 2.0, atol=1e-8)


def test_chain_equals_manual_composition(spectra):
    chained = snv_derivative().fit(spectra).transform(spectra)

    snv_out = SNVPreprocessor().fit(spectra).transform(spectra)
    manual = DerivativePreprocessor().fit(snv_out).transform(snv_out)

    np.testing.assert_allclose(chained, manual)


def test_chain_preserves_shape(spectra):
    out = snv_derivative().fit(spectra).transform(spectra)
    assert out.shape == spectra.shape
    assert isinstance(snv_derivative(), ChainPreprocessor)
