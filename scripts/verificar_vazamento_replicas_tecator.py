"""Quanto as réplicas do Tecator que o ADR 009 não agrupa inflam o resultado?

O Tecator tem 22 pares de espectros idênticos, todos com `y` idêntico, e o
agrupamento do ADR 009 só junta 2 deles (adendo de 05/11/2026 do ADR 009).
Nos outros 20, um membro pode ficar no treino e o gêmeo no teste.

Teste, sem mudar o protocolo: `evaluate()` com o braço de referência
(`PLSArm`, SNV, partição e folds atuais), `seed_split` 0 a 29, `seed_algo`
0. Para cada semente, o MESMO modelo e o MESMO teste, com o R² e o RMSEP
calculados de dois jeitos:
  teste inteiro                  o que o protocolo reporta hoje
  sem os gêmeos                  tirando do teste os espectros cujo gêmeo
                                 idêntico ficou no treino
Como tirar amostras do teste muda o R² mesmo sem vazamento, cada semente
tem também uma referência: tirar do teste o mesmo número de amostras SEM
gêmeo, sorteadas (200 sorteios, média). O efeito do vazamento é a
diferença entre os dois.

Também conta os pares que ficam ambos no treino mas em folds diferentes da
CV interna, que podem otimizar a escolha do número de componentes. Esse
efeito NÃO é medido aqui.

Uso: python -B verificar_vazamento_replicas_tecator.py
"""

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from sklearn.metrics import mean_squared_error, r2_score

from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.protocol import DEFAULT_N_SPLITS, DEFAULT_TEST_SIZE, _make_cv_folds, _split_train_test, evaluate

SEMENTES = range(30)
SORTEIOS = 200

ds = load("tecator")
blocos = defaultdict(list)
for i, linha in enumerate(ds.X):
    blocos[linha.tobytes()].append(i)
pares = [v for v in blocos.values() if len(v) > 1]
gemeo = {}
for a, b in pares:
    gemeo[a], gemeo[b] = b, a
print(f"Tecator: {ds.X.shape[0]} linhas, {len(pares)} pares de espectros idênticos, "
      f"{sum(len({ds.groups[j] for j in v}) == 1 for v in pares)} agrupados pelo ADR 009\n")


def metricas(y, p):
    return r2_score(y, p), float(np.sqrt(mean_squared_error(y, p)))


print(f"{'seed':>4} {'teste':>5} {'gêmeos':>6} {'R² inteiro':>10} {'R² sem gêmeos':>13} "
      f"{'R² ref.':>8} {'ΔR² vaz.':>9} {'ΔRMSEP vaz.':>11} {'pares em folds dif.':>19}")
d_r2, d_rmsep, n_gemeos, n_folds = [], [], [], []
for s in SEMENTES:
    res = evaluate(arm=PLSArm(), dataset=ds, seed_split=s, seed_algo=0)
    test_idx, y_pred = res.test_idx, res.y_pred
    y_test = ds.y[test_idx]
    treino = set(range(ds.X.shape[0])) - set(test_idx.tolist())
    vaza = np.array([i in gemeo and gemeo[i] in treino for i in test_idx])
    k = int(vaza.sum())

    r2_all, rmsep_all = metricas(y_test, y_pred)
    r2_sem, rmsep_sem = metricas(y_test[~vaza], y_pred[~vaza])

    # referência: tirar k amostras sem gêmeo, sorteadas
    rng = np.random.default_rng(1000 + s)
    sem_gemeo = np.flatnonzero(np.array([i not in gemeo for i in test_idx]))
    ref_r2, ref_rmsep = [], []
    for _ in range(SORTEIOS):
        fora = rng.choice(sem_gemeo, size=k, replace=False)
        manter = np.setdiff1d(np.arange(len(test_idx)), fora)
        r, e = metricas(y_test[manter], y_pred[manter])
        ref_r2.append(r)
        ref_rmsep.append(e)
    dr2 = (r2_all - r2_sem) - (r2_all - np.mean(ref_r2))
    drmsep = (rmsep_sem - rmsep_all) - (np.mean(ref_rmsep) - rmsep_all)

    # pares com os dois no treino, em folds diferentes da CV interna
    split_seed, cv_seed = np.random.SeedSequence(s).spawn(2)
    tr_idx, _ = _split_train_test(
        n=ds.X.shape[0], test_size=DEFAULT_TEST_SIZE,
        rng=np.random.default_rng(split_seed), groups=ds.groups,
    )
    assert set(tr_idx.tolist()) == treino
    folds = _make_cv_folds(
        n_train=len(tr_idx), n_splits=DEFAULT_N_SPLITS,
        rng=np.random.default_rng(cv_seed), groups=ds.groups[tr_idx],
    )
    fold_de = {}
    for f, (_, va) in enumerate(folds):
        for j in va:
            fold_de[int(tr_idx[j])] = f
    nf = sum(a in fold_de and b in fold_de and fold_de[a] != fold_de[b] for a, b in pares)

    d_r2.append(dr2)
    d_rmsep.append(drmsep)
    n_gemeos.append(k)
    n_folds.append(nf)
    print(f"{s:>4} {len(test_idx):>5} {k:>6} {r2_all:>10.4f} {r2_sem:>13.4f} "
          f"{np.mean(ref_r2):>8.4f} {dr2:>+9.4f} {drmsep:>+11.4f} {nf:>19}", flush=True)


def resumo(a):
    a = np.asarray(a)
    return f"mediana {np.median(a):+.4f}, média {a.mean():+.4f}, faixa [{a.min():+.4f}; {a.max():+.4f}]"


print()
print(f"gêmeos no teste por semente: mediana {int(np.median(n_gemeos))}, "
      f"faixa {min(n_gemeos)} a {max(n_gemeos)}")
print(f"pares em folds diferentes da CV interna: mediana {int(np.median(n_folds))}, "
      f"faixa {min(n_folds)} a {max(n_folds)}")
print(f"ΔR² do vazamento (positivo = o teste inteiro infla o R²):  {resumo(d_r2)}")
print(f"ΔRMSEP do vazamento (positivo = o teste inteiro subestima o erro): {resumo(d_rmsep)}")
print(f"sementes com ΔR² > 0: {sum(x > 0 for x in d_r2)} de {len(d_r2)}")
