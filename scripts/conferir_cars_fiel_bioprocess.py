"""Por que o CARS fiel cai nas partições 10 e 16 do bioprocess? (19/11/2026)

Nas 30 partições piloto do bioprocess, o CARS `fiel` tem R² de 0,129 na
`seed_split` 10 e 0,497 na 16, contra 0,83 a 0,89 nas outras. Aqui roda o
mesmo braço, sem mudança, nessas duas e em duas partições normais (0 e 7),
e grava, para cada uma:

1. o que o braço escolheu (hiperparâmetros) e o RMSECV interno do CARS;
2. se o erro de teste é espalhado ou vem de poucas amostras (os maiores
   resíduos e a fração do erro quadrático que eles levam);
3. a curva do erro de teste contra o número de componentes do modelo
   final, nas mesmas bandas, para ver se o número escolhido é o problema;
4. o mesmo com o modelo autoescalado, como o do modo `protocolo`, para
   ver se o problema é o modelo só centrado.

Conferência: o R² recalculado tem de bater com o do CSV das 30 partições.

Piloto: decisão de método, nada daqui entra no texto. Não muda o braço.

Uso: python -B conferir_cars_fiel_bioprocess.py [processos]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import json
import multiprocessing as mp
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

CSV_30 = RAIZ / "results" / "bracos_bioprocess_30_particoes.csv"
SAIDA = RAIZ / "results" / "conferencia_cars_fiel_bioprocess.json"
PARTICOES = (10, 16, 0, 7)


def uma(s):
    sys.path.insert(0, str(RAIZ / "src"))
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.metrics import r2_score

    from tcc.arms.cars import CARSArm
    from tcc.data import load
    from tcc.preprocessing import SNVPreprocessor
    from tcc.protocol import evaluate

    class Gravador(CARSArm):
        """O mesmo braço; só guarda o treino que recebeu."""

        def fit(self, X_train, y_train, cv_folds, rng_algo, budget):
            self.X_train, self.y_train = X_train, y_train
            return super().fit(X_train, y_train, cv_folds, rng_algo, budget)

    ds = load("bioprocess", drop_artifact_bands=False)
    braco = Gravador(mode="fiel")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = evaluate(braco, ds, seed_split=s, seed_algo=0)

    X_te = SNVPreprocessor().fit(ds.X[r.test_idx]).transform(ds.X[r.test_idx])
    y_te = ds.y[r.test_idx]
    res = y_te - r.y_pred
    ordem = np.argsort(-np.abs(res))
    sq = res ** 2

    cols = np.sort(np.fromiter(r.selection, dtype=int))
    Xtr, ytr = braco.X_train[:, cols], braco.y_train
    curva_centrado, curva_escalado = {}, {}
    teto = int(r.hyperparams["ncomp_ceiling"])
    for h in range(1, min(teto, len(cols)) + 1):
        for escala, curva in ((False, curva_centrado), (True, curva_escalado)):
            m = PLSRegression(n_components=h, scale=escala).fit(Xtr, ytr)
            p = np.asarray(m.predict(X_te[:, cols])).ravel()
            curva[h] = round(float(r2_score(y_te, p)), 4)

    return {
        "seed_split": s,
        "r2": r.r2,
        "rmsep": r.rmsep,
        "hyperparams": r.hyperparams,
        "n_teste": int(len(y_te)),
        "y_teste_faixa": [float(y_te.min()), float(y_te.max())],
        "maiores_residuos": [
            {"linha": int(r.test_idx[i]), "y": float(y_te[i]), "pred": float(r.y_pred[i])}
            for i in ordem[:5]
        ],
        "fracao_erro_5_maiores": float(sq[ordem[:5]].sum() / sq.sum()),
        "fracao_erro_1pct_maiores": float(
            sq[ordem[: max(1, len(sq) // 100)]].sum() / sq.sum()
        ),
        "r2_por_ncomp_centrado": curva_centrado,
        "r2_por_ncomp_autoescalado": curva_escalado,
    }


def main():
    processos = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    with open(CSV_30, encoding="utf-8") as f:
        antes = {int(l["seed_split"]): float(l["r2"])
                 for l in csv.DictReader(f) if l["braco"] == "cars_fiel"}
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        linhas = list(ex.map(uma, PARTICOES))
    for l in linhas:
        if abs(l["r2"] - antes[l["seed_split"]]) > 1e-6:
            sys.exit(f"R² não bate na partição {l['seed_split']}: "
                     f"{l['r2']:.6f} contra {antes[l['seed_split']]:.6f}")
    print("conferência: R² igual ao CSV nas", len(linhas), "partições")
    SAIDA.write_text(json.dumps(linhas, indent=1, ensure_ascii=False), encoding="utf-8")
    for l in linhas:
        h = l["hyperparams"]
        print(f"\nseed {l['seed_split']}: R² {l['r2']:.4f}  bandas {h['n_bands']}  "
              f"ncomp {h['n_components']} (teto {h['ncomp_ceiling']}, A1 {h['a1_ncomp']})  "
              f"RMSECV CARS {h['cars_rmsecv']:.4f}  RMSEP {l['rmsep']:.4f}  "
              f"melhor execução {h['cars_best_run']}")
        print(f"  5 maiores resíduos levam {l['fracao_erro_5_maiores']:.1%} do erro "
              f"(1% maiores: {l['fracao_erro_1pct_maiores']:.1%}); y teste "
              f"{l['y_teste_faixa'][0]:.2f} a {l['y_teste_faixa'][1]:.2f}")
        for m in l["maiores_residuos"][:3]:
            print(f"    linha {m['linha']}: y {m['y']:.3f}  previsto {m['pred']:.3f}")
        print("  R² por ncomp, centrado:   ", l["r2_por_ncomp_centrado"])
        print("  R² por ncomp, autoescalado:", l["r2_por_ncomp_autoescalado"])
    print("\ngravado em", SAIDA)


if __name__ == "__main__":
    main()
