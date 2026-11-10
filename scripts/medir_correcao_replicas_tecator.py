"""O que muda no Tecator com a correção das réplicas (ADR 009).

Compara a regra original do ADR 009 (só linhas vizinhas com alvos
idênticos) com a regra em vigor desde 09/11/2026 (`tcc.data`: vizinhas,
espectro idêntico ou espectro próximo, sempre com alvos idênticos, em
componentes conexas).

Até 09/11 este script comparava a regra original com a correção de 06/11,
que só juntava os espectros idênticos (188 grupos); a medição daquele dia
está no DIARIO. Agora compara com a regra completa (180 grupos):

1. grupos antes e depois;
2. nas 30 partições de exploração (`seed_split` 0–29): quantas mudam o
   conjunto de teste, e quantos pares de espectros idênticos atravessam
   treino/teste antes e depois;
3. PLS completo (`PLSArm`, SNV) nessas 30 partições, antes e depois;
4. piso de ruído: dispersão relativa do RMSEP do `MeanArm` em 100
   partições, como no PROTOCOLO (7,7% no Tecator com a regra atual).

Uso: python -B medir_correcao_replicas_tecator.py
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from dataclasses import replace

import skfda.datasets

import tcc.data as data
from tcc.arms.mean import MeanArm
from tcc.arms.pls import PLSArm
from tcc.protocol import evaluate


depois = data.load("tecator")
_, alvos = skfda.datasets.fetch_tecator(return_X_y=True, as_frame=True)
regra_original = data._adjacent_replicate_groups(
    alvos[["fat", "water", "protein"]].to_numpy(dtype=float)
)
antes = replace(depois, groups=regra_original)
assert np.array_equal(antes.X, depois.X) and np.array_equal(antes.y, depois.y)

blocos = defaultdict(list)
for i, (x, y) in enumerate(zip(antes.X, antes.y)):
    blocos[(x.tobytes(), float(y))].append(i)
pares = [v for v in blocos.values() if len(v) > 1]
print(f"grupos: {len(np.unique(antes.groups))} antes, {len(np.unique(depois.groups))} depois; "
      f"{len(pares)} pares de espectro e alvo idênticos\n", flush=True)


def atravessam(test_idx):
    teste = set(test_idx.tolist())
    return sum(len({j in teste for j in v}) == 2 for v in pares)


print(f"{'seed':>4} {'teste igual':>11} {'pares cruzando':>15} {'R2 antes':>9} {'R2 depois':>9} "
      f"{'RMSEP antes':>11} {'RMSEP depois':>12}", flush=True)
r2 = {"antes": [], "depois": []}
rmsep = {"antes": [], "depois": []}
iguais = 0
for s in range(30):
    a = evaluate(PLSArm(), antes, seed_split=s, seed_algo=0)
    d = evaluate(PLSArm(), depois, seed_split=s, seed_algo=0)
    igual = set(a.test_idx.tolist()) == set(d.test_idx.tolist())
    iguais += igual
    for k, r in (("antes", a), ("depois", d)):
        r2[k].append(r.r2)
        rmsep[k].append(r.rmsep)
    print(f"{s:>4} {str(igual):>11} {atravessam(a.test_idx):>7} -> {atravessam(d.test_idx):<5}"
          f" {a.r2:>9.4f} {d.r2:>9.4f} {a.rmsep:>11.4f} {d.rmsep:>12.4f}", flush=True)

print(f"\npartições com o mesmo teste: {iguais} de 30")
for k in ("antes", "depois"):
    print(f"PLS {k:<6}: R² mediano {np.median(r2[k]):.4f} (média {np.mean(r2[k]):.4f}), "
          f"RMSEP mediano {np.median(rmsep[k]):.4f} (média {np.mean(rmsep[k]):.4f})")
dif = np.array(r2["depois"]) - np.array(r2["antes"])
print(f"R² depois − antes, por semente: mediana {np.median(dif):+.4f}, "
      f"faixa [{dif.min():+.4f}; {dif.max():+.4f}]")

print("\npiso de ruído (MeanArm, seed_split 0–99): desvio / média do RMSEP")
for nome, ds in (("antes", antes), ("depois", depois)):
    e = np.array([evaluate(MeanArm(), ds, seed_split=s, seed_algo=0).rmsep for s in range(100)])
    print(f"  {nome:<6}: {100 * e.std(ddof=1) / e.mean():.1f}%")
