"""Validação pontual contra o resultado publicado do paper de referência.

NÃO usa a `evaluate()` do protocolo único, de propósito: este é o
"protocolo da literatura", que reproduz o desenho do artigo (divisão fixa,
H declarado) só para checar se a fonte de dados local é equivalente à
deles. Ele nunca entra na grade principal nem na decomposição.

TEMPORÁRIO: script autocontido. Deve migrar para `src/tcc/validation.py`
quando a tarefa D (segundo modo de protocolo) for implementada — ver
análise de 03/09 e o ADR que registrará a decisão.

Protocolo do paper, para o PLS no Tecator:
  - 172 treino / 43 teste (80/20)
  - H = 10 componentes latentes
  - Z-score ajustado só no treino (espectro e alvo)
  - Reportado: R² = 0,919 / RMSE = 0,296 (escala normalizada)

A divisão 172/43 não é aleatória: 172 = 129 + 43 é a divisão padrão do
Tecator (treino + monitoramento) contra os últimos 43 de teste, sequencial
na ordem original do conjunto.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tcc.data import load

N_TRAIN = 172
N_COMPONENTS = 10

PAPER_R2 = 0.919
PAPER_RMSE = 0.296


def main() -> None:
    dataset = load("tecator")
    X, y = dataset.X, dataset.y

    print(f"Fonte local: {dataset.name} via scikit-fda")
    print(f"  X: {X.shape}  y: {y.shape}")
    print(f"  eixo: {dataset.axis[0]:.0f}-{dataset.axis[-1]:.0f} {dataset.unit}")
    print(f"  gordura: {y.min():.1f}% a {y.max():.1f}%")
    print("  paper descreve a faixa como 7% a 76% (pergunta nº 5, em aberto)")
    print()

    # Divisão sequencial padrão do Tecator, não aleatória
    X_train, X_test = X[:N_TRAIN], X[N_TRAIN:]
    y_train, y_test = y[:N_TRAIN], y[N_TRAIN:]
    print(f"Divisão: {len(y_train)} treino / {len(y_test)} teste (sequencial)")

    # Z-score ajustado SÓ no treino, espectro e alvo
    x_mean, x_std = X_train.mean(axis=0), X_train.std(axis=0, ddof=0)
    y_mean, y_std = y_train.mean(), y_train.std(ddof=0)

    Xz_train = (X_train - x_mean) / x_std
    Xz_test = (X_test - x_mean) / x_std
    yz_train = (y_train - y_mean) / y_std
    yz_test = (y_test - y_mean) / y_std

    # scale=False: o z-score já foi aplicado acima, explicitamente
    model = PLSRegression(n_components=N_COMPONENTS, scale=False)
    model.fit(Xz_train, yz_train)
    yz_pred = np.asarray(model.predict(Xz_test)).ravel()

    r2 = float(r2_score(yz_test, yz_pred))
    rmse = float(np.sqrt(np.mean((yz_test - yz_pred) ** 2)))

    print(f"H = {N_COMPONENTS} componentes latentes, z-score ajustado no treino")
    print()
    print(f"{'':>12} {'obtido':>9} {'paper':>9} {'Δ':>9}")
    print(f"{'R²':>12} {r2:>9.4f} {PAPER_R2:>9.4f} {r2 - PAPER_R2:>+9.4f}")
    print(f"{'RMSE (norm)':>12} {rmse:>9.4f} {PAPER_RMSE:>9.4f} {rmse - PAPER_RMSE:>+9.4f}")
    print()

    # Referência em unidades originais, para leitura química
    rmse_original = rmse * y_std
    print(f"RMSE em unidades originais: {rmse_original:.4f} pontos percentuais de gordura")


if __name__ == "__main__":
    main()
