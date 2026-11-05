"""Custo do CARSArm, nos dois modos, contra o PLS de espectro completo, num conjunto.

Mesmo caminho de medir_custo_ipls.py, medir_custo_vip.py e
medir_custo_gapls.py: evaluate() com SNV e particao agrupada, seed_split 0,
seed_algo 0. No modo `protocolo`, busca completa ((N, razao, fator do teto)
e numero de componentes do A1 por CV interna); no modo `fiel`, N = 100,
razao 0,9 e fator 3 (ADR 016).

Os R2 sao de uma particao so: servem para conferir o encanamento, nao sao
resultado.

Uso: python medir_custo_cars.py tecator|gasoline|mango|bioprocess
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tcc.arms.cars import CARSArm
from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.protocol import evaluate

nome = sys.argv[1]
ds = load(nome)
print(f"{nome}: X {ds.X.shape}", flush=True)

linhas = []
for arm in (PLSArm(), CARSArm(), CARSArm(mode="fiel")):
    r = evaluate(arm, ds, seed_split=0, seed_algo=0)
    linhas.append(r)
    print(f"  {r.arm_name:<10} R2 {r.r2:.4f}  RMSEP {r.rmsep:.4f}  n_fits {r.n_fits:>8}  "
          f"tempo {r.wall_time:8.1f} s  hiperparametros {r.hyperparams}", flush=True)

pls = linhas[0]
for r in linhas[1:]:
    print(f"  razao {r.arm_name}/PLS: {r.n_fits / pls.n_fits:.1f}x em ajustes, "
          f"{r.wall_time / pls.wall_time:.1f}x em tempo")
