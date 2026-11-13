"""Figuras (Estágio 8 do pipeline; ADR 022).

Cada função recebe dados já calculados (pelas métricas e pela decomposição)
e devolve uma `matplotlib.figure.Figure`; nada aqui calcula resultado.
Figuras estáticas, para o texto impresso.

As sete do pipeline:
1. `waterfall`: a cascata da decomposição, de A1 até B4;
2. `equivalence_forest`: o intervalo de confiança de cada termo ao lado da
   margem ±δ;
3. `performance_vs_reproducibility`: um ponto por braço;
4. `jaccard_two_axes`: o Jaccard nos dois eixos de semente, lado a lado;
5. `bands_over_spectrum`: as bandas de cada método sobre o espectro médio e
   as janelas químicas;
6. `cost`: custo por braço, em escala log;
7. `decomposition_by_regime`: a decomposição por conjunto, em ordem de n.

Cores: azul e laranja da paleta de referência (validadas juntas para
daltonismo), cinza para o que é referência; texto sempre em tinta neutra.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

AZUL, LARANJA = "#2a78d6", "#eb6834"
CINZA, CINZA_CLARO, TINTA, TINTA_2 = "#8a8985", "#e4e3df", "#0b0b0b", "#52514e"
SUPERFICIE = "#fcfcfb"

TERMOS = (("nao_lin", "não-linearidade\nB1 − A1"), ("ponderacao", "ponderação\nB2 − B1"),
          ("aprendizado", "aprendizado\nB4 − B2"))


def _base(ax):
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(CINZA)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(axis="y", color=CINZA_CLARO, linewidth=0.8)
    ax.set_axisbelow(True)


def _num(v: float) -> str:
    """Número em formato brasileiro: 23, 1.200, 0,5, 0,021."""
    if v >= 10:
        return f"{v:,.0f}".replace(",", ".")
    return f"{v:.2g}".replace(".", ",")


def _fig(w=7.0, h=4.0, ncols=1, sharey=False):
    fig, axes = plt.subplots(1, ncols, figsize=(w, h), sharey=sharey, squeeze=False)
    fig.patch.set_facecolor(SUPERFICIE)
    for ax in axes[0]:
        _base(ax)
    return fig, list(axes[0])


def waterfall(a1: float, terms: dict[str, float], *, metric: str = "R²", title: str = ""):
    """Cascata: A1, depois cada termo aditivo empilhado, até B4 = A1 + soma.

    `terms` traz as **médias** de "nao_lin", "ponderacao" e "aprendizado",
    e `a1` a média do A1. Mediana não serve: não é aditiva, e a barra do B4
    (A1 + soma) deixaria de ser o B4 (no piloto do Tecator, 0,97088 contra
    0,97305 de mediana real). Aumento em azul, queda em laranja; A1 e B4 em
    cinza.
    """
    fig, (ax,) = _fig()
    nivel = a1
    rotulos = ["A1\n(PLS)"]
    ax.bar(0, a1, color=CINZA, width=0.6)
    for i, (chave, rot) in enumerate(TERMOS, start=1):
        d = terms[chave]
        ax.bar(i, d, bottom=nivel, color=AZUL if d >= 0 else LARANJA, width=0.6,
               edgecolor=SUPERFICIE, linewidth=2)
        # deslocamento em pontos, não em unidades da métrica: serve para R² e RMSE
        ax.annotate(f"{d:+.4f}", (i, nivel + d), xytext=(0, 3 if d >= 0 else -3),
                    textcoords="offset points", ha="center",
                    va="bottom" if d >= 0 else "top", fontsize=9, color=TINTA)
        nivel += d
        rotulos.append(rot)
    ax.bar(len(TERMOS) + 1, nivel, color=CINZA, width=0.6)
    rotulos.append("B4\n(porta)")
    ax.set_xticks(range(len(rotulos)), rotulos)
    vals = [a1, nivel] + [a1 + sum(terms[k] for k, _ in TERMOS[:j]) for j in range(4)]
    lo, hi = min(vals), max(vals)
    pad = max(0.01, (hi - lo) * 0.6)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_ylabel(metric, color=TINTA_2)
    ax.set_title(title or f"Decomposição de B4 − A1 ({metric})", color=TINTA, fontsize=11, loc="left")
    return fig


def equivalence_forest(results: dict[str, dict], delta: float, *, metric: str = "R²",
                       title: str = ""):
    """Um intervalo por termo contra a faixa ±δ.

    `results` mapeia o nome do termo para a saída de `tcc.decomposition.tost`
    (usa "mean", "ci_low", "ci_high" e "equivalent").
    """
    nomes = list(results)
    fig, (ax,) = _fig(h=0.6 * len(nomes) + 1.6)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=CINZA_CLARO, linewidth=0.8)
    ax.axvspan(-delta, delta, color=CINZA_CLARO, zorder=0)
    ax.axvline(0, color=CINZA, linewidth=1)
    for i, nome in enumerate(nomes):
        r = results[nome]
        y = len(nomes) - 1 - i
        ax.plot([r["ci_low"], r["ci_high"]], [y, y], color=AZUL, linewidth=2, solid_capstyle="round")
        ax.plot(r["mean"], y, "o", color=AZUL, markersize=8, markeredgecolor=SUPERFICIE,
                markeredgewidth=2)
        ax.text(max(r["ci_high"], delta) + delta * 0.08, y,
                "equivalente" if r["equivalent"] else "não equivalente",
                va="center", fontsize=9, color=TINTA)
    ax.set_yticks(range(len(nomes)), list(reversed(nomes)))
    lim = max(delta, *(max(abs(r["ci_low"]), abs(r["ci_high"])) for r in results.values()))
    ax.set_xlim(-lim * 1.3, lim * 2.0)
    ax.set_xlabel(f"diferença pareada em {metric}  (faixa cinza: ±δ = ±{delta:g})", color=TINTA_2)
    ax.set_title(title or "Intervalos de confiança × margem de equivalência", color=TINTA,
                 fontsize=11, loc="left")
    return fig


def performance_vs_reproducibility(points: dict[str, tuple[float, float]], *, neural: Sequence[str],
                                   performance_label: str = "ΔR² mediano contra o PLS",
                                   title: str = ""):
    """Um ponto por braço: desempenho no eixo x, Jaccard no eixo y.

    Clássicos em azul, de rede em laranja, todos com o nome escrito ao lado.
    """
    fig, (ax,) = _fig(h=4.5)
    ax.grid(axis="x", color=CINZA_CLARO, linewidth=0.8)
    xs = [x for x, _ in points.values()]
    corte = min(xs) + 0.65 * (max(xs) - min(xs)) if len(xs) > 1 else float("inf")
    for nome, (x, y) in points.items():
        cor = LARANJA if nome in neural else AZUL
        ax.plot(x, y, "o", color=cor, markersize=9, markeredgecolor=SUPERFICIE, markeredgewidth=2)
        # rótulo à esquerda nos pontos da direita, para não cruzar os vizinhos
        esq = x > corte
        ax.annotate(nome, (x, y), xytext=(-7 if esq else 7, 5), textcoords="offset points",
                    fontsize=8, color=TINTA, ha="right" if esq else "left")
    ax.axvline(0, color=CINZA, linewidth=1)
    ax.set_xlabel(performance_label, color=TINTA_2)
    ax.set_ylabel("Jaccard médio entre partições", color=TINTA_2)
    ax.set_ylim(0, 1.05)
    ax.plot([], [], "o", color=AZUL, label="clássico")
    ax.plot([], [], "o", color=LARANJA, label="rede")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(title or "Desempenho × reprodutibilidade", color=TINTA, fontsize=11, loc="left")
    return fig


def jaccard_two_axes(by_split: dict[str, float], by_algo: dict[str, float],
                     chance: dict[str, float] | None = None, *, deterministic: Sequence[str] = (),
                     title: str = ""):
    """O Jaccard por braço nos dois eixos de semente, lado a lado, mesma escala.

    Braço determinístico no eixo `seed_algo` não tem barra: leva o rótulo
    "determinístico". `chance`, se dado, marca o Jaccard do acaso.
    """
    nomes = list(by_split)
    fig, axes = _fig(w=8.0, h=0.45 * len(nomes) + 1.6, ncols=2, sharey=True)
    for ax, dados, eixo in ((axes[0], by_split, "entre partições (seed_split)"),
                            (axes[1], by_algo, "entre sementes do algoritmo (seed_algo)")):
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=CINZA_CLARO, linewidth=0.8)
        for i, nome in enumerate(nomes):
            y = len(nomes) - 1 - i
            if nome in dados:
                ax.barh(y, dados[nome], color=AZUL, height=0.6, edgecolor=SUPERFICIE, linewidth=2)
                ax.text(dados[nome] + 0.02, y, f"{dados[nome]:.2f}", va="center", fontsize=8,
                        color=TINTA)
            elif nome in deterministic:
                ax.text(0.02, y, "determinístico", va="center", fontsize=8, color=TINTA_2,
                        style="italic")
            if chance and nome in chance and nome in dados:
                ax.plot([chance[nome]] * 2, [y - 0.35, y + 0.35], color=TINTA, linewidth=1.5)
        ax.set_xlim(0, 1.1)
        ax.set_xlabel(f"Jaccard {eixo}", color=TINTA_2)
    axes[0].set_yticks(range(len(nomes)), list(reversed(nomes)))
    fig.suptitle(title or "Reprodutibilidade da seleção nos dois eixos de semente"
                 + ("  (traço: acaso)" if chance else ""), color=TINTA, fontsize=11, x=0.02,
                 ha="left")
    return fig


def bands_over_spectrum(axis: np.ndarray, mean_spectrum: np.ndarray,
                        selections: dict[str, set[int]], windows: Sequence[tuple[float, float]],
                        *, unit: str = "nm", title: str = ""):
    """O espectro médio em cima; embaixo, uma faixa por método com as bandas
    escolhidas; as janelas químicas sombreadas nos dois painéis."""
    n = len(selections)
    fig, axes = plt.subplots(2, 1, figsize=(8.0, 3.0 + 0.35 * n), sharex=True,
                             gridspec_kw={"height_ratios": [2.2, 0.35 * n + 0.4]})
    fig.patch.set_facecolor(SUPERFICIE)
    for ax in axes:
        _base(ax)
        for lo, hi in windows:
            ax.axvspan(lo, hi, color=CINZA_CLARO, zorder=0)
    axes[0].plot(axis, mean_spectrum, color=TINTA, linewidth=1.5)
    axes[0].set_ylabel("espectro médio", color=TINTA_2)
    axes[1].grid(axis="y", visible=False)
    for i, (nome, sel) in enumerate(selections.items()):
        y = n - 1 - i
        xs = axis[sorted(sel)]
        axes[1].plot(xs, [y] * len(xs), "|", color=AZUL, markersize=9, markeredgewidth=2)
    axes[1].set_yticks(range(n), list(reversed(list(selections))))
    axes[1].set_ylim(-0.7, n - 0.3)
    axes[1].set_xlabel(f"{'número de onda' if unit != 'nm' else 'comprimento de onda'} ({unit})",
                       color=TINTA_2)
    axes[0].set_title(title or "Bandas selecionadas e janelas químicas (faixas cinza)",
                      color=TINTA, fontsize=11, loc="left")
    return fig


def cost(costs: dict[str, float], *, label: str = "tempo por execução (s, mediana)", title: str = ""):
    """Custo por braço, barras horizontais em escala log, do menor ao maior.

    O padrão é o tempo: o `n_fits` de rede (1 por treino) não é comparável com
    o dos braços clássicos (ADR 017), então misturar os dois engana.
    """
    itens = sorted(costs.items(), key=lambda kv: kv[1])
    fig, (ax,) = _fig(h=0.45 * len(itens) + 1.4)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=CINZA_CLARO, linewidth=0.8, which="major")
    for y, (nome, v) in enumerate(itens):
        ax.barh(y, v, color=AZUL, height=0.6, edgecolor=SUPERFICIE, linewidth=2)
        ax.text(v * 1.15, y, _num(v), va="center", fontsize=8, color=TINTA)
    ax.set_xscale("log")
    # depois do set_xscale: a escala log recoloca os traços menores
    ax.minorticks_off()
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: _num(v)))
    ax.set_yticks(range(len(itens)), [k for k, _ in itens])
    ax.set_xlabel(f"{label}, escala log", color=TINTA_2)
    ax.set_title(title or "Custo computacional por braço", color=TINTA, fontsize=11, loc="left")
    return fig


def decomposition_by_regime(by_dataset: dict[str, dict[str, float]], n_samples: dict[str, int],
                            *, metric: str = "R²", title: str = ""):
    """Os três termos aditivos por conjunto (médias, como na cascata), os
    conjuntos em ordem de n."""
    conjuntos = sorted(by_dataset, key=lambda d: n_samples[d])
    fig, axes = _fig(w=2.4 * len(conjuntos) + 1, h=3.6, ncols=len(conjuntos), sharey=True)
    for ax, ds in zip(axes, conjuntos):
        vals = [by_dataset[ds][k] for k, _ in TERMOS]
        ax.bar(range(3), vals, color=[AZUL if v >= 0 else LARANJA for v in vals], width=0.6,
               edgecolor=SUPERFICIE, linewidth=2)
        ax.axhline(0, color=CINZA, linewidth=1)
        ax.set_xticks(range(3), ["não-lin.", "ponder.", "aprend."], fontsize=8)
        ax.set_title(f"{ds}\nn = {n_samples[ds]}", color=TINTA, fontsize=10)
    axes[0].set_ylabel(f"termo ({metric})", color=TINTA_2)
    fig.suptitle(title or "Decomposição por regime amostral", color=TINTA, fontsize=11, x=0.02,
                 ha="left", y=1.0)
    fig.subplots_adjust(top=0.78)
    return fig
