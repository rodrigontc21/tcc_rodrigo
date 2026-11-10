"""CARS contra o PLS completo em várias partições (ADR 016).

Em 05/11, numa partição só (`seed_split` 0), o CARS ficou abaixo do PLS
completo no Gasoline (R² 0,9667 no `protocolo` e 0,9706 no `fiel`, contra
0,9839) e acima no Tecator. Uma partição não decide. Este script repete a
comparação em 10 partições.

Desenho, fixado antes de rodar: `evaluate()` com SNV e partição agrupada,
`seed_split` 0 a 9, `seed_algo` 0; braços `pls_full`, `cars` (modo
`protocolo`) e `cars_fiel`. Os três usam a mesma partição em cada semente,
então a comparação é pareada: ΔR² = R²(CARS) − R²(PLS) por semente. O
Wilcoxon pareado entra como descrição; com 10 sementes, não decide nada
sozinho.

Uso: python -B comparar_cars_particoes.py tecator|gasoline [n_sementes]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from scipy.stats import wilcoxon

from tcc.arms.cars import CARSArm
from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.protocol import evaluate

nome = sys.argv[1]
n_sementes = int(sys.argv[2]) if len(sys.argv) > 2 else 10
ds = load(nome)
bracos = {"pls": PLSArm, "cars": CARSArm, "cars_fiel": lambda: CARSArm(mode="fiel")}
print(f"{nome}: X {ds.X.shape}, seed_split 0 a {n_sementes - 1}, seed_algo 0\n", flush=True)
print(f"{'seed':>4} {'PLS':>7} {'CARS':>7} {'bandas':>6} {'fiel':>7} {'bandas':>6}"
      f" {'tempo CARS':>10} {'tempo fiel':>10}", flush=True)

r2 = {k: [] for k in bracos}
rmsep = {k: [] for k in bracos}
bandas = {"cars": [], "cars_fiel": []}
for s in range(n_sementes):
    linha = {}
    for k, fabrica in bracos.items():
        linha[k] = evaluate(fabrica(), ds, seed_split=s, seed_algo=0)
        r2[k].append(linha[k].r2)
        rmsep[k].append(linha[k].rmsep)
        if k in bandas:
            bandas[k].append(linha[k].hyperparams["n_bands"])
    print(f"{s:>4} {linha['pls'].r2:>7.4f} {linha['cars'].r2:>7.4f}"
          f" {linha['cars'].hyperparams['n_bands']:>6} {linha['cars_fiel'].r2:>7.4f}"
          f" {linha['cars_fiel'].hyperparams['n_bands']:>6}"
          f" {linha['cars'].wall_time:>9.1f}s {linha['cars_fiel'].wall_time:>9.1f}s", flush=True)

pls = np.array(r2["pls"])
print()
for k in ("cars", "cars_fiel"):
    d = np.array(r2[k]) - pls
    p = wilcoxon(d).pvalue if np.any(d != 0) else float("nan")
    print(f"{k:<9} RMSEP mediano {np.median(rmsep[k]):.4f}, faixa [{min(rmsep[k]):.4f}; {max(rmsep[k]):.4f}]"
          f" (PLS {np.median(rmsep['pls']):.4f}, faixa [{min(rmsep['pls']):.4f}; {max(rmsep['pls']):.4f}])")
    print(f"{k:<9} R² mediano {np.median(r2[k]):.4f} (PLS {np.median(pls):.4f});"
          f" ΔR² mediano {np.median(d):+.4f}, faixa [{d.min():+.4f}; {d.max():+.4f}];"
          f" não abaixo do PLS em {int(np.sum(d >= 0))} de {len(d)};"
          f" Wilcoxon p = {p:.3f}; bandas medianas {np.median(bandas[k]):.0f}")
d = np.array(r2["cars"]) - np.array(r2["cars_fiel"])
print(f"protocolo − fiel: ΔR² mediano {np.median(d):+.4f}, faixa [{d.min():+.4f}; {d.max():+.4f}]")
