"""O iPLS escolhe o `int_num` na borda da grade? (orientação, 16/11/2026)

No ensaio da grade final (partição 0), o iPLS escolheu `int_num` = 10, o
menor candidato, no Tecator, no Gasoline e no Mango. Aqui, nas `seed_split`
0–29 do Tecator e do Gasoline (o Mango leva ~18 min por partição), conta
quantas vezes cada `int_num` é escolhido e quantas caem na borda.

Piloto: decisão de método, nada daqui entra no texto.

Uso: python -B conferir_borda_ipls.py [processos]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import multiprocessing as mp
import sys
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

SAIDA = RAIZ / "results" / "conferencia_borda_ipls.csv"


def uma(tarefa):
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.arms.ipls import IPLSArm
    from tcc.data import load
    from tcc.protocol import evaluate
    conjunto, s = tarefa
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = evaluate(IPLSArm(), load(conjunto), seed_split=s, seed_algo=0)
    h = r.hyperparams
    return {"conjunto": conjunto, "seed_split": s, "int_num": h["int_num"],
            "borda": h["int_num_edge"] or "", "n_bandas": h["n_bands"], "r2": f"{r.r2:.6f}"}


def main():
    from tcc.arms.ipls import DEFAULT_INT_NUM_CANDIDATES
    processos = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    tarefas = [(c, s) for c in ("tecator", "gasoline") for s in range(30)]
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        linhas = list(ex.map(uma, tarefas))
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    print("grade:", DEFAULT_INT_NUM_CANDIDATES)
    for c in ("tecator", "gasoline"):
        ls = [l for l in linhas if l["conjunto"] == c]
        print(f"{c:9} int_num: {dict(sorted(Counter(l['int_num'] for l in ls).items()))} | "
              f"borda: {dict(Counter(l['borda'] or 'meio' for l in ls))}")
    print("gravado em", SAIDA)


if __name__ == "__main__":
    main()
