"""Mede o `c` do TOST de cada conjunto (PROTOCOLO, "A grade de `c`"; ADR 017).

Regra fixada em 12/11/2026, antes de medir: `c_TOST` = mediana, nas
`seed_split` 0–29 com `seed_algo` 0, de `d_s / g_s`, onde, no B4-limpo
(`gate_prior`, `c` = 1, porta isenta) sob o protocolo,
- `d_s` é o maior |θ_final − θ_inicial| dos logits da porta;
- `g_s` é a distância inicial entre o 1º e o 2º logit.

O `c_TOST` usa só o deslocamento da porta, nunca o desempenho no teste. O
`evaluate()` calcula o R² de teste, porque é o caminho do protocolo, mas este
script não o grava nem o imprime.

Uma thread por processo e paralelismo só entre partições, como em
`rodar_bracos_30_particoes.py`.

Uso:
  python -B medir_c_tost.py rodar [processos] [conjuntos...]
  python -B medir_c_tost.py resumo
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np

SAIDA = RAIZ / "results" / "c_tost.csv"
CONJUNTOS = ["tecator", "gasoline", "mango", "bioprocess"]
SEMENTES = range(30)
CAMPOS = ["conjunto", "seed_split", "d", "g", "d_sobre_g", "melhor_epoca",
          "epocas", "topo_inicial", "topo_final", "tempo_s"]


def uma(conjunto, s):
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.arms.gate import gate_prior
    from tcc.data import load
    from tcc.protocol import evaluate

    r = evaluate(gate_prior(), load(conjunto), seed_split=s, seed_algo=0)
    h = r.hyperparams
    return {
        "conjunto": conjunto, "seed_split": s,
        "d": f"{h['gate_max_disp']:.6f}", "g": f"{h['gate_gap']:.6f}",
        "d_sobre_g": f"{h['gate_max_disp'] / h['gate_gap']:.6f}",
        "melhor_epoca": h["best_epoch"], "epocas": h["epochs_run"],
        "topo_inicial": h["gate_top_band_initial"], "topo_final": h["gate_top_band_final"],
        "tempo_s": f"{r.wall_time:.2f}",
    }


def ler():
    if not SAIDA.exists():
        return []
    with open(SAIDA, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rodar(processos, conjuntos):
    feitos = {(r["conjunto"], int(r["seed_split"])) for r in ler()}
    tarefas = [(c, s) for c in conjuntos for s in SEMENTES if (c, s) not in feitos]
    novo = not SAIDA.exists()
    print(f"{len(tarefas)} treinos, {processos} processo(s), 1 thread cada", flush=True)
    t0 = time.time()
    with open(SAIDA, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        if novo:
            w.writeheader()
        with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
            futuros = [ex.submit(uma, c, s) for c, s in tarefas]
            for fut in as_completed(futuros):
                linha = fut.result()
                w.writerow(linha)
                f.flush()
                print(f"[{(time.time() - t0) / 60:5.1f} min] {linha['conjunto']:<10} "
                      f"seed {linha['seed_split']:>2}: d/g {float(linha['d_sobre_g']):.4f}",
                      flush=True)


def resumo():
    linhas = ler()
    print(f"{'conjunto':<11}{'n':>3}{'d med':>8}{'g med':>8}{'c_TOST':>9}"
          f"{'faixa d/g':>20}{'topo trocou':>13}")
    for c in CONJUNTOS:
        rs = [r for r in linhas if r["conjunto"] == c]
        if not rs:
            continue
        dg = np.array([float(r["d_sobre_g"]) for r in rs])
        d = np.median([float(r["d"]) for r in rs])
        g = np.median([float(r["g"]) for r in rs])
        trocou = sum(r["topo_inicial"] != r["topo_final"] for r in rs)
        print(f"{c:<11}{len(rs):>3}{d:>8.3f}{g:>8.2f}{np.median(dg):>9.4f}"
              f"   [{dg.min():.4f}; {dg.max():.4f}]{trocou:>8}/{len(rs)}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "rodar":
        a = sys.argv[2:]
        proc = int(a[0]) if a and a[0].isdigit() else 4
        conj = [x for x in a if not x.isdigit()] or CONJUNTOS
        rodar(proc, conj)
    elif len(sys.argv) >= 2 and sys.argv[1] == "resumo":
        resumo()
    else:
        sys.exit(__doc__)
