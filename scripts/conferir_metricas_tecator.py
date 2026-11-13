"""Conferência das métricas (ADR 019) e da camada de seleção (ADR 018) em
dados reais: Tecator, piloto.

Roda os braços pelo `evaluate()` e passa os `Result` pelas métricas, para
ver se os números fazem sentido, não para tirar conclusão:
- eixo `seed_split`: `seed_split` 0 a 9, `seed_algo` 0, todos os braços;
- eixo `seed_algo`: `seed_split` 0, `seed_algo` 0 a 4, os braços
  estocásticos (GA-PLS, CARS e as portas treináveis);
- linha de base: o top-k do próprio prior ANOVA nas mesmas partições;
- desempenho recalculado pela métrica contra o R² e o RMSEP do `Result`.

**Piloto** (`seed_split` 0–9): nada daqui entra no texto nem muda o
protocolo.
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

import numpy as np

CONJUNTO = "tecator"


def fabricas():
    from tcc.arms.cars import CARSArm
    from tcc.arms.gapls import GAPLSArm
    from tcc.arms.gate import gate_prior, gate_uniform, mlp_full, mlp_weighted
    from tcc.arms.ipls import IPLSArm
    from tcc.arms.pls import PLSArm
    from tcc.arms.vip import VIPArm
    return {"pls_full": PLSArm, "ipls": IPLSArm, "vip_threshold": VIPArm,
            "ga_pls": GAPLSArm, "cars": CARSArm, "mlp_full": mlp_full,
            "mlp_weighted": mlp_weighted, "gate_uniform": gate_uniform,
            "gate_prior": gate_prior}


def rodar(tarefa):
    nome, s, a = tarefa
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.data import load
    from tcc.protocol import evaluate
    return evaluate(fabricas()[nome](), load(CONJUNTO), seed_split=s, seed_algo=a)


def main():
    from diagnosticar_rede_mango import treino_e_parada
    from tcc.arms.gate import anova_prior
    from tcc.data import load
    from tcc.metrics import (cost_summary, expected_jaccard, mean_pairwise_jaccard,
                             performance, reproducibility)
    from tcc.selection import paired_k, to_selection, top_k

    nomes = list(fabricas())
    estocasticos = ["ga_pls", "cars", "gate_uniform", "gate_prior"]
    tarefas = [(n, s, 0) for n in nomes for s in range(10)]
    tarefas += [(n, 0, a) for n in estocasticos for a in range(1, 5)]
    with ProcessPoolExecutor(4, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(rodar, tarefas))
    ds = load(CONJUNTO)
    p = ds.X.shape[1]

    # 1. desempenho: a métrica recalcula o que o evaluate gravou
    difs = max(max(abs(performance(ds.y[r.test_idx], r.y_pred)["r2"] - r.r2),
                   abs(performance(ds.y[r.test_idx], r.y_pred)["rmsep"] - r.rmsep))
               for r in res)
    print(f"desempenho: maior diferença métrica × Result em {len(res)} resultados: {difs:.1e}")

    eixo_split = [r for r in res if r.seed_algo == 0]
    k = paired_k(eixo_split)
    tam = {n: sorted(len(r.selection) for r in eixo_split if r.arm_name == n)
           for n in ("ipls", "vip_threshold", "ga_pls", "cars")}
    print(f"\nk pareado (piloto, só para conferir): {k}; tamanhos por braço: "
          + "; ".join(f"{n} {v[0]}–{v[-1]}" for n, v in tam.items()))

    # 2. reprodutibilidade, com a referência do acaso
    rep_s = reproducibility(eixo_split, k=k, axis="seed_split")
    rep_a = reproducibility([r for r in res if r.seed_split == 0], k=k, axis="seed_algo")
    print(f"\n{'braço':<15}{'Jaccard partição':>18}{'acaso':>8}{'Jaccard algoritmo':>19}")
    for n in nomes:
        rs = [r for r in eixo_split if r.arm_name == n]
        sels = [to_selection(r, k) for r in rs]
        if sels[0] is None:
            print(f"{n:<15}{'— (sem seleção)':>18}")
            continue
        acaso = np.mean([expected_jaccard(len(a), len(b), p) for a, b in combinations(sels, 2)])
        ja = rep_a.get((CONJUNTO, n))
        print(f"{n:<15}{rep_s[(CONJUNTO, n)]:>18.3f}{acaso:>8.3f}"
              f"{('—' if ja is None else f'{ja:.3f}'):>19}")

    # 3. linha de base: o top-k do prior nas mesmas partições
    priors = []
    for s in range(10):
        X, y, folds = treino_e_parada(ds, s)
        f = folds[0][0]
        sd = X[f].std(0)
        priors.append(top_k(anova_prior((X[f] - X[f].mean(0)) / np.where(sd == 0, 1, sd), y[f]), k))
    print(f"{'prior (top-k)':<15}{mean_pairwise_jaccard(priors):>18.3f}"
          f"{expected_jaccard(k, k, p):>8.3f}")

    # 4. custo
    print("\ncusto (mediana, eixo seed_split):")
    for (_, n), c in cost_summary(eixo_split).items():
        print(f"  {n:<15} n_fits {c['n_fits']:>9.0f}   wall_time {c['wall_time']:>6.1f} s")


if __name__ == "__main__":
    main()
