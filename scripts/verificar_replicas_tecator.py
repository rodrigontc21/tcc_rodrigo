"""Replicas do Tecator: pares de espectros identicos e o efeito na ancora do PLS.

Sustenta a "Ressalva obrigatoria" do ADR 013 e o item A1.

Uso: python verificar_replicas_tecator.py
"""

import sys

sys.dont_write_bytecode = True  # nao criar __pycache__ no repositorio do artigo

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[1]
PGSG = RAIZ / "docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
sys.path.insert(0, str(RAIZ / "src"))

X = pd.read_csv(PGSG / "data/raw/tecator/spectra.csv").values
Y = pd.read_csv(PGSG / "data/raw/tecator/targets.csv").values
gordura = Y[:, 1]  # coluna 1 = gordura (a coluna 0, rotulada Fat, e agua)

# pares de espectros identicos, bit a bit
grupos = defaultdict(list)
for i, linha in enumerate(X):
    grupos[linha.tobytes()].append(i)
pares = [v for v in grupos.values() if len(v) > 1]
print(f"  grupos de espectros identicos: {len(pares)}, "
      f"tamanhos {sorted(set(len(v) for v in pares))}")
print(f"  com o y tambem identico: "
      f"{sum(all((Y[v[0]] == Y[j]).all() for j in v) for v in pares)} de {len(pares)}")

# contra os grupos do ADR 009, no loader deste trabalho
from tcc.data import load  # noqa: E402

g = np.asarray(load("tecator").groups)
juntos = sum(1 for a, b in pares if g[a] == g[b])
print(f"  pares que o ADR 009 poe no mesmo grupo: {juntos}; separa: {len(pares) - juntos}")

# na particao do artigo (semente 42)
idx = np.arange(len(X))
tr, te = train_test_split(idx, test_size=0.2, random_state=42)
te_set = set(te)
cruzam = [(a, b) for a, b in pares if (a in te_set) != (b in te_set)]
print(f"  pares que atravessam a particao semente 42: {len(cruzam)}")


def r2_pls(tr_i, te_i, H=12):
    # mesmo protocolo da ancora: Z-score de X e y no treino, H* = 12 da gordura
    sx = StandardScaler().fit(X[tr_i])
    sy = StandardScaler().fit(gordura[tr_i, None])
    m = PLSRegression(H).fit(sx.transform(X[tr_i]), sy.transform(gordura[tr_i, None]).ravel())
    return r2_score(sy.transform(gordura[te_i, None]).ravel(),
                    m.predict(sx.transform(X[te_i])).ravel())


no_teste = {a if a in te_set else b for a, b in cruzam}
no_treino = {b if a in te_set else a for a, b in cruzam}
print()
print("  PLS na gordura, H* = 12 mantido:")
print(f"    particao do artigo, 172/43           R2 {r2_pls(tr, te):.4f}")
print(f"    tirando do teste os {len(no_teste)} com gemeo no treino  "
      f"R2 {r2_pls(tr, [i for i in te if i not in no_teste]):.4f}")
print(f"    tirando do treino os {len(no_treino)} gemeos          "
      f"R2 {r2_pls([i for i in tr if i not in no_treino], te):.4f}")
