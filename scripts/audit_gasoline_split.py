"""Auditoria da divisão de literatura do Gasoline (adendo ao ADR 010).

Roda o portão de validação exatamente como está em `validation.py` (PLS
com H = 5 fixo, Z-score de espectro e alvo ajustado só no treino) em N
divisões `train_test_split(test_size=0.2, random_state=s)`, s = 0..N-1
(padrão N = 2000), e situa a semente 42 na distribuição de R² e RMSE.

Além da posição da 42, mede a força do argumento de identificação: quantas
sementes reproduzem os valores publicados (com intervalo de Wilson), como
essa contagem varia com a tolerância, e quanto R² e RMSE são redundantes
entre si (correlação e contagens marginais).

Para não duplicar o pipeline nem alterar `validation.py`, a semente da
divisão é trocada pela global `tcc.validation.GASOLINE_SPLIT_SEED`, que
`_literature_split` lê a cada chamada; o valor original é restaurado no
fim. Só auditoria: nunca entra na grade principal.

Gera em results/:

- gasoline_split_audit.csv  uma linha por semente
- gasoline_split_audit.md   estatísticas, posição da 42, sensibilidade
- gasoline_split_audit.png  R² × RMSE, semente 42 destacada
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, percentileofscore, spearmanr

import tcc.validation as validation
from tcc.arms.pls import PLSArm
from tcc.data import load

N_COMPONENTS = 5
SEED_UNDER_AUDIT = 42

# pgsg_0, Seção 4.2 e Tabela 1 (escala normalizada)
PAPER_R2 = 0.975
PAPER_RMSE = 0.145
# Tolerância do teste de reprodução em tests/test_validation.py (5e-4 =
# meia unidade da 3ª casa publicada, ADR 010), e a faixa da análise de
# sensibilidade
TOLERANCE = 5e-4
TOLERANCES = (1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2)

PERCENTILES = (5, 25, 50, 75, 95)
# Sementes listadas por linha na tabela de sensibilidade
MAX_LISTED_SEEDS = 12


def _run(gasoline, seeds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    original_seed = validation.GASOLINE_SPLIT_SEED
    r2, rmse = [], []
    try:
        for seed in seeds:
            validation.GASOLINE_SPLIT_SEED = int(seed)
            result = validation.evaluate_against_literature(
                PLSArm(n_components=N_COMPONENTS), gasoline
            )
            r2.append(result.r2)
            rmse.append(result.rmsep)
    finally:
        validation.GASOLINE_SPLIT_SEED = original_seed
    return np.array(r2), np.array(rmse)


def _describe(values: np.ndarray) -> dict[str, float]:
    stats = {
        "média": float(np.mean(values)),
        "desvio-padrão": float(np.std(values, ddof=1)),
        "mínimo": float(np.min(values)),
        "máximo": float(np.max(values)),
    }
    for p in PERCENTILES:
        stats[f"percentil {p}"] = float(np.percentile(values, p))
    return stats


def _position(values: np.ndarray, value: float) -> dict[str, float]:
    """Percentil da semente auditada: fração das sementes com valor
    estritamente menor (strict), menor ou igual (weak), e a média dos dois
    (rank, com empates divididos)."""
    return {
        kind: float(percentileofscore(values, value, kind=kind))
        for kind in ("strict", "weak", "rank")
    }


def _wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Intervalo de Wilson de 95% para a proporção k/n."""
    p = k / n
    center = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return max(0.0, center - half), min(1.0, center + half)


def _pct(x: float) -> str:
    return f"{100 * x:.3f}%"


def _sensitivity(r2: np.ndarray, rmse: np.ndarray, seeds: np.ndarray) -> list[dict]:
    """Contagens por tolerância: só R², só RMSE, os dois. Se as duas
    métricas fossem confirmações independentes, a contagem conjunta seria
    ≈ o produto das marginais dividido por n; se forem redundantes, fica
    perto da menor das marginais."""
    n = len(seeds)
    rows = []
    for tol in TOLERANCES:
        hit_r2 = np.abs(r2 - PAPER_R2) <= tol
        hit_rmse = np.abs(rmse - PAPER_RMSE) <= tol
        both = hit_r2 & hit_rmse
        rows.append(
            {
                "tol": tol,
                "r2": int(hit_r2.sum()),
                "rmse": int(hit_rmse.sum()),
                "both": int(both.sum()),
                "expected_if_independent": float(hit_r2.sum() * hit_rmse.sum() / n),
                "seeds": seeds[both],
            }
        )
    return rows


def _plot(r2, rmse, i42, n, png_path: Path) -> None:
    fig, (ax_hist, ax_scatter) = plt.subplots(1, 2, figsize=(10, 4))
    ax_hist.hist(r2, bins=40, color="#8a8a8a")
    ax_hist.axvline(r2[i42], color="#d1495b", label=f"random_state=42 ({r2[i42]:.4f})")
    ax_hist.axvline(PAPER_R2, color="#1f5f8b", linestyle="--", label=f"paper ({PAPER_R2})")
    ax_hist.set_xlabel("R² no teste (escala normalizada)")
    ax_hist.set_ylabel("nº de sementes")
    ax_hist.legend(fontsize=8)
    ax_scatter.scatter(
        r2, rmse, s=6, color="#8a8a8a", alpha=0.6, label=f"random_state 0–{n - 1}"
    )
    ax_scatter.scatter(r2[i42], rmse[i42], s=60, color="#d1495b", label="random_state=42")
    ax_scatter.scatter(PAPER_R2, PAPER_RMSE, s=60, marker="x", color="#1f5f8b", label="paper")
    ax_scatter.set_xlabel("R² no teste")
    ax_scatter.set_ylabel("RMSE no teste (normalizado)")
    ax_scatter.legend(fontsize=8)
    fig.suptitle(
        f"Gasoline, PLS H={N_COMPONENTS}, train_test_split(test_size=0.2), {n} sementes"
    )
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=2000,
        help="número de random_state (0 a N-1) a varrer (padrão: 2000)",
    )
    args = parser.parse_args()

    gasoline = load("gasoline")
    seeds = np.arange(args.n_seeds)
    r2, rmse = _run(gasoline, seeds)
    n = len(seeds)
    i42 = int(np.flatnonzero(seeds == SEED_UNDER_AUDIT)[0])

    stats_r2, stats_rmse = _describe(r2), _describe(rmse)
    pos_r2, pos_rmse = _position(r2, r2[i42]), _position(rmse, rmse[i42])

    sensitivity = _sensitivity(r2, rmse, seeds)
    main_row = next(row for row in sensitivity if row["tol"] == TOLERANCE)
    k = main_row["both"]
    lo, hi = _wilson(k, n)
    # O paper reporta 3 casas: "reproduzir o número publicado" na precisão
    # dele é arredondar para o mesmo valor (meia unidade, ±5e-4)
    rounded = seeds[(np.round(r2, 3) == PAPER_R2) & (np.round(rmse, 3) == PAPER_RMSE)]
    lo_rounded, hi_rounded = _wilson(len(rounded), n)

    pearson = pearsonr(r2, rmse)
    spearman = spearmanr(r2, rmse)

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)

    csv_path = out_dir / "gasoline_split_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["random_state", "r2", "rmse"])
        for s, a, b in zip(seeds, r2, rmse):
            writer.writerow([s, f"{a:.6f}", f"{b:.6f}"])

    png_path = out_dir / "gasoline_split_audit.png"
    _plot(r2, rmse, i42, n, png_path)

    lines = [
        "# Auditoria da divisão de literatura do Gasoline",
        "",
        f"PLS H={N_COMPONENTS}, Z-score no treino, `train_test_split(test_size=0.2, "
        f"random_state=s)`, s = 0..{n - 1}. Gerado por "
        "`scripts/audit_gasoline_split.py`.",
        "",
        "| estatística | R² | RMSE |",
        "|---|---|---|",
    ]
    lines += [f"| {key} | {stats_r2[key]:.4f} | {stats_rmse[key]:.4f} |" for key in stats_r2]
    lines += [
        "",
        f"## random_state = {SEED_UNDER_AUDIT}",
        "",
        f"R² = {r2[i42]:.6f}, RMSE = {rmse[i42]:.6f} (paper: {PAPER_R2}, {PAPER_RMSE}).",
        "",
        "| percentil (scipy `percentileofscore`) | R² | RMSE |",
        "|---|---|---|",
    ]
    lines += [
        f"| {kind} | {pos_r2[kind]:.1f} | {pos_rmse[kind]:.1f} |"
        for kind in ("strict", "weak", "rank")
    ]
    lines += [
        "",
        "## Sementes que reproduzem o paper",
        "",
        f"Com tolerância {TOLERANCE:g} nas duas métricas: {k} de {n} "
        f"({', '.join(map(str, main_row['seeds']))}); proporção {_pct(k / n)}, "
        f"Wilson 95% [{_pct(lo)}, {_pct(hi)}].",
        f"Arredondando a 3 casas (precisão do paper): {len(rounded)} de {n} "
        f"({', '.join(map(str, rounded))}); proporção {_pct(len(rounded) / n)}, "
        f"Wilson 95% [{_pct(lo_rounded)}, {_pct(hi_rounded)}].",
        "",
        "| tolerância | batem R² | batem RMSE | batem os dois | Wilson 95% (os dois) "
        "| esperado se independentes | razão obs/esp | sementes (os dois) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in sensitivity:
        listed = [str(s) for s in row["seeds"][:MAX_LISTED_SEEDS]]
        if len(row["seeds"]) > MAX_LISTED_SEEDS:
            listed.append("…")
        row_lo, row_hi = _wilson(row["both"], n)
        expected = row["expected_if_independent"]
        ratio = f"{row['both'] / expected:.2f}" if expected > 0 else "—"
        lines.append(
            f"| {row['tol']:g} | {row['r2']} | {row['rmse']} | {row['both']} "
            f"| [{_pct(row_lo)}, {_pct(row_hi)}] | {expected:.4f} | {ratio} "
            f"| {', '.join(listed)} |"
        )
    lines += [
        "",
        "## Correlação entre R² e RMSE",
        "",
        f"Pearson r = {pearson.statistic:.4f} (p = {pearson.pvalue:.2g}); "
        f"Spearman ρ = {spearman.statistic:.4f}.",
        "",
        f"![R² × RMSE]({png_path.name})",
        "",
    ]
    summary_end = len(lines)
    lines += [
        f"## Todas as sementes ({n})",
        "",
        "| random_state | R² | RMSE |",
        "|---|---|---|",
    ]
    lines += [f"| {s} | {a:.4f} | {b:.4f} |" for s, a, b in zip(seeds, r2, rmse)]
    md_path = out_dir / "gasoline_split_audit.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:summary_end]))
    print(
        f"Salvo em {csv_path.relative_to(ROOT)}, {md_path.relative_to(ROOT)} "
        f"e {png_path.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
