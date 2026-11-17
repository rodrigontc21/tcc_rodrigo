"""A grade alargada do VIP (ADR 014, 16/11/2026): a escolha ainda cai na borda?

Roda o `VIPArm` com a grade padrão (agora {0,2; 0,4; ...; 1,5}) nas
`seed_split` 0–29 do Tecator, do Gasoline e do Mango, e nas 0–3 do
bioprocess, e conta qual limiar cada partição escolheu. A grade foi
declarada antes desta rodada; aqui só se confere se a escolha saiu da borda
de baixo, onde caía no Mango com a grade antiga (0,8 em 30 de 30).

Piloto: nada daqui entra no texto. Os números de R² ficam no CSV de saída
para conferência, não para escolher a grade.

Uso: python -B conferir_grade_vip.py [processos]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import multiprocessing as mp
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

SAIDA = RAIZ / "results" / "conferencia_grade_vip.csv"
TAREFAS = ([("tecator", s) for s in range(30)] + [("gasoline", s) for s in range(30)]
           + [("mango", s) for s in range(30)] + [("bioprocess", s) for s in range(4)])


def uma(tarefa):
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.arms.vip import VIPArm
    from tcc.data import load
    from tcc.protocol import evaluate
    conjunto, s = tarefa
    r = evaluate(VIPArm(), load(conjunto), seed_split=s, seed_algo=0)
    return {"conjunto": conjunto, "seed_split": s, "limiar": r.hyperparams["threshold"],
            "n_bandas": r.hyperparams["n_bands"], "r2": f"{r.r2:.6f}",
            "n_ajustes": r.n_fits, "tempo_s": f"{r.wall_time:.1f}"}


def main():
    from tcc.arms.vip import DEFAULT_THRESHOLD_CANDIDATES as GRADE
    processos = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        linhas = list(ex.map(uma, TAREFAS))
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    print("grade:", GRADE)
    for conjunto in ("tecator", "gasoline", "mango", "bioprocess"):
        ls = [l for l in linhas if l["conjunto"] == conjunto]
        cont = Counter(l["limiar"] for l in ls)
        borda = sum(cont[g] for g in (GRADE[0], GRADE[-1]))
        bandas = sorted(l["n_bandas"] for l in ls)
        print(f"{conjunto:10} {len(ls):>2} partições | limiares: "
              + ", ".join(f"{t:g}: {cont[t]}" for t in GRADE if cont[t])
              + f" | na borda: {borda} | bandas: {bandas[0]} a {bandas[-1]}")
    print("gravado em", SAIDA)


if __name__ == "__main__":
    main()
