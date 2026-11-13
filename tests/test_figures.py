"""Figuras do Estágio 8 (src/tcc/figures.py), com entradas sintéticas.

Não compara pixels: lê de volta o que foi desenhado (alturas e bases das
barras, faixa ±δ, escala, rótulos, ordem dos painéis) e confere com a
entrada. As figuras não calculam resultado, então o risco é desenhar errado
o que recebem: barra no lugar trocado, sinal com a cor errada, painel fora
de ordem.
"""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.patches import Polygon, Rectangle

from tcc import figures as F


@pytest.fixture(autouse=True)
def _fecha_figuras():
    yield
    plt.close("all")


def _cor(artista_ou_cor) -> str:
    c = artista_ou_cor if isinstance(artista_ou_cor, str) else artista_ou_cor.get_facecolor()
    return mcolors.to_hex(c)


def _barras(ax):
    """Barras de dados: Rectangle com largura e altura (sem o fundo do eixo)."""
    return [p for p in ax.patches if isinstance(p, Rectangle) and p.get_width() and p.get_height()
            and p is not ax.patch]


def _textos(ax):
    return [t.get_text() for t in ax.texts]


# ---------------------------------------------------------------- _num

@pytest.mark.parametrize(("v", "esperado"), [(23.4, "23"), (1234.0, "1.234"), (0.5, "0,5"),
                                             (0.214, "0,21"), (0.0213, "0,021"), (10.0, "10")])
def test_num_uses_brazilian_format(v, esperado):
    assert F._num(v) == esperado


# ---------------------------------------------------------------- 1. cascata

TERMOS = {"nao_lin": 0.004, "ponderacao": -0.003, "aprendizado": 0.002}


def test_waterfall_stacks_terms_cumulatively_from_a1():
    fig = F.waterfall(0.90, TERMOS)
    barras = sorted(_barras(fig.axes[0]), key=lambda p: p.get_x())
    assert len(barras) == 5
    a1, nl, pond, apr, b4 = barras
    assert a1.get_y() == 0 and a1.get_height() == pytest.approx(0.90)
    assert nl.get_y() == pytest.approx(0.90) and nl.get_height() == pytest.approx(0.004)
    assert pond.get_y() == pytest.approx(0.904) and pond.get_height() == pytest.approx(-0.003)
    assert apr.get_y() == pytest.approx(0.901) and apr.get_height() == pytest.approx(0.002)
    assert b4.get_y() == 0 and b4.get_height() == pytest.approx(0.903)


def test_waterfall_colors_by_sign_and_references_in_gray():
    fig = F.waterfall(0.90, TERMOS)
    cores = [_cor(p) for p in sorted(_barras(fig.axes[0]), key=lambda p: p.get_x())]
    assert cores == [F.CINZA, F.AZUL, F.LARANJA, F.AZUL, F.CINZA]


def test_waterfall_labels_each_term_with_sign():
    fig = F.waterfall(0.90, TERMOS)
    assert _textos(fig.axes[0]) == ["+0.0040", "-0.0030", "+0.0020"]


def test_waterfall_keeps_all_levels_inside_the_axis():
    fig = F.waterfall(0.90, {"nao_lin": 0.05, "ponderacao": -0.08, "aprendizado": 0.01})
    lo, hi = fig.axes[0].get_ylim()
    for nivel in (0.90, 0.95, 0.87, 0.88):
        assert lo < nivel < hi


def test_waterfall_label_offset_is_in_points_not_metric_units():
    # RMSE em escala de dezenas: deslocamento fixo em unidades da métrica
    # (0,002) colaria o rótulo na barra; em pontos, fica igual em qualquer escala.
    fig = F.waterfall(30.0, {"nao_lin": -2.0, "ponderacao": 1.0, "aprendizado": -0.5},
                      metric="RMSE")
    for t in fig.axes[0].texts:
        assert t.get_anncoords() == "offset points"


# ---------------------------------------------------------------- 2. equivalência

def _tost(mean, lo, hi, eq):
    return {"mean": mean, "ci_low": lo, "ci_high": hi, "equivalent": eq}


def _faixa_x(ax):
    """Extremos x da faixa ±δ (axvspan: Rectangle ou Polygon, conforme a versão)."""
    for p in ax.patches:
        if isinstance(p, Polygon):
            xs = p.get_xy()[:, 0]
            return min(xs), max(xs)
        if isinstance(p, Rectangle) and p.get_width() and p.get_x() < 0:
            return p.get_x(), p.get_x() + p.get_width()
    raise AssertionError("sem faixa ±δ")


def test_equivalence_forest_shades_exactly_plus_minus_delta():
    fig = F.equivalence_forest({"a": _tost(0.001, -0.002, 0.004, True)}, 0.01)
    assert _faixa_x(fig.axes[0]) == pytest.approx((-0.01, 0.01))


def test_equivalence_forest_draws_interval_and_mean_per_term_in_order():
    res = {"primeiro": _tost(0.001, -0.002, 0.004, True),
           "segundo": _tost(0.02, 0.012, 0.03, False)}
    fig = F.equivalence_forest(res, 0.01)
    ax = fig.axes[0]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["segundo", "primeiro"]
    linhas = [ln for ln in ax.lines if len(ln.get_xdata()) == 2 and _cor(ln.get_color()) == F.AZUL]
    por_y = {ln.get_ydata()[0]: tuple(ln.get_xdata()) for ln in linhas}
    assert por_y[1] == pytest.approx((-0.002, 0.004))   # primeiro, em cima
    assert por_y[0] == pytest.approx((0.012, 0.03))
    assert _textos(ax) == ["equivalente", "não equivalente"]


def test_equivalence_forest_fits_intervals_wider_than_delta():
    fig = F.equivalence_forest({"a": _tost(0.0, -0.05, 0.08, False)}, 0.01)
    lo, hi = fig.axes[0].get_xlim()
    assert lo < -0.05 and hi > 0.08


# ---------------------------------------------------------------- 3. desempenho × reprodutibilidade

def test_performance_vs_reproducibility_places_and_colors_each_arm():
    pts = {"ipls": (-0.001, 0.3), "cars": (0.001, 0.2), "gate_prior": (0.005, 0.8)}
    fig = F.performance_vs_reproducibility(pts, neural=["gate_prior"])
    ax = fig.axes[0]
    pontos = {(ln.get_xdata()[0], ln.get_ydata()[0]): _cor(ln.get_color())
              for ln in ax.lines if len(ln.get_xdata()) == 1}
    assert pontos == {(-0.001, 0.3): F.AZUL, (0.001, 0.2): F.AZUL, (0.005, 0.8): F.LARANJA}
    assert sorted(_textos(ax)) == ["cars", "gate_prior", "ipls"]
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["clássico", "rede"]


def test_performance_vs_reproducibility_puts_right_side_labels_to_the_left():
    pts = {"esq": (0.0, 0.5), "meio": (0.5, 0.5), "dir": (1.0, 0.5)}
    fig = F.performance_vs_reproducibility(pts, neural=[])
    ha = {t.get_text(): t.get_horizontalalignment() for t in fig.axes[0].texts}
    assert ha == {"esq": "left", "meio": "left", "dir": "right"}


# ---------------------------------------------------------------- 4. Jaccard nos dois eixos

def test_jaccard_two_axes_bars_match_values_in_both_panels():
    split = {"ipls": 0.3, "cars": 0.2, "gate": 0.8}
    algo = {"cars": 0.1, "gate": 0.4}
    fig = F.jaccard_two_axes(split, algo, deterministic=["ipls"])
    ax_s, ax_a = fig.axes
    # y = n − 1 − i: o primeiro nome fica em cima
    assert {p.get_y() + p.get_height() / 2: p.get_width() for p in _barras(ax_s)} == \
        pytest.approx({2: 0.3, 1: 0.2, 0: 0.8})
    assert {p.get_y() + p.get_height() / 2: p.get_width() for p in _barras(ax_a)} == \
        pytest.approx({1: 0.1, 0: 0.4})
    assert [t.get_text() for t in ax_s.get_yticklabels()] == ["gate", "cars", "ipls"]
    assert ax_s.get_xlim() == ax_a.get_xlim() == (0, 1.1)


def test_jaccard_two_axes_marks_deterministic_arm_without_bar():
    fig = F.jaccard_two_axes({"ipls": 0.3, "cars": 0.2}, {"cars": 0.1}, deterministic=["ipls"])
    ax_a = fig.axes[1]
    det = [t for t in ax_a.texts if t.get_text() == "determinístico"]
    assert len(det) == 1 and det[0].get_position()[1] == 1   # ipls, em cima
    assert "determinístico" not in _textos(fig.axes[0])


def test_jaccard_two_axes_chance_tick_only_where_bar_exists():
    fig = F.jaccard_two_axes({"ipls": 0.3, "cars": 0.2}, {"cars": 0.1},
                             {"ipls": 0.05, "cars": 0.04}, deterministic=["ipls"])
    ax_s, ax_a = fig.axes
    tracos = lambda ax: sorted(ln.get_xdata()[0] for ln in ax.lines)  # noqa: E731
    assert tracos(ax_s) == pytest.approx([0.04, 0.05])
    assert tracos(ax_a) == pytest.approx([0.04])


# ---------------------------------------------------------------- 5. bandas sobre o espectro

def test_bands_over_spectrum_marks_selected_positions_and_windows():
    eixo = np.linspace(850, 1050, 100)
    sels = {"a": {0, 10, 99}, "b": {50}}
    fig = F.bands_over_spectrum(eixo, np.sin(eixo / 50), sels, [(920, 940), (1030, 1050)])
    ax_esp, ax_sel = fig.axes
    marcas = {ln.get_ydata()[0]: list(ln.get_xdata()) for ln in ax_sel.lines}
    assert marcas[1] == pytest.approx(list(eixo[[0, 10, 99]]))   # "a", em cima
    assert marcas[0] == pytest.approx([eixo[50]])
    assert [t.get_text() for t in ax_sel.get_yticklabels()] == ["b", "a"]
    for ax in (ax_esp, ax_sel):
        assert len(ax.patches) >= 2   # uma faixa por janela
    assert np.allclose(ax_esp.lines[0].get_xdata(), eixo)
    assert "comprimento de onda (nm)" in ax_sel.get_xlabel()


def test_bands_over_spectrum_uses_wavenumber_label_for_cm():
    eixo = np.linspace(800, 1800, 50)
    fig = F.bands_over_spectrum(eixo, eixo, {"a": {1}}, [], unit="cm⁻¹")
    assert "número de onda (cm⁻¹)" in fig.axes[1].get_xlabel()


# ---------------------------------------------------------------- 6. custo

def test_cost_sorts_ascending_on_log_scale_without_minor_ticks():
    fig = F.cost({"ga": 12.0, "pls": 0.5, "rede": 0.17, "cars": 22.0})
    ax = fig.axes[0]
    assert ax.get_xscale() == "log"
    assert [t.get_text() for t in ax.get_yticklabels()] == ["rede", "pls", "ga", "cars"]
    assert [p.get_width() for p in sorted(_barras(ax), key=lambda p: p.get_y())] == \
        pytest.approx([0.17, 0.5, 12.0, 22.0])
    fig.canvas.draw()
    assert len(ax.xaxis.get_minorticklocs()) == 0
    assert _textos(ax) == ["0,17", "0,5", "12", "22"]


def test_cost_default_label_is_time():
    fig = F.cost({"a": 1.0})
    assert fig.axes[0].get_xlabel().startswith("tempo por execução")


# ---------------------------------------------------------------- 7. por regime

def test_decomposition_by_regime_orders_panels_by_sample_size():
    by = {"grande": {"nao_lin": 0.1, "ponderacao": 0.2, "aprendizado": -0.1},
          "pequeno": {"nao_lin": -0.3, "ponderacao": 0.0, "aprendizado": 0.4},
          "medio": {"nao_lin": 0.01, "ponderacao": 0.02, "aprendizado": 0.03}}
    n = {"grande": 400, "pequeno": 60, "medio": 200}
    fig = F.decomposition_by_regime(by, n)
    assert [ax.get_title() for ax in fig.axes] == ["pequeno\nn = 60", "medio\nn = 200",
                                                   "grande\nn = 400"]
    # painel 0 = "pequeno"; a barra de altura 0 existe mas não tem área
    alturas_p = [p.get_height() for p in sorted(fig.axes[0].patches, key=lambda p: p.get_x())]
    assert alturas_p == pytest.approx([-0.3, 0.0, 0.4])
    alturas = [p.get_height() for p in sorted(fig.axes[2].patches, key=lambda p: p.get_x())]
    assert alturas == pytest.approx([0.1, 0.2, -0.1])
    cores = [_cor(p) for p in sorted(fig.axes[2].patches, key=lambda p: p.get_x())]
    assert cores == [F.AZUL, F.AZUL, F.LARANJA]


def test_decomposition_by_regime_title_does_not_overlap_panel_titles():
    fig = F.decomposition_by_regime({"a": dict.fromkeys(("nao_lin", "ponderacao", "aprendizado"), 0.1)},
                                    {"a": 10}, title="título")
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    sup = fig._suptitle.get_window_extent(r)
    painel = fig.axes[0].title.get_window_extent(r)
    assert sup.y0 >= painel.y1
