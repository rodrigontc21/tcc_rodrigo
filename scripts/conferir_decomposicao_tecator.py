"""Conferência da decomposição e do TOST (ADR 020) em dados reais: Tecator, piloto.

Os cinco braços da decomposição (A1 = PLS completo, B1 = MLP sem porta,
B2 = porta do prior congelada, B3 = porta uniforme, B4 = B4-limpo) nas
`seed_split` 0–9, `seed_algo` 0, pelo `evaluate()`. Confere a identidade
aditiva nos dados reais, mostra os termos, roda um TOST com um δ **só
ilustrativo** e o Friedman com cada partição como bloco.

**Piloto:** nada daqui entra no texto nem muda o protocolo. O δ do TOST não
é o do protocolo, que ainda não foi fixado.
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np

DELTA_ILUSTRATIVO = 0.01  # em R²; NÃO é o δ do protocolo


def rodar(tarefa):
    nome, s = tarefa
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.arms.gate import gate_prior, gate_uniform, mlp_full, mlp_weighted
    from tcc.arms.pls import PLSArm
    from tcc.data import load
    from tcc.protocol import evaluate
    fab = {"pls_full": PLSArm, "mlp_full": mlp_full, "mlp_weighted": mlp_weighted,
           "gate_uniform": gate_uniform, "gate_prior": gate_prior}
    return evaluate(fab[nome](), load("tecator"), seed_split=s, seed_algo=0)


def main():
    from tcc.decomposition import (ARMS, additive_identity_gap, decompose, friedman,
                                   posthoc_wilcoxon_holm, tost)

    tarefas = [(n, s) for n in ARMS.values() for s in range(10)]
    with ProcessPoolExecutor(4, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(rodar, tarefas))

    dec = decompose(res)
    print(f"partições completas: {len(dec['total'])}, excluídas: {dec['excluidas']}")
    print(f"identidade aditiva, maior diferença: {additive_identity_gap(dec):.1e}\n")

    print(f"{'termo':<13}{'mediana':>9}{'média':>9}{'mín':>9}{'máx':>9}"
          f"   TOST com δ = {DELTA_ILUSTRATIVO} (ilustrativo)")
    for termo in ("nao_lin", "ponderacao", "aprendizado", "prior", "total"):
        v = np.array(list(dec[termo].values()))
        t = tost(v, DELTA_ILUSTRATIVO)
        print(f"{termo:<13}{np.median(v):>+9.4f}{v.mean():>+9.4f}{v.min():>+9.4f}{v.max():>+9.4f}"
              f"   IC90 [{t['ci_low']:+.4f}; {t['ci_high']:+.4f}]  p {t['p']:.3f}  "
              f"{'equivalente' if t['equivalent'] else 'não equivalente'}")

    nomes = list(ARMS.values())
    tab = np.array([[next(r.r2 for r in res if r.arm_name == n and r.seed_split == s)
                     for n in nomes] for s in range(10)])
    f = friedman(tab)
    print(f"\nFriedman (10 partições como blocos, 5 braços): estatística {f['statistic']:.2f}, "
          f"p {f['p']:.4f}")
    print("R² mediano: " + "  ".join(f"{n} {np.median(tab[:, i]):.4f}" for i, n in enumerate(nomes)))
    ph = posthoc_wilcoxon_holm(tab, nomes)
    sig = [f"{a}×{b} {v['p_holm']:.3f}" for (a, b), v in ph.items() if v["p_holm"] < 0.05]
    print("pares com p de Holm < 0,05: " + (", ".join(sig) if sig else "nenhum"))


if __name__ == "__main__":
    main()
