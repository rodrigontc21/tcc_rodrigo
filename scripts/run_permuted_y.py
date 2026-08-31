"""Sonda de vazamento: PermutedYArm(MeanArm) no Tecator, muitas seed_split.

Com o alvo embaralhado no treino, não existe relação X→y a aprender:
R² apreciavelmente acima de zero denunciaria vazamento no caminho de X
(pré-processamento, seleção de variáveis). Complementa o baseline da
média, que valida o lado do y mas nunca toca em X.

Gera dois arquivos versionados em results/ (para envio à orientação):

- permuted_y_tecator.csv  uma linha por execução de `evaluate`
- permuted_y_tecator.md   estatísticas descritivas + tabela completa
"""

from __future__ import annotations

import argparse
import csv

import numpy as np

# Reaproveita o molde do baseline da média (mesmo diretório): colunas,
# formatação de linha, estatísticas e tabelas Markdown idênticas
from run_mean_baseline import (
    COLUMNS,
    N_SAMPLE_ROWS,
    ROOT,
    _format_row,
    _markdown_stats,
    _markdown_table,
    _stats_lines,
)

from tcc.arms.mean import MeanArm
from tcc.arms.permuted import PermutedYArm
from tcc.data import load
from tcc.protocol import evaluate


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
        result = evaluate(
            PermutedYArm(MeanArm()), tecator, seed_split=seed_split, seed_algo=0
        )
        r2_values.append(result.r2)
        rmsep_values.append(result.rmsep)
        rows.append(_format_row(result, n_test=len(result.test_idx)))

    r2_arr = np.array(r2_values)
    rmsep_arr = np.array(rmsep_values)

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)

    csv_path = out_dir / "permuted_y_tecator.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    md_path = out_dir / "permuted_y_tecator.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Sonda de vazamento: y permutado no Tecator\n\n")
        f.write("\n".join(_markdown_stats(args.n_seeds, r2_arr, rmsep_arr)))
        f.write(f"\n\n## Todas as partições ({len(rows)})\n\n")
        f.write("\n".join(_markdown_table(rows)))
        f.write("\n")

    sample = rows[:N_SAMPLE_ROWS]
    header = (
        f"{'arm':>17} {'dataset':>8} {'split':>5} {'algo':>4} "
        f"{'r2':>9} {'rmsep':>8} {'rmse_cv':>8} {'n_fits':>6} "
        f"{'wall_time':>10} {'n_test':>6}"
    )
    print(header)
    print("-" * len(header))
    for row in sample:
        print(
            f"{row['arm_name']:>17} {row['dataset_name']:>8} "
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
