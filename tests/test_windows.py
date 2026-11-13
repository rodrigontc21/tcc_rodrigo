"""Janelas de plausibilidade química (docs/janelas_quimicas.md; ADR 019)."""

from __future__ import annotations

import numpy as np
import pytest

from tcc.data import load
from tcc.metrics import fraction_in_windows
from tcc.windows import BANDS, ROLES, windows

# As posições do alvo, como estão em docs/janelas_quimicas.md. Se alguém
# mudar uma banda no código sem mudar o documento (ou o contrário), quebra.
ALVO = {
    "tecator": {930, 1040},
    "gasoline": {1144, 1190, 1395, 1674},
    "mango": {910},
    "bioprocess": {1126, 1061, 1017, 910, 899},
}


def test_target_bands_are_the_documented_ones():
    for ds, esperado in ALVO.items():
        assert {b.position for b in BANDS[ds] if b.role == "alvo"} == esperado, ds


def test_every_band_has_a_source_and_a_known_role():
    for ds, bands in BANDS.items():
        for b in bands:
            assert b.sources and all(b.sources), (ds, b.position)
            assert b.role in ROLES and b.assignment


@pytest.fixture(scope="module", params=["tecator", "gasoline", "mango", "bioprocess"])
def dataset(request):
    return load(request.param)


def test_every_band_falls_inside_the_dataset_axis(dataset):
    lo, hi = float(dataset.axis.min()), float(dataset.axis.max())
    for b in BANDS[dataset.name if dataset.name in BANDS else _key(dataset)]:
        assert lo <= b.position <= hi, (dataset.name, b.position)


def _key(ds):
    return next(k for k in BANDS if k in ds.name.lower())


def test_windows_follow_the_half_width_and_the_roles():
    assert windows("tecator", 10) == [(920, 940), (1030, 1050)]
    assert windows("tecator", 10, roles=("alvo", "agua")) == [(920, 940), (1030, 1050), (960, 980)]
    assert windows("mango", 5, roles=("pigmento",)) == [(675, 685), (470, 480), (430, 440)]


@pytest.mark.parametrize("kw", [{"half_width": 0}, {"half_width": -5}])
def test_half_width_must_be_positive(kw):
    with pytest.raises(ValueError):
        windows("tecator", **kw)


def test_unknown_dataset_or_role_is_an_error():
    with pytest.raises(ValueError):
        windows("milho", 10)
    with pytest.raises(ValueError):
        windows("tecator", 10, roles=("gordura",))


def test_fraction_on_the_real_tecator_axis():
    # Eixo de 850 a 1048 nm em passos de 2. Com meia largura de 10 nm, as
    # bandas 920–940 e 1030–1050 nm: as de índice 35 (920 nm), 45 (940 nm)
    # e 95 (1040 nm) caem dentro; 0 (850 nm) e 60 (970 nm, água) não.
    axis = load("tecator").axis
    assert axis[35] == 920 and axis[45] == 940 and axis[95] == 1040 and axis[60] == 970
    w = windows("tecator", 10)
    assert fraction_in_windows({35, 45, 95, 0, 60}, axis, w) == pytest.approx(3 / 5)
    assert fraction_in_windows({60}, axis, windows("tecator", 10, roles=("agua",))) == 1.0


def test_bioprocess_windows_are_in_wavenumbers():
    axis = load("bioprocess").axis
    w = windows("bioprocess", 10)
    inside = [j for j in range(len(axis)) if any(lo <= axis[j] <= hi for lo, hi in w)]
    # a janela mais baixa é 899 ± 10 (889) e a mais alta, 1126 ± 10 (1136)
    assert inside and all(889 <= axis[j] <= 1136 for j in inside)
    assert np.isclose(min(abs(axis[j] - 1126) for j in inside), 0, atol=2.5)
