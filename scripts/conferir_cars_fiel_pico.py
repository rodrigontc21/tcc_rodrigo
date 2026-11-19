"""Contraprova: é mesmo o pico da linha 3208 que derruba o CARS fiel? (19/11/2026)

`conferir_cars_fiel_bioprocess.py` apontou a linha 3208 do bioprocess, um
espectro com um pico estreito, como a causa do R² baixo do CARS fiel nas
partições 10 e 16. Aqui, a contraprova, com o modelo entregue pelo braço
sem mudança nenhuma:

1. em quais das 30 partições a linha 3208 cai no teste, e o R² do CARS
   fiel em cada uma (se ela cai no teste em partições boas, a explicação
   está incompleta);
2. nas partições 10 e 16: o R² sem a linha 3208 no teste; o R² com o
   espectro dela trocado pelo da réplica (linha 3207, mesma mistura); e o
   R² com só as bandas do pico trocadas pelas da réplica;
3. se as bandas do pico estão entre as que o CARS selecionou, e o peso que
   o modelo dá a elas.

Piloto: decisão de método, nada daqui entra no texto. Não muda o braço.

Uso: python -B conferir_cars_fiel_pico.py
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import multiprocessing as mp
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

CSV_30 = RAIZ / "results" / "bracos_bioprocess_30_particoes.csv"
LINHA, REPLICA = 3208, 3207


def particoes_com_a_linha():
    """Refaz só a partição treino/teste de `evaluate` (mesmas sementes)."""
    from tcc.data import load
    from tcc.protocol import DEFAULT_TEST_SIZE, _split_train_test

    ds = load("bioprocess")
    fora = []
    for s in range(30):
        split_seed, _cv = np.random.SeedSequence(s).spawn(2)
        _tr, te = _split_train_test(ds.X.shape[0], DEFAULT_TEST_SIZE,
                                    np.random.default_rng(split_seed), groups=ds.groups)
        if LINHA in set(int(i) for i in te):
            fora.append(s)
    return fora


def uma(s):
    sys.path.insert(0, str(RAIZ / "src"))
    from sklearn.metrics import r2_score

    from tcc.arms.cars import CARSArm
    from tcc.data import load
    from tcc.preprocessing import SNVPreprocessor
    from tcc.protocol import evaluate

    class Gravador(CARSArm):
        def fit(self, *a, **k):
            self.fitted = super().fit(*a, **k)
            return self.fitted

    ds = load("bioprocess")
    braco = Gravador(mode="fiel")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = evaluate(braco, ds, seed_split=s, seed_algo=0)
    snv = SNVPreprocessor().fit(ds.X)
    te = r.test_idx
    X_te = snv.transform(ds.X[te])
    y_te = ds.y[te]
    pos = int(np.flatnonzero(te == LINHA)[0])
    f = braco.fitted

    sem = np.ones(len(te), bool)
    sem[pos] = False
    r2_sem = r2_score(y_te[sem], r.y_pred[sem])

    X_rep = X_te.copy()
    X_rep[pos] = snv.transform(ds.X[[REPLICA]])[0]
    r2_rep = r2_score(y_te, f.predict(X_rep))

    dif = np.abs(snv.transform(ds.X[[LINHA]])[0] - snv.transform(ds.X[[REPLICA]])[0])
    pico = np.flatnonzero(dif > 3)
    X_pico = X_te.copy()
    X_pico[pos, pico] = snv.transform(ds.X[[REPLICA]])[0][pico]
    pred_pico = f.predict(X_pico)

    cols = list(f._columns)
    coef = np.abs(np.ravel(f._model.coef_))
    no_modelo = [int(b) for b in pico if b in cols]
    peso = {int(b): float(coef[cols.index(b)] / np.median(coef)) for b in no_modelo}

    return {
        "s": s, "r2": r.r2, "pred_linha": float(r.y_pred[pos]), "y_linha": float(y_te[pos]),
        "r2_sem_linha": r2_sem, "r2_com_replica": r2_rep,
        "r2_so_pico_trocado": r2_score(y_te, pred_pico),
        "pred_so_pico_trocado": float(pred_pico[pos]),
        "bandas_pico": [int(b) for b in pico], "pico_no_modelo": no_modelo,
        "peso_relativo": peso, "ncomp": r.hyperparams["n_components"],
    }


def main():
    with open(CSV_30, encoding="utf-8") as fh:
        r2 = {int(l["seed_split"]): float(l["r2"])
              for l in csv.DictReader(fh) if l["braco"] == "cars_fiel"}
    fora = particoes_com_a_linha()
    print(f"linha {LINHA} no teste nas partições: {fora}")
    for s in fora:
        print(f"  partição {s}: R² do CARS fiel {r2[s]:.4f}")
    alvo = [s for s in fora]
    with ProcessPoolExecutor(min(4, len(alvo)), mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(uma, alvo))
    for x in res:
        print(f"\npartição {x['s']} (ncomp {x['ncomp']}): R² {x['r2']:.4f}; "
              f"linha {LINHA}: real {x['y_linha']:.3f}, previsto {x['pred_linha']:.2f}")
        print(f"  sem a linha no teste: R² {x['r2_sem_linha']:.4f}")
        print(f"  espectro trocado pelo da réplica: R² {x['r2_com_replica']:.4f}")
        print(f"  só as bandas do pico trocadas: R² {x['r2_so_pico_trocado']:.4f} "
              f"(previsto {x['pred_so_pico_trocado']:.2f})")
        print(f"  bandas do pico {x['bandas_pico']}, no modelo: {x['pico_no_modelo']}, "
              f"peso / mediana: {x['peso_relativo']}")


if __name__ == "__main__":
    main()
