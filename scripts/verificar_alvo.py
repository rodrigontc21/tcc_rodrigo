"""Verificacao do alvo do Tecator no codigo do pgsg.

Tres checagens independentes:
  1. o conteudo das colunas do targets.csv bate com os rotulos?
  2. qual coluna o codigo do artigo seleciona?
  3. qual coluna reproduz os numeros publicados?
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

PGSG = Path.home() / "tcc/docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
RAW = PGSG / "data/raw/tecator"

print("=" * 72)
print(" 1. O CONTEUDO DAS COLUNAS BATE COM OS ROTULOS?")
print("=" * 72)

alvos = pd.read_csv(RAW / "targets.csv")
CANONICO = {  # ADR 004: conferido em Python e em R, e pela orientacao em 03/09
    "gordura": (0.9, 49.1),
    "agua": (39.3, 76.6),
    "proteina": (11.0, 21.8),
}

print(f"\n  arquivo: {RAW / 'targets.csv'}")
print(f"\n  {'rotulo':>10} {'min':>8} {'max':>8} {'media':>8}   {'= de fato':>10}")
for col in alvos.columns:
    v = alvos[col].values
    real = next(
        (nome for nome, (lo, hi) in CANONICO.items()
         if abs(v.min() - lo) < 0.1 and abs(v.max() - hi) < 0.1),
        "?",
    )
    print(f"  {col:>10} {v.min():>8.2f} {v.max():>8.2f} {v.mean():>8.2f}   {real:>10}")

print("\n  faixas canonicas do Tecator:")
for nome, (lo, hi) in CANONICO.items():
    print(f"    {nome:>10}: {lo} a {hi}")

print()
print("=" * 72)
print(" 2. QUAL COLUNA O CODIGO DO ARTIGO SELECIONA?")
print("=" * 72)
print()
for arquivo in ("scripts/baseline_pls.py", "revision_r1/one_se_analysis.py"):
    caminho = PGSG / arquivo
    if not caminho.exists():
        continue
    print(f"  {arquivo}:")
    for n, linha in enumerate(caminho.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if "[:, 0]" in linha or "[:,0]" in linha:
            print(f"    linha {n:>3}: {linha.strip()}")
    print()

print("=" * 72)
print(" 3. QUAL COLUNA REPRODUZ OS NUMEROS PUBLICADOS?")
print("=" * 72)

X = pd.read_csv(RAW / "spectra.csv").values
y = alvos.values

# protocolo do artigo, lido de src/data/preprocessing*.py
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
sx, sy = StandardScaler(), StandardScaler()
Xtr, Xte = sx.fit_transform(Xtr), sx.transform(Xte)
ytr, yte = sy.fit_transform(ytr), sy.transform(yte)

print(f"\n  protocolo: train_test_split(test_size=0.2, random_state=42)")
print(f"             Z-score de X e y ajustado no treino, PLS com H=10")
print(f"             treino {len(Xtr)} / teste {len(Xte)}")
print(f"\n  PUBLICADO NO ARTIGO:  R2 = 0.919   RMSE = 0.296")
print(f"\n  {'coluna':>8} {'rotulo':>10} {'conteudo':>10} {'R2':>9} {'RMSE':>9}")
for i, col in enumerate(alvos.columns):
    v = alvos[col].values
    real = next(
        (nome for nome, (lo, hi) in CANONICO.items()
         if abs(v.min() - lo) < 0.1 and abs(v.max() - hi) < 0.1),
        "?",
    )
    pls = PLSRegression(n_components=10).fit(Xtr, ytr[:, i])
    pred = np.asarray(pls.predict(Xte)).ravel()
    r2 = r2_score(yte[:, i], pred)
    rmse = float(np.sqrt(np.mean((yte[:, i] - pred) ** 2)))
    bate = "  <== BATE" if abs(r2 - 0.919) < 0.002 and abs(rmse - 0.296) < 0.002 else ""
    print(f"  {i:>8} {col:>10} {real:>10} {r2:>9.4f} {rmse:>9.4f}{bate}")

print()
print("=" * 72)
print(" 4. O ARQUIVO DA REVISAO QUE GEROU OS NUMEROS DA SECAO 4.2")
print("=" * 72)
saida = PGSG / "revision_r1/one_se_output.txt"
if saida.exists():
    linhas = saida.read_text(encoding="utf-8", errors="replace").splitlines()
    for linha in linhas[:40]:
        if any(p in linha for p in ("H_min", "RMSECV(H_min)", "SE(H_min)",
                                    "H*  (one-SE", "H = 10 (paper)", "TECATOR")):
            print("   ", linha.strip())
print()
print("  Secao 4.2 do artigo publicado:")
print('    "the argmin lies at H = 14 (RMSECV = 0.2093 +/- 0.0269 on the')
print('     normalized scale) and the one-SE rule selects H* = 10"')
print()
