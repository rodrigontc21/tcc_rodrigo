# ADR 002 — rmse_cv é propriedade de FittedArm

**Data:** 2026-08-25
**Status:** aceito

## Contexto

O `Result` precisa carregar o erro da validação cruzada interna, mas cada
braço conduz sua busca de hiperparâmetro de forma própria (o PLS escolhe
componentes latentes; o CARS, iterações de eliminação). Para `evaluate`
calcular esse valor, teria de replicar a lógica de cada método.

## Decisão

Exponha `rmse_cv` como propriedade de `FittedArm`. O braço reporta o erro
que obteve internamente; `evaluate` apenas o repassa ao `Result`.

## Consequências

`evaluate` não conhece detalhes internos de nenhum braço. Braços sem busca
de hiperparâmetro retornam `nan` — sinaliza "não se aplica" mantendo o tipo
`float`.

O valor é autodeclarado, então um braço que reporte errado não é detectável
de fora; mesma classe de problema do `n_fits`.
