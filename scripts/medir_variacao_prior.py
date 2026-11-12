"""Quanto o prior da porta muda de uma partição para outra? (PROTOCOLO, H5 e H6)

O PROTOCOLO deixou pendente, na reinterpretação da H5: "entre partições o
prior é recalculado em cada treino, e o quanto ele varia de uma partição
para outra ainda não foi medido — é a primeira coisa a medir no piloto".
Importa porque, se o prior quase não muda, a porta parte do mesmo lugar em
toda partição, e Jaccard alto da porta seria, nas palavras do parecer de
01/10, "o esperado de modelos que partem da mesma inicialização".

O prior é o do braço (`tcc.arms.gate.anova_prior`), calculado nas mesmas
linhas que o braço usa: as linhas de ajuste da rede (o treino menos a fold
de parada), na partição e nas folds do `evaluate()`, `seed_split` 0–29. Não
treina nada e não usa o teste.

Medidas, por conjunto:
- a banda de maior prior em cada partição: quantas partições têm a mesma;
- Jaccard dos top-10 entre os 435 pares de partições;
- correlação de Pearson do vetor de prior entre os pares;
- a referência do acaso para o Jaccard de dois top-10 sorteados.

Uso: python -B medir_variacao_prior.py [conjuntos...]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

import numpy as np

from diagnosticar_rede_mango import treino_e_parada
from tcc.arms.gate import anova_prior
from tcc.data import load

K = 10


def jaccard(a, b):
    return len(a & b) / len(a | b)


def acaso(p, k=K, n=20000, rng=np.random.default_rng(0)):
    return float(np.mean([jaccard(set(rng.choice(p, k, replace=False)),
                                  set(rng.choice(p, k, replace=False))) for _ in range(n)]))


def main(conjuntos):
    print(f"{'conjunto':<11}{'p':>5}  {'topo modal':>12}{'Jaccard top-10':>24}"
          f"{'acaso':>7}{'correlação do prior':>26}")
    for nome in conjuntos:
        ds = load(nome)
        priors = []
        for s in range(30):
            X, y, folds = treino_e_parada(ds, s)
            fit_idx = folds[0][0]
            Xf = X[fit_idx]
            sd = Xf.std(0)
            Xz = (Xf - Xf.mean(0)) / np.where(sd == 0, 1.0, sd)
            priors.append(anova_prior(Xz, y[fit_idx]))
        P = np.array(priors)
        p = P.shape[1]
        topo = Counter(int(np.argmax(v)) for v in P)
        banda, vezes = topo.most_common(1)[0]
        tops = [set(np.argsort(v)[-K:]) for v in P]
        J = np.array([jaccard(a, b) for a, b in combinations(tops, 2)])
        C = np.array([np.corrcoef(a, b)[0, 1] for a, b in combinations(P, 2)])
        print(f"{nome:<11}{p:>5}  {f'{vezes}/30 (b{banda})':>12}"
              f"{f'{np.median(J):.2f} [{J.min():.2f}; {J.max():.2f}]':>24}"
              f"{acaso(p):>7.3f}"
              f"{f'{np.median(C):.4f} [{C.min():.4f}; {C.max():.4f}]':>26}", flush=True)
        outros = ", ".join(f"b{b}: {n}" for b, n in topo.most_common()[1:4])
        if outros:
            print(f"{'':<11}outras bandas no topo: {outros}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["tecator", "gasoline", "mango", "bioprocess"])
