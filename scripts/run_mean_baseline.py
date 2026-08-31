"""Linha de base trivial: MeanArm no Tecator, muitas seed_split.

Gera dois arquivos versionados em results/ (para envio à orientação):

- mean_baseline_tecator.csv  uma linha por execução de `evaluate`
- mean_baseline_tecator.md   estatísticas descritivas + tabela completa

O MeanArm ignora X por completo, então a dispersão do RMSEP entre partições
é o piso de ruído de partição do conjunto: variação que existe antes de
qualquer modelo entrar em cena.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tcc.arms.mean import MeanArm
from tcc.data import load
from tcc.protocol import evaluate

COLUMNS = [
    "arm_name",
    "dataset_name",
    "seed_split",
    "seed_algo",
    "r2",
    "rmsep",
    "rmse_cv",
    "n_fits",
    "wall_time",
    "n_test",
]

N_SAMPLE_ROWS = 10


def _format_row(result, n_test: int) -> dict:
    # Casas fixas na gravação: round() puro deixaria o Excel com 15+
    # decimais ou notação científica (2.7e-05) e comeria zeros finais
    return {
        "arm_name": result.arm_name,
        "dataset_name": result.dataset_name,
        "seed_split": result.seed_split,
        "seed_algo": result.seed_algo,
        "r2": f"{result.r2:.4f}",
        "rmsep": f"{result.rmsep:.4f}",
        "rmse_cv": f"{result.rmse_cv:.4f}",
        "n_fits": result.n_fits,
        "wall_time": f"{result.wall_time:.6f}",
        "n_test": n_test,
    }


def _describe(values: np.ndarray) -> dict[str, float]:
    return {
        "média": float(np.mean(values)),
        "desvio-padrão": float(np.std(values, ddof=1)),
        "mínimo": float(np.min(values)),
        "máximo": float(np.max(values)),
        "percentil 5": float(np.percentile(values, 5)),
        "percentil 95": float(np.percentile(values, 95)),
    }


def _stats_lines(n_seeds: int, r2: np.ndarray, rmsep: np.ndarray) -> list[str]:
    lines = [f"Estatísticas sobre {n_seeds} partições:", ""]
    lines.append(f"{'':>15} {'RMSEP':>9} {'R²':>9}")
    stats_rmsep = _describe(rmsep)
    stats_r2 = _describe(r2)
    for key in stats_rmsep:
        lines.append(f"{key:>15} {stats_rmsep[key]:>9.4f} {stats_r2[key]:>9.4f}")
    return lines


def _markdown_table(rows: list[dict]) -> list[str]:
    lines = ["| " + " | ".join(COLUMNS) + " |"]
    lines.append("|" + "|".join("---" for _ in COLUMNS) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(row[c]) for c in COLUMNS) + " |")
    return lines


def _markdown_stats(n_seeds: int, r2: np.ndarray, rmsep: np.ndarray) -> list[str]:
    stats_rmsep = _describe(rmsep)
    stats_r2 = _describe(r2)
    lines = [f"Estatísticas descritivas sobre {n_seeds} partições:", ""]
    lines.append("| estatística | RMSEP | R² |")
    lines.append("|---|---|---|")
    for key in stats_rmsep:
        lines.append(f"| {key} | {stats_rmsep[key]:.4f} | {stats_r2[key]:.4f} |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=100,
        help="número de seed_split (0 a N-1) a executar (padrão: 100)",
    )
    args = parser.parse_args()

    tecator = load("tecator")

    rows = []
    r2_values = []
    rmsep_values = []
    for seed_split in range(args.n_seeds):
        result = evaluate(MeanArm(), tecator, seed_split=seed_split, seed_algo=0)
        r2_values.append(result.r2)
        rmsep_values.append(result.rmsep)
        rows.append(_format_row(result, n_test=len(result.test_idx)))

    r2_arr = np.array(r2_values)
    rmsep_arr = np.array(rmsep_values)

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)

    csv_path = out_dir / "mean_baseline_tecator.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Mesma tabela em Markdown, com as estatísticas no topo: renderiza
    # direto no GitHub, para leitura sem depender do Excel
    md_path = out_dir / "mean_baseline_tecator.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Linha de base: MeanArm no Tecator\n\n")
        f.write("\n".join(_markdown_stats(args.n_seeds, r2_arr, rmsep_arr)))
        f.write(f"\n\n## Todas as partições ({len(rows)})\n\n")
        f.write("\n".join(_markdown_table(rows)))
        f.write("\n")

    # No terminal, só uma amostra: 100 linhas iguais não ajudam ninguém
    sample = rows[:N_SAMPLE_ROWS]
    header = (
        f"{'arm':>5} {'dataset':>8} {'split':>5} {'algo':>4} "
        f"{'r2':>9} {'rmsep':>8} {'rmse_cv':>8} {'n_fits':>6} "
        f"{'wall_time':>10} {'n_test':>6}"
    )
    print(header)
    print("-" * len(header))
    for row in sample:
        print(
            f"{row['arm_name']:>5} {row['dataset_name']:>8} "
            f"{row['seed_split']:>5} {row['seed_algo']:>4} "
            f"{row['r2']:>9} {row['rmsep']:>8} {row['rmse_cv']:>8} "
            f"{row['n_fits']:>6} {row['wall_time']:>10} {row['n_test']:>6}"
        )
    if len(rows) > len(sample):
        print(f"... ({len(rows) - len(sample)} linhas omitidas; completo no CSV)")

    print()
    print("\n".join(_stats_lines(args.n_seeds, r2_arr, rmsep_arr)))
    print(f"\nSalvo em {csv_path.relative_to(ROOT)} e {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
