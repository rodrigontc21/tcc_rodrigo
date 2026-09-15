"""Experimento do Estágio 1: SNV vs. derivada vs. SNV→derivada no Tecator.

Executa a decisão registrada no PROTOCOLO.md (reunião de 01/09): comparar
os três candidatos empiricamente e escolher com evidência. Avaliador é o
PLSArm com busca de componentes por CV interna, sob o protocolo único
(evaluate), em 30 seed_split com seed_algo fixo — PLS é determinístico,
então variar seed_algo não acrescentaria nada.

Gera dois arquivos versionados em results/ (para envio à orientação):

- preprocessing_comparison_tecator.csv  uma linha por execução
- preprocessing_comparison_tecator.md   comparativo + tabela completa
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.preprocessing import DerivativePreprocessor, SNVPreprocessor, snv_derivative
from tcc.protocol import evaluate

PREPROCESSORS = {
    "snv": SNVPreprocessor,
    "derivative": DerivativePreprocessor,
    "snv_derivative": snv_derivative,
}

COLUMNS = [
    "preprocessor",
    "arm_name",
    "dataset_name",
    "seed_split",
    "seed_algo",
    "r2",
    "rmsep",
    "rmse_cv",
    "n_components",
    "n_fits",
    "wall_time",
    "n_test",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=30,
        help="número de seed_split (0 a N-1) a executar (padrão: 30)",
    )
    args = parser.parse_args()

    tecator = load("tecator")

    rows = []
    metrics: dict[str, dict[str, list[float]]] = {
        name: {"r2": [], "rmsep": []} for name in PREPROCESSORS
    }
    for name, make in PREPROCESSORS.items():
        for seed_split in range(args.n_seeds):
            result = evaluate(
                PLSArm(),
                tecator,
                seed_split=seed_split,
                seed_algo=0,
                preprocessor=make(),
            )
            metrics[name]["r2"].append(result.r2)
            metrics[name]["rmsep"].append(result.rmsep)
            rows.append(
                {
                    "preprocessor": name,
                    "arm_name": result.arm_name,
                    "dataset_name": result.dataset_name,
                    "seed_split": result.seed_split,
                    "seed_algo": result.seed_algo,
                    "r2": f"{result.r2:.4f}",
                    "rmsep": f"{result.rmsep:.4f}",
                    "rmse_cv": f"{result.rmse_cv:.4f}",
                    "n_components": result.hyperparams["n_components"],
                    "n_fits": result.n_fits,
                    "wall_time": f"{result.wall_time:.6f}",
                    "n_test": len(result.test_idx),
                }
            )

    summary_lines = [
        f"{'pré-processador':>16} {'R² média':>9} {'R² dp':>8} "
        f"{'RMSEP média':>12} {'RMSEP dp':>9}"
    ]
    md_summary = [
        "| pré-processador | R² média | R² dp | RMSEP média | RMSEP dp |",
        "|---|---|---|---|---|",
    ]
    for name in PREPROCESSORS:
        r2 = np.array(metrics[name]["r2"])
        rmsep = np.array(metrics[name]["rmsep"])
        summary_lines.append(
            f"{name:>16} {r2.mean():>9.4f} {r2.std(ddof=1):>8.4f} "
            f"{rmsep.mean():>12.4f} {rmsep.std(ddof=1):>9.4f}"
        )
        md_summary.append(
            f"| {name} | {r2.mean():.4f} | {r2.std(ddof=1):.4f} "
            f"| {rmsep.mean():.4f} | {rmsep.std(ddof=1):.4f} |"
        )

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)

    csv_path = out_dir / "preprocessing_comparison_tecator.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    md_path = out_dir / "preprocessing_comparison_tecator.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Comparação de pré-processamento: PLS no Tecator\n\n")
        f.write(
            f"PLSArm com busca de componentes por CV interna, "
            f"{args.n_seeds} `seed_split`, `seed_algo=0`.\n\n"
        )
        f.write("\n".join(md_summary))
        f.write(f"\n\n## Todas as execuções ({len(rows)})\n\n")
        f.write("| " + " | ".join(COLUMNS) + " |\n")
        f.write("|" + "|".join("---" for _ in COLUMNS) + "|\n")
        for row in rows:
            f.write("| " + " | ".join(str(row[c]) for c in COLUMNS) + " |\n")

    print(f"PLSArm (busca por CV) x {args.n_seeds} seed_split, seed_algo=0\n")
    print("\n".join(summary_lines))
    print(f"\nSalvo em {csv_path.relative_to(ROOT)} e {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
