"""Reconferência dos picos do bioprocess nos dados crus, antes do SNV (19/11/2026).

`conferir_picos_bioprocess.py` conta picos comparando réplicas depois do
SNV. Aqui: (1) se o pico da banda 663 existe nos dados crus e se muda entre
réplicas; (2) se a variação depois do SNV vem só da divisão pelo desvio do
espectro; (3) o pico da linha 3208 em contagens.

Piloto: decisão de método, nada daqui entra no texto.

Uso (de dentro do repositório): python -B scripts/conferir_pico_663_cru.py
"""
import sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src")); warnings.simplefilter("ignore")
import numpy as np
from tcc.data import load
from tcc.preprocessing import SNVPreprocessor

ds = load("bioprocess", drop_artifact_bands=False)
R = ds.X
X = SNVPreprocessor().fit(R).transform(R)
g = ds.groups

# 1) o pico da 663 existe nos dados crus (antes do SNV)?
loc_raw = R[:, 663] - (R[:, 661] + R[:, 665]) / 2
ruido = np.median(np.abs(R[:, 600] - (R[:, 598] + R[:, 602]) / 2))
print("cru: altura local da 663, mediana", round(np.median(loc_raw), 1),
      "| mesma conta na 600 (ruído):", round(ruido, 1))

# 2) forma em volta da 663 num espectro com pico alto e na réplica dele
i = 274
rep = [j for j in np.flatnonzero(g == g[i]) if j != i][0]
print("cru em volta da 663, linha", i, ":", np.round(R[i, 659:668]).astype(int).tolist())
print("cru em volta da 663, réplica", rep, ":", np.round(R[rep, 659:668]).astype(int).tolist())

# 3) contagem independente: diferença da altura local entre réplicas (SNV)
loc = X[:, 663] - (X[:, 661] + X[:, 665]) / 2
n3 = 0
pares_a, pares_b = [], []
for gg in np.unique(g):
    idx = np.flatnonzero(g == gg)
    for k in idx:
        outros = idx[idx != k]
        if loc[k] - np.median(loc[outros]) > 3:
            n3 += 1
    if len(idx) == 2:
        pares_a.append(loc[idx[0]]); pares_b.append(loc[idx[1]])
print("contagem independente, altura local da 663 acima da réplica por > 3:", n3)

# 4) química ou instrumento? réplicas concordam? e com o alvo?
pa, pb = np.array(pares_a), np.array(pares_b)
print("correlação entre réplicas, altura local da 663:", round(np.corrcoef(pa, pb)[0, 1], 3))
loc_q = X[:, 1000] - (X[:, 990] + X[:, 1010]) / 2
qa = [];  qb = []
for gg in np.unique(g):
    idx = np.flatnonzero(g == gg)
    if len(idx) == 2:
        qa.append(loc_q[idx[0]]); qb.append(loc_q[idx[1]])
print("controle, banda 1000 (altura sobre ±10):", round(np.corrcoef(qa, qb)[0, 1], 3))
print("correlação da altura local da 663 com y (glicose):", round(np.corrcoef(loc, ds.y)[0, 1], 3))

# 5) a linha 3208 nos dados crus
d = R[3208] - R[3207]
j = int(np.argmax(d))
print("3208 cru: maior excesso sobre a réplica na banda", j, "=", round(d[j]),
      "| vizinhas", np.round(d[j-3:j+4]).astype(int).tolist(),
      "| típico |dif| cru:", round(np.median(np.abs(d))))

# --- a altura crua da 663 é constante? ---
ds = load("bioprocess", drop_artifact_bands=False); R = ds.X; X = SNVPreprocessor().fit(R).transform(R); g = ds.groups
h_raw = R[:, 663] - (R[:, 661] + R[:, 665]) / 2
h_snv = X[:, 663] - (X[:, 661] + X[:, 665]) / 2
p = np.percentile(h_raw, [1, 25, 50, 75, 99])
print("altura crua da 663 (contagens): p1,p25,p50,p75,p99 =", np.round(p).astype(int).tolist())
print("espectros com altura crua < 1000:", int((h_raw < 1000).sum()), "de", len(R))
sd = R.std(axis=1)
print("altura no SNV ≈ altura crua / desvio do espectro? correlação:",
      round(np.corrcoef(h_snv, h_raw / sd)[0, 1], 4))
print("correlação da altura no SNV com 1/desvio:", round(np.corrcoef(h_snv, 1 / sd)[0, 1], 3))
# entre réplicas, cru: a diferença relativa da altura
dif = []
for gg in np.unique(g):
    idx = np.flatnonzero(g == gg)
    if len(idx) == 2:
        a, b = h_raw[idx]
        dif.append(abs(a - b) / ((a + b) / 2))
print("diferença relativa da altura crua entre réplicas: mediana", round(np.median(dif), 3),
      "p95", round(np.percentile(dif, 95), 3))

# --- correlação crua com a glicose e os dois grupos de altura ---
ds = load("bioprocess", drop_artifact_bands=False); R = ds.X
h = R[:, 663] - (R[:, 661] + R[:, 665]) / 2
print("correlação da altura CRUA com a glicose:", round(np.corrcoef(h, ds.y)[0, 1], 3))
cont, bordas = np.histogram(h, bins=[0, 1000, 1400, 1600, 1800, 2500, 3000, 3100, 3300, 3500, 1e9])
print("histograma da altura crua:", list(zip(bordas[:-1].astype(int).tolist(), cont.tolist())))
print("entre 1.800 e 3.000:", int(((h > 1800) & (h < 3000)).sum()))
