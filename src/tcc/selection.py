"""Camada de seleção (Estágio 4 do pipeline; ADR 018).

Converte a saída de qualquer braço num conjunto de bandas comparável entre
métodos. A regra é a do pipeline:

- métodos com seleção explícita (iPLS, CARS, GA-PLS): o conjunto que
  devolvem (`Result.selection`), do tamanho que o método escolheu;
- VIP e portas contínuas: as `k` bandas de maior escore
  (`Result.band_scores`);
- PLS completo e MLP sem porta: sem seleção, `None`, fora das métricas de
  seleção.

Como saber em qual caso cada braço cai: quem tem `band_scores` usa o escore
(VIP, B2, B2', B3, B4 e B5); quem não tem e tem `selection` usa o conjunto
(iPLS, GA-PLS e CARS); quem não tem nenhum dos dois fica de fora. O VIP tem
as duas coisas, e o pipeline manda usar o escore, não o corte por limiar.

Desempate no top-k: entre escores iguais, fica a banda de menor índice. É
determinístico e não depende da ordem interna do `argsort`.

A cardinalidade pareada `k` é a média de bandas retidas pelos métodos
clássicos no conjunto (`paired_k`). De quais execuções ela sai é decisão
do protocolo (ADR 018, Em aberto); a função só faz a conta.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

# Braços clássicos de seleção, cujos tamanhos definem o k pareado. São os
# nomes que os braços dão a si mesmos (`arm.name`) na busca padrão. O CARS
# `fiel` fica de fora: ele existe para o portão contra o artigo, e o que
# entra na comparação com os outros braços é o `protocolo` (ADR 016).
CLASSICAL_SELECTION_ARMS = ("ipls", "vip_threshold", "ga_pls", "cars")


def top_k(scores: np.ndarray, k: int) -> set[int]:
    """As k bandas de maior escore; empate decidido pelo menor índice."""
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 1:
        raise ValueError("escores devem ser um vetor, um por banda")
    p = scores.shape[0]
    if not 1 <= k <= p:
        raise ValueError(f"k = {k} fora de [1, {p}]")
    if np.isnan(scores).any():
        raise ValueError("escore nan: não há ordem definida")
    # lexsort ordena pela última chave primeiro: maior escore, depois menor índice
    order = np.lexsort((np.arange(p), -scores))
    return {int(j) for j in order[:k]}


def to_selection(result, k: int) -> set[int] | None:
    """O conjunto de bandas de um `Result`, pela regra do pipeline."""
    if result.band_scores is not None:
        return top_k(result.band_scores, k)
    if result.selection is not None:
        return set(result.selection)
    return None


def paired_k(results: Iterable, arms: Iterable[str] = CLASSICAL_SELECTION_ARMS) -> int:
    """k pareado: a média, arredondada, de bandas retidas pelos braços clássicos.

    Conta cada `Result` de um braço da lista, em qualquer partição, pelo
    tamanho de `selection`. O arredondamento é o comum (0,5 sobe), para não
    depender do arredondamento bancário do Python.
    """
    arms = set(arms)
    sizes = [len(r.selection) for r in results
             if r.arm_name in arms and r.selection is not None]
    if not sizes:
        raise ValueError("nenhum resultado de braço clássico de seleção")
    return int(np.floor(np.mean(sizes) + 0.5))


def k_grid(k: int, p: int, fractions=(0.5, 0.75, 1.0, 1.25, 1.5)) -> list[int]:
    """Faixa de k da análise de sensibilidade (pipeline: por exemplo ±50%).

    Os valores são arredondados, recortados a [1, p] e sem repetição, em
    ordem crescente.
    """
    if not 1 <= k <= p:
        raise ValueError(f"k = {k} fora de [1, {p}]")
    return sorted({min(p, max(1, int(np.floor(k * f + 0.5)))) for f in fractions})
