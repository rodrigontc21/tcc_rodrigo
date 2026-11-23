"""O iPLS escolhe as mesmas bandas com o OpenBLAS no R? (23/11/2026)

A orientação respondeu em 05/11: o OpenBLAS no R só entra se as seleções
das `seed_split` 0 a 4 saírem idênticas nos dois BLAS (o de referência,
que o R usa hoje, e o OpenBLAS). Aqui o iPLS roda sem mudança nenhuma, com
`evaluate()` como na produção (`seed_algo` 0), uma thread por processo, e
grava, por conjunto e partição: as bandas selecionadas, o `int_num`, o
número de componentes, o R² e o tempo, mais o BLAS que o R carregou.

Dois passos, um por BLAS (a troca do BLAS é feita fora, no sistema):

    python -B conferir_blas_ipls.py gravar referencia
    python -B conferir_blas_ipls.py gravar openblas
    python -B conferir_blas_ipls.py comparar referencia openblas

Conjuntos: Tecator, Gasoline e Mango. O bioprocess fica de fora aqui: o
iPLS leva de 1h26 a 3h09 por partição nele.

Piloto: decisão de método, nada daqui entra no texto. Não muda o braço.
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import json
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

CONJUNTOS = ("tecator", "gasoline", "mango")
PARTICOES = range(5)


def saida(rotulo):
    return RAIZ / "results" / f"conferencia_blas_ipls_{rotulo}.json"


def uma(tarefa):
    sys.path.insert(0, str(RAIZ / "src"))
    import warnings

    from rpy2 import robjects

    from tcc.arms.ipls import IPLSArm
    from tcc.data import load
    from tcc.protocol import evaluate

    conjunto, s = tarefa
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = evaluate(IPLSArm(), load(conjunto), seed_split=s, seed_algo=0)
    blas = str(robjects.r("La_library()")[0])
    return {
        "conjunto": conjunto, "seed_split": s,
        "bandas": sorted(int(b) for b in r.selection),
        "int_num": r.hyperparams.get("int_num"),
        "n_componentes": r.hyperparams.get("n_components"),
        "r2": r.r2, "tempo_s": round(time.time() - t0, 1),
        "lapack_do_r": blas,
    }


def gravar(rotulo, processos):
    t0 = time.time()
    tarefas = [(c, s) for c in CONJUNTOS for s in PARTICOES]
    linhas = []
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        futuros = [ex.submit(uma, t) for t in tarefas]
        for fu in as_completed(futuros):
            l = fu.result()
            linhas.append(l)
            print(f"[{(time.time() - t0) / 60:6.1f} min] {l['conjunto']:8} seed {l['seed_split']}: "
                  f"{len(l['bandas'])} bandas, int_num {l['int_num']}, R² {l['r2']:.6f}", flush=True)
    linhas.sort(key=lambda l: (CONJUNTOS.index(l["conjunto"]), l["seed_split"]))
    libs = sorted({l["lapack_do_r"] for l in linhas})
    print("LAPACK que o R carregou:", libs)
    saida(rotulo).write_text(json.dumps(linhas, indent=1, ensure_ascii=False), encoding="utf-8")
    print("gravado em", saida(rotulo))


def comparar(a, b):
    A = {(l["conjunto"], l["seed_split"]): l for l in json.loads(saida(a).read_text(encoding="utf-8"))}
    B = {(l["conjunto"], l["seed_split"]): l for l in json.loads(saida(b).read_text(encoding="utf-8"))}
    print(f"{a}: {sorted({l['lapack_do_r'] for l in A.values()})}")
    print(f"{b}: {sorted({l['lapack_do_r'] for l in B.values()})}")
    iguais = 0
    for k in sorted(A, key=lambda k: (CONJUNTOS.index(k[0]), k[1])):
        x, y = A[k], B[k]
        mesma = x["bandas"] == y["bandas"]
        iguais += mesma
        print(f"{k[0]:8} seed {k[1]}: seleção {'IGUAL' if mesma else 'DIFERENTE'}; "
              f"int_num {x['int_num']}/{y['int_num']}; ncomp {x['n_componentes']}/{y['n_componentes']}; "
              f"ΔR² {y['r2'] - x['r2']:+.2e}; tempo {x['tempo_s']:.0f}/{y['tempo_s']:.0f} s")
    print(f"\nseleções idênticas em {iguais} de {len(A)}")
    for c in CONJUNTOS:
        ta = sum(A[(c, s)]["tempo_s"] for s in PARTICOES)
        tb = sum(B[(c, s)]["tempo_s"] for s in PARTICOES)
        print(f"{c:8} tempo somado: {ta:.0f} s ({a}) contra {tb:.0f} s ({b})")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "gravar":
        gravar(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    elif len(sys.argv) == 4 and sys.argv[1] == "comparar":
        comparar(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
