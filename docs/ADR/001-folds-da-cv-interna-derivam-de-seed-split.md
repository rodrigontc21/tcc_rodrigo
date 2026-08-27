# ADR 001 — Folds da CV interna derivam de seed_split

**Data:** 2026-08-25
**Status:** aceito

## Contexto

O trabalho tem dois eixos de semente. `seed_split` controla a partição
treino/teste; `seed_algo` controla a aleatoriedade interna do método. O
pipeline chama essa separação de "a decisão de projeto mais importante do
trabalho e a mais fácil de errar". Restava decidir de qual eixo derivam as
folds da validação cruzada interna.

## Decisão

Derive as folds de `seed_split`. Gere-as em `evaluate` e injete-as em
`Arm.fit`; o braço nunca constrói as próprias folds.

## Consequências

Variar `seed_algo` com `seed_split` fixo mede instabilidade algorítmica
pura, sem contaminação por mudança de folds. Todos os braços ensaiam sobre
exatamente as mesmas folds sob a mesma `seed_split`.

Em contrapartida, nada no contrato obriga o braço a de fato usar as folds
injetadas — um braço que chame `cross_val_score(cv=5)` do sklearn usaria
splits próprios sem detecção, porque as folds não aparecem no `Result`.
Achado registrado, a resolver no Estágio 2.
