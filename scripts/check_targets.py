"""TEMPORÁRIO — diagnóstico da ordem das colunas de alvo do Tecator.

Descartar depois de resolvida a pergunta nº 5. Motivo: a documentação do
`fda.usc` descreve os alvos como "Fat, Water and Protein"; a do `caret`,
para o mesmo conjunto, como "water, fat and protein". Ordem divergente é
ambiguidade suficiente para verificar empiricamente antes de investigar a
divergência de faixa em outras fontes.

Carrega direto de `skfda`, sem passar por `tcc.data.load()`, para o
diagnóstico não herdar a suposição que está sendo testada.
"""

from __future__ import annotations

import numpy as np
import skfda.datasets

N_HEAD = 10


def main() -> None:
    curves, targets = skfda.datasets.fetch_tecator(return_X_y=True)
    targets = np.asarray(targets, dtype=float)

    print(f"targets: shape={targets.shape}, dtype={targets.dtype}")
    print()

    print("=== 1) Estatísticas por coluna (identificadas por índice) ===")
    print(f"{'coluna':>8} {'min':>8} {'max':>8} {'média':>8} {'desvio':>8}")
    for j in range(targets.shape[1]):
        col = targets[:, j]
        print(
            f"{j:>8} {col.min():>8.2f} {col.max():>8.2f} "
            f"{col.mean():>8.2f} {col.std(ddof=1):>8.2f}"
        )
    print()

    print("=== 2) Soma das três colunas ===")
    row_sums = targets.sum(axis=1)
    print(f"primeiras {N_HEAD} amostras:")
    for i in range(N_HEAD):
        parts = "  ".join(f"{targets[i, j]:>6.2f}" for j in range(targets.shape[1]))
        print(f"  amostra {i:>3}: {parts}   soma = {row_sums[i]:>7.2f}")
    print(
        f"\nmédia da soma sobre as {len(row_sums)} amostras: {row_sums.mean():.2f} "
        f"(desvio {row_sums.std(ddof=1):.2f}, min {row_sums.min():.2f}, "
        f"max {row_sums.max():.2f})"
    )
    print("esperado ~100 se as três forem percentuais de fat/water/protein")
    print()

    print("=== 3) Correlação par a par ===")
    corr = np.corrcoef(targets, rowvar=False)
    header = "        " + " ".join(f"{j:>8}" for j in range(targets.shape[1]))
    print(header)
    for i in range(targets.shape[1]):
        row = " ".join(f"{corr[i, j]:>8.4f}" for j in range(targets.shape[1]))
        print(f"{i:>8} {row}")
    print("em carne, gordura e água são fortemente anticorrelacionadas")
    print()

    print("=== 4) Nomes das colunas via as_frame=True (evidência definitiva) ===")
    try:
        X_df, y_df = skfda.datasets.fetch_tecator(return_X_y=True, as_frame=True)
        print(f"tipo do alvo: {type(y_df).__name__}")
        columns = getattr(y_df, "columns", None)
        if columns is not None:
            print(f"colunas do alvo: {list(columns)}")
        else:
            print(f"nome do alvo: {getattr(y_df, 'name', '(sem nome)')}")
        print()
        print(y_df.head(N_HEAD))
    except Exception as exc:  # diagnóstico não deve morrer por causa da API
        print(f"as_frame=True falhou: {type(exc).__name__}: {exc}")
        print("tentando pelo bunch completo...")
        bunch = skfda.datasets.fetch_tecator(as_frame=True)
        target = getattr(bunch, "target", None)
        print(f"target: {type(target).__name__}")
        columns = getattr(target, "columns", None)
        print(f"colunas: {list(columns) if columns is not None else '(n/d)'}")
        print(f"feature_names: {getattr(bunch, 'target_names', '(n/d)')}")


if __name__ == "__main__":
    main()
