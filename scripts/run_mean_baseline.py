"""Linha de base trivial: MeanArm no Tecator, 10 seed_split.

Gera results/mean_baseline_tecator.csv (versionado, para envio à
orientação) com uma linha por execução de `evaluate`. O MeanArm ignora X
por completo, então estes números são o piso de referência: qualquer braço
de verdade tem que ficar bem acima deles.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

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


def main() -> None:
    tecator = load("tecator")

    rows = []
    for seed_split in range(10):
        result = evaluate(MeanArm(), tecator, seed_split=seed_split, seed_algo=0)
        rows.append(
            {
                "arm_name": result.arm_name,
                "dataset_name": result.dataset_name,
                "seed_split": result.seed_split,
                "seed_algo": result.seed_algo,
                # Casas fixas na gravação: round() puro deixaria o Excel
                # com 15+ decimais ou notação científica (2.7e-05) e
                # comeria zeros finais (-0.019 em vez de -0.0190)
                "r2": f"{result.r2:.4f}",
                "rmsep": f"{result.rmsep:.4f}",
                "rmse_cv": f"{result.rmse_cv:.4f}",
                "n_fits": result.n_fits,
                "wall_time": f"{result.wall_time:.6f}",
                "n_test": len(result.test_idx),
            }
        )

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)

    csv_path = out_dir / "mean_baseline_tecator.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Mesma tabela em Markdown: renderiza direto no GitHub, para leitura
    # sem depender da configuração regional do Excel
    md_path = out_dir / "mean_baseline_tecator.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Linha de base: MeanArm no Tecator\n\n")
        f.write("| " + " | ".join(COLUMNS) + " |\n")
        f.write("|" + "|".join("---" for _ in COLUMNS) + "|\n")
        for row in rows:
            f.write("| " + " | ".join(str(row[c]) for c in COLUMNS) + " |\n")

    header = (
        f"{'arm':>5} {'dataset':>8} {'split':>5} {'algo':>4} "
        f"{'r2':>9} {'rmsep':>8} {'rmse_cv':>8} {'n_fits':>6} "
        f"{'wall_time':>10} {'n_test':>6}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['arm_name']:>5} {row['dataset_name']:>8} "
            f"{row['seed_split']:>5} {row['seed_algo']:>4} "
            f"{row['r2']:>9} {row['rmsep']:>8} {row['rmse_cv']:>8} "
            f"{row['n_fits']:>6} {row['wall_time']:>10} {row['n_test']:>6}"
        )
    print(f"\nSalvo em {csv_path.relative_to(ROOT)} e {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
