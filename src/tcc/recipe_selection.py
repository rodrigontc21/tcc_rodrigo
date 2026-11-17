"""Escolha da receita de treino das redes, por conjunto (PROTOCOLO; ADR 017).

A receita é, para a rede, o que o H* é para o PLS: um parâmetro escolhido
por conjunto, por um procedimento declarado, na validação interna, sem
olhar o teste (orientação, 16/11/2026). Este módulo só tem a regra; quem
roda os treinos e junta os números é `scripts/escolher_receita.py`.

**Candidatos** (`CANDIDATES`), todos em lote único: uma época é um passo
do otimizador, e o orçamento de passos é o objeto da tese, então a forma do
otimizador não muda entre conjuntos, só os valores. O primeiro é a receita
do artigo (`ARTICLE`). Mini-lote só entraria se nenhum candidato de lote
único fosse admissível, e então nos quatro conjuntos, como mudança
declarada no objeto da tese, não por este módulo.

**Admissibilidade**, declarada antes de rodar. Um candidato é admissível
num conjunto se:
1. a faixa de `d_s / g_s` do B4-limpo nas partições (maior sobre menor)
   não passa de `MAX_DSG_RANGE`. Nos três conjuntos em que a receita do
   artigo funciona, a faixa foi de 1,5 a 3,4 vezes; no Mango, 67 vezes,
   que é a assinatura do treino quebrado;
2. nenhum treino tem a melhor época dentro da janela da paciência
   (`best_epoch <= patience`): o treino nunca saiu da fase inicial.

**Escolha:** entre os admissíveis, o de menor RMSE médio na fold de parada
define o limite de um erro-padrão (erro-padrão entre partições); fica o
candidato **mais barato** dentro do limite. Mais barato é o menor orçamento
de épocas; no empate, a menor paciência; no empate, a taxa do artigo. É a
mesma regra de um erro-padrão do H* do PLS.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from tcc.arms.gate import ARTICLE, TrainRecipe

MAX_DSG_RANGE = 5.0


def _recipe(lr: float, max_epochs: int, patience: int) -> TrainRecipe:
    if (lr, max_epochs, patience) == (ARTICLE.lr, ARTICLE.max_epochs, ARTICLE.patience):
        return ARTICLE  # o nome do braço continua sem sufixo
    return TrainRecipe(name=f"lr{lr:g}_e{max_epochs}_p{patience}", lr=lr,
                       max_epochs=max_epochs, patience=patience)


# Orçamentos de 200 (o do artigo) a 2.000 épocas, com a paciência em 10% do
# orçamento e no mínimo 30 (a do artigo); a taxa do artigo e uma cerca de três
# vezes menor, porque em treino longo a de 0,01 ficou instável no Mango
# (DIARIO de 12/11). Oito candidatos.
BUDGETS = ((200, 30), (500, 50), (1000, 100), (2000, 200))
RATES = (0.01, 0.003)
CANDIDATES = tuple(_recipe(lr, e, p) for lr in RATES for e, p in BUDGETS)


def cost_key(recipe: TrainRecipe) -> tuple:
    """Ordem de custo: orçamento de épocas, paciência, e a taxa do artigo antes."""
    return (recipe.max_epochs, recipe.patience, recipe.lr != ARTICLE.lr, recipe.lr)


@dataclass(frozen=True)
class CandidateResult:
    """O que a escolha usa de um candidato num conjunto, das `seed_split` piloto.

    `stop_rmse[s]`: RMSE na fold de parada, na melhor época, médio sobre os
    braços de rede rodados na partição `s`. `dsg`: `d_s / g_s` do B4-limpo,
    um por partição. `best_epochs`: a melhor época de cada treino rodado.
    """

    stop_rmse: Sequence[float]
    dsg: Sequence[float]
    best_epochs: Sequence[int]


def admissible(recipe: TrainRecipe, result: CandidateResult,
               max_dsg_range: float = MAX_DSG_RANGE) -> tuple[bool, list[str]]:
    """Se o candidato passa nos dois filtros, e por que não, se não passa."""
    reasons = []
    dsg = np.asarray(result.dsg, dtype=float)
    if dsg.size == 0 or np.any(~np.isfinite(dsg)) or np.any(dsg <= 0):
        reasons.append("d_s / g_s ausente, não finito ou não positivo")
    elif dsg.max() / dsg.min() > max_dsg_range:
        reasons.append(f"faixa de d_s / g_s {dsg.max() / dsg.min():.1f}× > {max_dsg_range:g}×")
    early = int(np.sum(np.asarray(result.best_epochs) <= recipe.patience))
    if early:
        reasons.append(f"{early} treino(s) com a melhor época dentro da paciência "
                       f"({recipe.patience})")
    return not reasons, reasons


def choose(results: Mapping[TrainRecipe, CandidateResult],
           max_dsg_range: float = MAX_DSG_RANGE) -> dict:
    """Aplica os filtros e a regra de um erro-padrão. Devolve a receita
    escolhida (ou None, se nenhum candidato for admissível) e a tabela."""
    table = {}
    for recipe, res in results.items():
        ok, reasons = admissible(recipe, res, max_dsg_range)
        r = np.asarray(res.stop_rmse, dtype=float)
        if r.size < 2:
            raise ValueError("são precisas pelo menos duas partições")
        table[recipe] = {"admissible": ok, "reasons": reasons, "mean": float(r.mean()),
                         "se": float(r.std(ddof=1) / np.sqrt(r.size))}
    ok = [rc for rc in table if table[rc]["admissible"]]
    if not ok:
        return {"chosen": None, "table": table, "limit": None}
    best = min(ok, key=lambda rc: table[rc]["mean"])
    limit = table[best]["mean"] + table[best]["se"]
    within = [rc for rc in ok if table[rc]["mean"] <= limit]
    return {"chosen": min(within, key=cost_key), "table": table, "limit": limit}
