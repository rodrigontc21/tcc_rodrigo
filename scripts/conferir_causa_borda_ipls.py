"""A borda do iPLS vem da grade ou da direção do desempate? (17/11/2026)

`conferir_borda_ipls.py` mostrou o iPLS escolhendo `int_num` = 10, o menor
candidato de {10, 15, 20, 25, 30}, em 20 de 30 partições do Tecator e 24 de
30 do Gasoline. Com o que o braço grava não dá para separar duas causas:

- **grade:** o erro de validação continua caindo abaixo de 10, ou seja, o
  ótimo está fora da grade;
- **desempate:** o mínimo está acima de 10, e o 10 só é escolhido porque a
  regra de um erro-padrão fica com o MENOR `int_num` dentro do limite.

Aqui o braço roda sem mudança nenhuma, só com dois candidatos a mais
embaixo (5 e 8) e gravando o erro médio e o erro-padrão de cada candidato.
Daí saem as duas respostas:

1. na grade declarada, onde está o mínimo quando a escolha foi 10;
2. na grade alargada, se o mínimo cai em 5 ou 8.

Conferência: aplicada só aos candidatos da grade declarada, a regra
reproduzida aqui precisa escolher o mesmo `int_num` que
`results/conferencia_borda_ipls.csv` gravou. Se não escolher, o script
para.

Piloto: decisão de método, nada daqui entra no texto. Não muda o braço.

Uso: python -B conferir_causa_borda_ipls.py [processos]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import multiprocessing as mp
import sys
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

ANTES = RAIZ / "results" / "conferencia_borda_ipls.csv"
SAIDA = RAIZ / "results" / "conferencia_causa_borda_ipls.csv"
ACRESCIMOS = (5, 8)


def _regra(medias, eps, candidatos):
    """A regra de um erro-padrão do `IPLSArm._search`, sobre um subconjunto
    dos candidatos (em ordem crescente)."""
    i_min = int(np.argmin(medias))
    limite = medias[i_min] + eps[i_min]
    return candidatos[int(np.argmax(medias <= limite))], candidatos[i_min]


def uma(tarefa):
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.arms.ipls import DEFAULT_INT_NUM_CANDIDATES, IPLSArm, _fit_pls
    from tcc.data import load
    from tcc.protocol import evaluate

    class Gravador(IPLSArm):
        """O mesmo braço, com o laço do `_search` repetido para gravar o
        erro de cada candidato. A regra de escolha é a do braço."""

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

    conjunto, s = tarefa
    grade = tuple(DEFAULT_INT_NUM_CANDIDATES)
    larga = tuple(sorted(set(ACRESCIMOS) | set(grade)))
    braco = Gravador(candidates=larga)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        evaluate(braco, load(conjunto), seed_split=s, seed_algo=0)

    idx = [larga.index(c) for c in grade]
    esc_dec, min_dec = _regra(braco.medias[idx], braco.eps[idx], grade)
    esc_larga, min_larga = _regra(braco.medias, braco.eps, larga)
    linha = {"conjunto": conjunto, "seed_split": s,
             "escolha_declarada": esc_dec, "minimo_declarada": min_dec,
             "escolha_alargada": esc_larga, "minimo_alargada": min_larga}
    for c, m, e in zip(larga, braco.medias, braco.eps):
        linha[f"rmse_{c}"] = f"{m:.6g}"
        linha[f"ep_{c}"] = f"{e:.6g}"
    return linha


def main():
    processos = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    with open(ANTES, encoding="utf-8") as f:
        antes = {(l["conjunto"], int(l["seed_split"])): int(l["int_num"])
                 for l in csv.DictReader(f)}
    tarefas = sorted(antes)
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        linhas = list(ex.map(uma, tarefas))

    diferentes = [(l["conjunto"], l["seed_split"], l["escolha_declarada"],
                   antes[(l["conjunto"], l["seed_split"])])
                  for l in linhas
                  if l["escolha_declarada"] != antes[(l["conjunto"], l["seed_split"])]]
    if diferentes:
        sys.exit(f"a regra reproduzida não bate com a rodada anterior: {diferentes}")
    print("conferência: a escolha na grade declarada bate nas", len(linhas), "partições")

    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)

    for c in ("tecator", "gasoline"):
        ls = [l for l in linhas if l["conjunto"] == c]
        no10 = [l for l in ls if l["escolha_declarada"] == 10]
        print(f"\n{c}: escolha 10 na grade declarada em {len(no10)} de {len(ls)}")
        print("  onde estava o mínimo nesses casos:",
              dict(sorted(Counter(l["minimo_declarada"] for l in no10).items())))
        print("  grade alargada, mínimo (todas):",
              dict(sorted(Counter(l["minimo_alargada"] for l in ls).items())))
        print("  grade alargada, escolha (todas):",
              dict(sorted(Counter(l["escolha_alargada"] for l in ls).items())))
    print("\ngravado em", SAIDA)


if __name__ == "__main__":
    main()
