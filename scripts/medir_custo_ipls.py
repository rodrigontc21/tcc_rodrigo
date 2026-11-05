"""Custo do IPLSArm contra o PLS de espectro completo, num conjunto.

Mesmo caminho da grade: evaluate() com SNV e particao agrupada, seed_split 0
(faixa de exploracao, 0-29), seed_algo 0. O iPLS roda com a busca completa
(int_num e glob_ncomp escolhidos por CV interna), que e o que a grade usara.

Os R2 sao de uma particao so: servem para conferir o encanamento, nao sao
resultado.

Uso: python medir_custo_ipls.py tecator|gasoline|mango|bioprocess
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tcc.arms.ipls import IPLSArm
from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.protocol import evaluate

nome = sys.argv[1]
ds = load(nome)
print(f"{nome}: X {ds.X.shape}", flush=True)

linhas = []
for arm in (PLSArm(), IPLSArm()):
    r = evaluate(arm, ds, seed_split=0, seed_algo=0)
    linhas.append(r)
    print(f"  {r.arm_name:<10} R2 {r.r2:.4f}  RMSEP {r.rmsep:.4f}  n_fits {r.n_fits:>7}  "
          f"tempo {r.wall_time:8.1f} s  hiperparametros {r.hyperparams}", flush=True)

pls, ipls = linhas
print(f"  razao iPLS/PLS: {ipls.n_fits / pls.n_fits:.1f}x em ajustes, "
      f"{ipls.wall_time / pls.wall_time:.1f}x em tempo")
