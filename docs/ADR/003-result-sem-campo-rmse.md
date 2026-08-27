# ADR 003 — Result sem campo rmse

**Data:** 2026-08-25
**Status:** aceito

## Contexto

O contrato do Estágio 0 no pipeline lista `r2, rmse, rmsep` no teste
externo. No teste externo, RMSE e RMSEP são a mesma conta sobre os mesmos
dados.

## Decisão

Carregue no `Result` os campos `r2`, `rmsep` e `rmse_cv`. Deixe o campo
`rmse` de fora por redundância; `rmse_cv` ocupa o lugar com significado
distinto — o erro da CV interna, não do teste externo.

## Consequências

Divergência declarada em relação ao contrato do pipeline. Quem comparar
código e documento vai notar a diferença, e este ADR é a justificativa.

Se a orientação preferir aderência literal, acrescentar `rmse` como alias
de `rmsep` é mudança de uma linha.
