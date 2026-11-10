"""Vazamento das réplicas do Tecator na CV interna: quanto pesa na escolha de H*?

Pedido da orientação em 09/11/2026 (ADR 009): a medida de 05/11 cobria só
o vazamento treino/teste no PLS. Falta o da CV interna, em que gêmeos em
folds diferentes podem escolher o número de componentes. Desenho dela:
"com a partição nova fixa, compare o H* escolhido com os gêmeos juntos no
mesmo fold contra o H* com eles em folds diferentes".

Para cada `seed_split` de 0 a 29, a partição e o SNV de `evaluate()`, com
a regra de réplicas de 09/11 (180 grupos). Duas versões das folds internas,
que diferem só na posição das réplicas:
- juntos: as folds do protocolo (`_make_cv_folds` com os grupos);
- separados: as mesmas folds, mas, em cada grupo com mais de uma linha no
  treino, a primeira linha fica e as outras vão para as folds seguintes
  (f+1, f+2, ... módulo 5). Nenhuma outra linha muda de fold.

Em cada versão, o `PLSArm` (regra de um erro-padrão) dá H*, o RMSECV e o
R² no teste do modelo final.

Uso: python -B medir_vazamento_cv_interna_tecator.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from scipy.stats import wilcoxon
from sklearn.metrics import r2_score

from tcc.arms.base import Budget
from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.preprocessing import SNVPreprocessor
from tcc.protocol import DEFAULT_N_SPLITS, DEFAULT_TEST_SIZE, _make_cv_folds, _split_train_test

ds = load("tecator")


def separar_gemeos(folds, grupos_treino, n_splits):
    """Mesmas folds, com as réplicas de cada grupo espalhadas em folds
    diferentes. Devolve as folds novas e quantas linhas mudaram."""
    n = len(grupos_treino)
    fold_de = np.empty(n, dtype=int)
    for f, (_, va) in enumerate(folds):
        fold_de[va] = f
    novo = fold_de.copy()
    movidas = 0
    for g in np.unique(grupos_treino):
        membros = np.flatnonzero(grupos_treino == g)
        for k, i in enumerate(membros[1:], start=1):
            novo[i] = (fold_de[membros[0]] + k) % n_splits
            movidas += 1
    todas = np.arange(n)
    return [(todas[novo != f], todas[novo == f]) for f in range(n_splits)], movidas


print(f"tecator: {len(np.unique(ds.groups))} grupos; seed_split 0 a 29\n")
print(f"{'seed':>4} {'movidas':>7} {'H* juntos':>9} {'H* separ.':>9} "
      f"{'RMSECV juntos':>13} {'RMSECV separ.':>13} {'R2 juntos':>9} {'R2 separ.':>9}", flush=True)
linhas = []
for s in range(30):
    split_seed, cv_seed = np.random.SeedSequence(s).spawn(2)
    tr, te = _split_train_test(
        n=ds.X.shape[0], test_size=DEFAULT_TEST_SIZE,
        rng=np.random.default_rng(split_seed), groups=ds.groups,
    )
    snv = SNVPreprocessor().fit(ds.X[tr])
    Xtr, Xte, ytr, yte = snv.transform(ds.X[tr]), snv.transform(ds.X[te]), ds.y[tr], ds.y[te]
    juntos = _make_cv_folds(
        n_train=len(tr), n_splits=DEFAULT_N_SPLITS,
        rng=np.random.default_rng(cv_seed), groups=ds.groups[tr],
    )
    separados, movidas = separar_gemeos(juntos, ds.groups[tr], DEFAULT_N_SPLITS)
    r = {}
    for nome, folds in (("juntos", juntos), ("separados", separados)):
        fit = PLSArm().fit(Xtr, ytr, folds, np.random.default_rng(0), Budget())
        r[nome] = (fit.hyperparams["n_components"], fit.rmse_cv, r2_score(yte, fit.predict(Xte)))
    linhas.append((movidas, *r["juntos"], *r["separados"]))
    print(f"{s:>4} {movidas:>7} {r['juntos'][0]:>9} {r['separados'][0]:>9} "
          f"{r['juntos'][1]:>13.4f} {r['separados'][1]:>13.4f} "
          f"{r['juntos'][2]:>9.4f} {r['separados'][2]:>9.4f}", flush=True)

a = np.array(linhas)
h_j, h_s = a[:, 1], a[:, 4]
cv_j, cv_s = a[:, 2], a[:, 5]
r2_j, r2_s = a[:, 3], a[:, 6]
print(f"\nlinhas movidas por partição: mediana {np.median(a[:, 0]):.0f}, faixa {a[:, 0].min():.0f} a {a[:, 0].max():.0f}")
print(f"H*: igual em {int(np.sum(h_j == h_s))} de 30; maior com os gêmeos separados em "
      f"{int(np.sum(h_s > h_j))}; menor em {int(np.sum(h_s < h_j))}")
d = cv_s - cv_j
print(f"RMSECV separados − juntos: mediana {np.median(d):+.4f}, faixa [{d.min():+.4f}; {d.max():+.4f}]; "
      f"menor (mais otimista) em {int(np.sum(d < 0))} de 30; Wilcoxon p = {wilcoxon(d).pvalue:.3f}")
d = r2_s - r2_j
nz = np.any(d != 0)
print(f"R² de teste separados − juntos: mediana {np.median(d):+.4f}, faixa [{d.min():+.4f}; {d.max():+.4f}]"
      + (f"; Wilcoxon p = {wilcoxon(d).pvalue:.3f}" if nz else "; idênticos"))
