"""Conferência da receita de treino configurável (ADR 017, 13/11/2026).

  padrao   roda pelo executor as 660 execuções de rede do Tecator (os 22
           braços de `conferir_executor.py`, `seed_split` 0–29) com o código
           novo, numa pasta nova, e compara pelo hash com a grade gravada
           antes de a receita existir (`results/grade_conferencia/tecator`).
  mango    roda o braço B4-limpo com a receita "até 2.000 épocas, paciência
           2.000" nas `seed_split` 0 a 2 do Mango, com a semente do torch
           em 0, e compara com o laço escrito à mão de
           `diagnosticar_rede_mango.py` (variante "longo"), na mesma semente:
           melhor época e RMSE na fold de parada, em y padronizado. Usa só o
           treino e a fold de parada; o teste não é separado.

Uso: python -B conferir_receita.py padrao|mango
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

PASTA = RAIZ / "results" / "grade_conferencia"


def padrao():
    from conferir_executor import bracos_rede, spec
    from tcc.grid import load_results, result_hash, run_grid

    destino = PASTA / "receita_padrao"
    print(run_grid(spec(bracos_rede()), destino, processes=4, log=lambda *_: None))
    novo = {(r.arm_name, r.seed_split): (result_hash(r), r.hyperparams)
            for r in load_results(destino)}
    antigo = {(r.arm_name, r.seed_split): (result_hash(r), r.hyperparams)
              for r in load_results(PASTA / "tecator") if (r.arm_name, r.seed_split) in novo}
    iguais = sum(novo[k][0] == antigo[k][0] for k in novo)
    print(f"{len(novo)} execuções; predições idênticas à grade de antes da receita: {iguais}")
    # os hiperparâmetros antigos têm de estar todos iguais no novo; o novo só acrescenta
    campos = sum(all(novo[k][1].get(c) == v or (v != v and novo[k][1].get(c) != novo[k][1].get(c))
                     for c, v in antigo[k][1].items()) for k in novo)
    extras = sorted(set(next(iter(novo.values()))[1]) - set(next(iter(antigo.values()))[1]))
    print(f"hiperparâmetros antigos iguais em {campos} de {len(novo)}; campos novos: {extras}")


class SementeZero:
    """Faz o braço usar a semente 0 do torch, a mesma do diagnóstico."""

    def integers(self, n):
        return 0


def mango():
    import numpy as np
    from diagnosticar_rede_mango import treinar, treino_e_parada
    from tcc.arms.base import Budget
    from tcc.arms.gate import TrainRecipe, gate_prior
    from tcc.data import load

    ds = load("mango")
    rec = TrainRecipe(name="longo", max_epochs=2000, patience=2000)
    for s in range(3):
        X, y, folds = treino_e_parada(ds, s)
        best_m, ep_m, _, _, _ = treinar(X, y, folds, "longo", seed=0)
        f = gate_prior(recipe=rec).fit(X, y, folds, SementeZero(), Budget())
        y_std = float(np.ravel(y)[folds[0][0]].std())
        best_b = f.rmse_cv / y_std
        h = f.hyperparams
        print(f"seed_split {s}: laço à mão melhor época {ep_m}, RMSE {best_m:.10f} | "
              f"braço melhor época {h['best_epoch']}, RMSE {best_b:.10f} | "
              f"diferença {abs(best_m - best_b):.1e}; épocas {h['epochs_run']}, "
              f"passos {h['n_steps']}", flush=True)


if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else ""
    if etapa == "padrao":
        padrao()
    elif etapa == "mango":
        mango()
    else:
        sys.exit(__doc__)
