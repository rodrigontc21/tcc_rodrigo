"""Custo do VIPArm contra o PLS de espectro completo, num conjunto.

Mesmo caminho de medir_custo_ipls.py: evaluate() com SNV e particao
agrupada, seed_split 0, seed_algo 0, busca completa (limiar e numero de
componentes escolhidos por CV interna).

Os R2 sao de uma particao so: servem para conferir o encanamento, nao sao
resultado.

Uso: python medir_custo_vip.py tecator|gasoline|mango|bioprocess
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tcc.arms.pls import PLSArm
from tcc.arms.vip import VIPArm
from tcc.data import load
from tcc.protocol import evaluate

nome = sys.argv[1]
ds = load(nome)
print(f"{nome}: X {ds.X.shape}", flush=True)

linhas = []
for arm in (PLSArm(), VIPArm()):
    r = evaluate(arm, ds, seed_split=0, seed_algo=0)
    linhas.append(r)
    print(f"  {r.arm_name:<14} R2 {r.r2:.4f}  RMSEP {r.rmsep:.4f}  n_fits {r.n_fits:>5}  "
          f"tempo {r.wall_time:7.1f} s  hiperparametros {r.hyperparams}", flush=True)

pls, vip = linhas
print(f"  razao VIP/PLS: {vip.n_fits / pls.n_fits:.2f}x em ajustes, "
      f"{vip.wall_time / pls.wall_time:.2f}x em tempo")
