"""Varredura de `c` sob o protocolo: B5(c) e B2'(c), piloto (PROTOCOLO; ADR 017).

A orientação pediu, em 12/11/2026, que `c` fosse um eixo varrido com grade
declarada e que a varredura dela (`scripts/orientacao/verify_b5_logit_scale.py`,
partição fixa do artigo, parada no teste) fosse refeita sob este protocolo.
Grade e `c_TOST` declarados no PROTOCOLO antes de rodar: a grade fixa da
orientação mais o `c_TOST` medido de cada conjunto (`scripts/medir_c_tost.py`).

Em cada conjunto, `seed_split` 0–29, `seed_algo` 0, e em cada `c`:
- B2'(c) (`mlp_weighted_scaled`), porta congelada em `softmax(c·logit(clip(s))/τ)`;
- B5(c) (`gate_prior_scaled`), a mesma porta, treinável e isenta de L2.
O Δ = R²(B5(c)) − R²(B2'(c)) na mesma partição é a quantidade da H8 nesse `c`.
Também o B3 (`gate_uniform`), como referência do extremo uniforme.

**Piloto** (`seed_split` 0–29): nenhum número daqui entra no texto como
resultado, e nada do protocolo muda com base neles.

Uma thread por processo; cada partição de um conjunto roda inteira num
processo (todos os braços e todos os `c`).

Uso:
  python -B varrer_c.py rodar [processos] [conjuntos...]
  python -B varrer_c.py resumo
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

SAIDA = RAIZ / "results" / "varredura_c.csv"
CONJUNTOS = ["tecator", "gasoline", "mango", "bioprocess"]
SEMENTES = range(30)
GRADE = [1.0, 0.5, 0.3, 0.17, 0.10, 0.054, 0.026, 0.0]
# Medidos em 12/11 antes da varredura (PROTOCOLO, "Os `c_TOST` medidos").
C_TOST = {"tecator": 0.0306, "gasoline": 0.0289, "mango": 0.0417, "bioprocess": 0.1140}
CAMPOS = ["conjunto", "seed_split", "braco", "c", "r2", "rmsep", "d", "g",
          "topo_trocou", "top10_mantidas", "melhor_epoca", "tempo_s"]


def grade(conjunto):
    return sorted(set(GRADE) | {C_TOST[conjunto]}, reverse=True)


def uma_particao(conjunto, s):
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.arms.gate import gate_prior_scaled, gate_uniform, mlp_weighted_scaled
    from tcc.data import load
    from tcc.protocol import evaluate

    ds = load(conjunto)
    bracos = [("B3", None, gate_uniform())]
    for c in grade(conjunto):
        bracos += [("B2'", c, mlp_weighted_scaled(c=c)), ("B5", c, gate_prior_scaled(c=c))]
    linhas = []
    for nome, c, arm in bracos:
        r = evaluate(arm, ds, seed_split=s, seed_algo=0)
        h = r.hyperparams
        linhas.append({
            "conjunto": conjunto, "seed_split": s, "braco": nome,
            "c": "" if c is None else f"{c:g}",
            "r2": f"{r.r2:.6f}", "rmsep": f"{r.rmsep:.6f}",
            "d": f"{h['gate_max_disp']:.6f}", "g": f"{h['gate_gap']:.6f}",
            "topo_trocou": int(h["gate_top_band_initial"] != h["gate_top_band_final"]),
            "top10_mantidas": h["gate_top10_kept"], "melhor_epoca": h["best_epoch"],
            "tempo_s": f"{r.wall_time:.2f}",
        })
    return conjunto, s, linhas


def ler():
    if not SAIDA.exists():
        return []
    with open(SAIDA, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rodar(processos, conjuntos):
    feitos = {(r["conjunto"], int(r["seed_split"])) for r in ler()}
    tarefas = [(c, s) for c in conjuntos for s in SEMENTES if (c, s) not in feitos]
    novo = not SAIDA.exists()
    print(f"{len(tarefas)} partições, {processos} processo(s), 1 thread cada", flush=True)
    t0 = time.time()
    with open(SAIDA, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        if novo:
            w.writeheader()
        with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
            futuros = [ex.submit(uma_particao, c, s) for c, s in tarefas]
            for fut in as_completed(futuros):
                conjunto, s, linhas = fut.result()
                w.writerows(linhas)
                f.flush()
                print(f"[{(time.time() - t0) / 60:5.1f} min] {conjunto:<10} seed {s:>2}", flush=True)


def resumo():
    from scipy.stats import wilcoxon

    tab = {}
    for r in ler():
        tab[(r["conjunto"], int(r["seed_split"]), r["braco"], r["c"])] = r
    for conj in CONJUNTOS:
        sementes = sorted({k[1] for k in tab if k[0] == conj})
        if not sementes:
            continue
        print(f"\n{conj} (piloto, {len(sementes)} partições; c_TOST = {C_TOST[conj]:g})")
        print(f"{'c':>7}{'d med':>8}{'g·c med':>9}{'topo troca':>11}{'top10':>7}"
              f"{'R² B2′':>9}{'R² B5':>8}{'Δ med':>9}{'faixa Δ':>20}{'Δ≥0':>7}{'p':>7}")
        for c in grade(conj):
            cs = f"{c:g}"
            ok = [s for s in sementes if (conj, s, "B5", cs) in tab and (conj, s, "B2'", cs) in tab]
            b5 = [tab[(conj, s, "B5", cs)] for s in ok]
            b2 = [tab[(conj, s, "B2'", cs)] for s in ok]
            r5 = np.array([float(r["r2"]) for r in b5])
            r2 = np.array([float(r["r2"]) for r in b2])
            d = r5 - r2
            p = f"{wilcoxon(d).pvalue:.3f}" if np.any(d != 0) else "—"
            marca = " *" if abs(c - C_TOST[conj]) < 1e-12 else ""
            print(f"{c:>7.4g}{np.median([float(r['d']) for r in b5]):>8.3f}"
                  f"{np.median([float(r['g']) for r in b5]):>9.3f}"
                  f"{sum(int(r['topo_trocou']) for r in b5):>7}/{len(b5):<3}"
                  f"{np.median([int(r['top10_mantidas']) for r in b5]):>7.0f}"
                  f"{np.median(r2):>9.4f}{np.median(r5):>8.4f}{np.median(d):>+9.4f}"
                  f"   [{d.min():+.4f}; {d.max():+.4f}]{int(np.sum(d >= 0)):>4}/{len(d)}"
                  f"{p:>7}{marca}")
        b3 = [tab[(conj, s, "B3", "")] for s in sementes if (conj, s, "B3", "") in tab]
        if b3:
            print(f"     B3: R² mediano {np.median([float(r['r2']) for r in b3]):.4f}, "
                  f"d mediano {np.median([float(r['d']) for r in b3]):.3f}")
    print("\n* = c_TOST do conjunto. Δ = R²(B5(c)) − R²(B2'(c)) na mesma partição. "
          "'g·c' é a distância inicial do topo nesse c.")


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
