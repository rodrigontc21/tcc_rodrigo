"""Validação pontual contra o resultado publicado do paper de referência.

Fina camada sobre `tcc.validation.evaluate_against_literature` (ADR 005),
que implementa o protocolo da literatura: divisão fixa 172/43 do Tecator
(129 treino + 43 monitoramento contra os últimos 43 de teste, sequencial)
e Z-score de espectro e alvo ajustado só no treino. Este modo NUNCA entra
na grade principal nem na decomposição.

Protocolo do paper, para o PLS no Tecator:
  - 172 treino / 43 teste (80/20), divisão padrão do conjunto
  - H = 10 componentes latentes
  - Reportado: R² = 0,919 / RMSE = 0,296 (escala normalizada)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.validation import N_TRAIN_TECATOR, evaluate_against_literature

N_COMPONENTS = 10

PAPER_R2 = 0.919
PAPER_RMSE = 0.296


def main() -> None:
    dataset = load("tecator")

    print(f"Fonte local: {dataset.name} via scikit-fda (sha256 {dataset.sha256[:12]}...)")
    print(f"  X: {dataset.X.shape}  y: {dataset.y.shape}")
    print(f"  gordura: {dataset.y.min():.1f}% a {dataset.y.max():.1f}%")
    print()
    print(
        f"Divisão fixa: {N_TRAIN_TECATOR} treino / "
        f"{dataset.X.shape[0] - N_TRAIN_TECATOR} teste (sequencial)"
    )
    print(f"H = {N_COMPONENTS} componentes latentes, Z-score ajustado no treino")
    print()

    result = evaluate_against_literature(PLSArm(n_components=N_COMPONENTS), dataset)

    print(f"{'':>12} {'obtido':>9} {'paper':>9} {'Δ':>9}")
    print(f"{'R²':>12} {result.r2:>9.4f} {PAPER_R2:>9.4f} {result.r2 - PAPER_R2:>+9.4f}")
    print(
        f"{'RMSE (norm)':>12} {result.rmsep:>9.4f} {PAPER_RMSE:>9.4f} "
        f"{result.rmsep - PAPER_RMSE:>+9.4f}"
    )
    print()
    print(
        f"RMSE em unidades originais: {result.rmse_original:.4f} "
        f"pontos percentuais de gordura"
    )


if __name__ == "__main__":
    main()
