"""A borda do iPLS no Mango: a curva de erro também é plana? (22/11/2026)

`conferir_causa_borda_ipls.py` mostrou, no Tecator e no Gasoline, que o
iPLS cai em `int_num` = 10 (a borda de baixo da grade) porque a curva do
erro de validação é plana: com a regra de um erro-padrão, a escolha vai
para o menor candidato dentro do limite. O Mango ficou de fora porque o
iPLS leva ~18 min por partição nele. Aqui, o mesmo teste no Mango, nas
`seed_split` 0 a 29: o braço roda sem mudança, só com dois candidatos a
mais embaixo (5 e 8), gravando o erro médio e o erro-padrão de cada
candidato. Daí:

1. a escolha e o mínimo na grade declarada {10, ..., 30};
2. a escolha e o mínimo na grade alargada {5, 8, 10, ..., 30}.

Conferência: o laço e a regra são os de `conferir_causa_borda_ipls.py`
(já conferidos contra o braço em 60 partições). Além disso, nas partições
em que a grade alargada escolhe o mesmo `int_num` que a declarada, o modelo
final é o mesmo da rodada de produção, e o R² tem de bater com
`results/bracos_mango_30_particoes.csv`. Se não bater, o script para.

Piloto: decisão de método, nada daqui entra no texto. Não muda o braço.

Uso: python -B conferir_causa_borda_ipls_mango.py [processos]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import multiprocessing as mp
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

PRODUCAO = RAIZ / "results" / "bracos_mango_30_particoes.csv"
SAIDA = RAIZ / "results" / "conferencia_causa_borda_ipls_mango.csv"


def uma(s):
    sys.path.insert(0, str(RAIZ / "src"))
    sys.path.insert(0, str(RAIZ / "scripts"))
    import warnings

    import numpy as np

    from conferir_causa_borda_ipls import ACRESCIMOS, _regra
    from tcc.arms.ipls import DEFAULT_INT_NUM_CANDIDATES, IPLSArm, _fit_pls
    from tcc.data import load
    from tcc.protocol import evaluate

    class Gravador(IPLSArm):
        """O mesmo laço de `conferir_causa_borda_ipls.py`."""

        def _search(self, X_train, y_train, cv_folds, glob_ncomp, budget):
            medias, eps, por_cand = [], [], []
            for int_num in self._candidates:
                sel = self._fold_selections(
                    X_train, y_train, cv_folds, int_num, glob_ncomp, budget
                )
                rmses = []
                for (ft, fv), bandas in zip(cv_folds, sel):
                    model, cols, _ = _fit_pls(X_train[ft], y_train[ft], bandas, glob_ncomp)
                    budget.increment()
                    y_hat = np.asarray(model.predict(X_train[fv][:, cols])).ravel()
                    rmses.append(float(np.sqrt(np.mean((y_train[fv] - y_hat) ** 2))))
                rmses = np.asarray(rmses)
                medias.append(rmses.mean())
                eps.append(rmses.std(ddof=1) / np.sqrt(len(rmses)))
                por_cand.append(sel)
            self.medias, self.eps = np.asarray(medias), np.asarray(eps)
            escolhido, _ = _regra(self.medias, self.eps, self._candidates)
            i = self._candidates.index(escolhido)
            return escolhido, float(self.medias[i]), por_cand[i]

    grade = tuple(DEFAULT_INT_NUM_CANDIDATES)
    larga = tuple(sorted(set(ACRESCIMOS) | set(grade)))
    braco = Gravador(candidates=larga)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = evaluate(braco, load("mango"), seed_split=s, seed_algo=0)

    idx = [larga.index(c) for c in grade]
    esc_dec, min_dec = _regra(braco.medias[idx], braco.eps[idx], grade)
    esc_larga, min_larga = _regra(braco.medias, braco.eps, larga)
    linha = {"conjunto": "mango", "seed_split": s,
             "escolha_declarada": esc_dec, "minimo_declarada": min_dec,
             "escolha_alargada": esc_larga, "minimo_alargada": min_larga,
             "r2_alargada": f"{r.r2:.6f}"}
    for c, m, e in zip(larga, braco.medias, braco.eps):
        linha[f"rmse_{c}"] = f"{m:.6g}"
        linha[f"ep_{c}"] = f"{e:.6g}"
    return linha


def main():
    processos = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    with open(PRODUCAO, encoding="utf-8") as f:
        r2_prod = {int(l["seed_split"]): float(l["r2"])
                   for l in csv.DictReader(f) if l["braco"] == "ipls"}
    t0 = time.time()
    linhas = []
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        futuros = [ex.submit(uma, s) for s in range(30)]
        for fu in as_completed(futuros):
            l = fu.result()
            linhas.append(l)
            print(f"[{(time.time() - t0) / 60:6.1f} min] seed {l['seed_split']:2d}: "
                  f"declarada {l['escolha_declarada']} (mín {l['minimo_declarada']}), "
                  f"alargada {l['escolha_alargada']} (mín {l['minimo_alargada']})", flush=True)
    linhas.sort(key=lambda l: l["seed_split"])

    iguais = [l for l in linhas if l["escolha_alargada"] == l["escolha_declarada"]]
    diferentes = [(l["seed_split"], l["r2_alargada"], r2_prod[l["seed_split"]])
                  for l in iguais
                  if abs(float(l["r2_alargada"]) - r2_prod[l["seed_split"]]) > 1e-6]

    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    print("gravado em", SAIDA)

    if diferentes:
        sys.exit(f"R² não bate com a produção nas partições de mesma escolha: {diferentes}")
    print(f"conferência: R² igual à produção nas {len(iguais)} partições em que as "
          f"duas grades escolhem o mesmo int_num")

    no10 = [l for l in linhas if l["escolha_declarada"] == 10]
    print(f"\nmango: escolha 10 na grade declarada em {len(no10)} de {len(linhas)}")
    print("  escolha na declarada (todas):",
          dict(sorted(Counter(l["escolha_declarada"] for l in linhas).items())))
    print("  mínimo na declarada (todas):",
          dict(sorted(Counter(l["minimo_declarada"] for l in linhas).items())))
    print("  grade alargada, mínimo (todas):",
          dict(sorted(Counter(l["minimo_alargada"] for l in linhas).items())))
    print("  grade alargada, escolha (todas):",
          dict(sorted(Counter(l["escolha_alargada"] for l in linhas).items())))


if __name__ == "__main__":
    main()
