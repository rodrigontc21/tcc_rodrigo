"""Quanto custaria o CARSArm no bioprocess, sem rodar o braço inteiro.

Como o perfil do iPLS (`perfilar_custo_ipls.py`): mede uma execução do
CARS (`run_cars`) no fold externo 0 da partição de `evaluate()` com
`seed_split` 0 e SNV, com os 4 folds internos, e extrapola. O número de
componentes do A1 nessa partição é 7 (DIARIO de 28/10), então o teto é
7, 14 ou 21 conforme o fator.

Mede N = 50 com fator 1, 2 e 3, e N = 100 com fator 1, para ver como o
tempo cresce com N. Extrapolação, supondo os folds iguais ao 0:
- `protocolo`: 12 candidatos × 5 folds, mais a execução final no treino;
- `fiel`: (100; 0,9; 3) × 5 folds, mais a final.

A execução final usa o treino inteiro (5/4 das linhas de um fold) e 5
folds; a estimativa a conta como uma execução de fold, para baixo.

Uso: python -B estimar_custo_cars_bioprocess.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from tcc.arms.base import Budget
from tcc.arms.cars import DEFAULT_CARS_CANDIDATES, FAITHFUL_CONFIG, run_cars
from tcc.arms.ipls import _inner_folds
from tcc.data import load
from tcc.preprocessing import SNVPreprocessor
from tcc.protocol import DEFAULT_N_SPLITS, DEFAULT_TEST_SIZE, _make_cv_folds, _split_train_test

A1_NCOMP = 7  # DIARIO de 28/10, bioprocess, seed_split 0
RATIO = 0.9

ds = load("bioprocess")
split_seed, cv_seed = np.random.SeedSequence(0).spawn(2)
train_idx, _ = _split_train_test(
    n=ds.X.shape[0], test_size=DEFAULT_TEST_SIZE,
    rng=np.random.default_rng(split_seed), groups=ds.groups,
)
snv = SNVPreprocessor().fit(ds.X[train_idx])
X_train, y_train = snv.transform(ds.X[train_idx]), ds.y[train_idx]
cv_folds = _make_cv_folds(
    n_train=len(train_idx), n_splits=DEFAULT_N_SPLITS,
    rng=np.random.default_rng(cv_seed), groups=ds.groups[train_idx],
)
fold_train = cv_folds[0][0]
Xf, yf = X_train[fold_train], y_train[fold_train]
inner = _inner_folds(cv_folds, 0)
print(f"bioprocess: fold_train 0 com {Xf.shape[0]} linhas e {Xf.shape[1]} bandas, "
      f"{len(inner)} folds internos\n", flush=True)

tempos = {}
for n_runs, factor in ((50, 1), (50, 2), (50, 3), (100, 1)):
    budget = Budget()
    t0 = time.perf_counter()
    r = run_cars(X=Xf, y=yf, folds=inner, n_runs=n_runs, ratio=RATIO,
                 max_ncomp=factor * A1_NCOMP, rng=np.random.default_rng(0), budget=budget)
    tempos[(n_runs, factor)] = time.perf_counter() - t0
    print(f"N {n_runs:>3}, fator {factor} (teto {factor * A1_NCOMP:>2}): "
          f"{tempos[(n_runs, factor)]:7.1f} s, {budget.n_fits:>7} ajustes, "
          f"escolhido o subconjunto {r.best + 1} com {len(r.selection)} bandas", flush=True)

# N = 100 por fator: o tempo de N = 50 escalado pela razão medida no fator 1
escala_n = tempos[(100, 1)] / tempos[(50, 1)]
def t(n_runs, factor):
    base = tempos[(50, factor)]
    return base * (escala_n if n_runs == 100 else 1.0)

protocolo = sum(DEFAULT_N_SPLITS * t(n, f) for n, _, f in DEFAULT_CARS_CANDIDATES)
protocolo += t(100, 3)  # a final, no pior caso
fiel = (DEFAULT_N_SPLITS + 1) * t(FAITHFUL_CONFIG[0], FAITHFUL_CONFIG[2])
print(f"\nN = 100 custa {escala_n:.2f} vezes N = 50 (fator 1)")
print(f"estimativa por partição: protocolo {protocolo / 3600:.1f} h, fiel {fiel / 3600:.1f} h")
print(f"30 partições (exploração): protocolo {30 * protocolo / 3600:.0f} h, fiel {30 * fiel / 3600:.0f} h")
