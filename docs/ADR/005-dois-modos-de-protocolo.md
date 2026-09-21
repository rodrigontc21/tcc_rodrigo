# ADR 005 — Dois modos de protocolo (Tarefa D)

**Data:** 2026-09-01
**Status:** aceito, implementado (2026-09-14)

## Contexto

O Estágio 2 vai exigir validar CARS e GA-PLS contra valores publicados na
literatura, que usam divisão fixa do conjunto (não partição aleatória
repetida) — no Tecator, 172 treino / 43 teste. O protocolo único do
Estágio 0 (`evaluate()`, partição aleatória via `seed_split`) não serve a
esse propósito, mas não pode ser substituído por ele — os dois usos
coexistem: `evaluate()` continua servindo à grade e à decomposição, e um
segundo modo serve exclusivamente ao portão de validação contra a
literatura.

## Decisão

Aprovada em reunião de orientação (01/09/2026): segunda função, em arquivo
separado (`src/tcc/validation.py`), com tipo de retorno distinto do
`Result` de `evaluate()` — para ficar estruturalmente impossível ela
entrar sem querer na grade principal. As duas compartilham o núcleo comum
(particionamento, ajuste do braço) por dentro, sem duplicar lógica.

Divisão fixa de 172/43 aprovada para uso uniforme em todos os braços
validados contra a literatura no Tecator — independente de qual split cada
artigo original (CARS, GA-PLS) individualmente usou.

## Consequências

O executor da grade (Estágio 5) importa só `evaluate()`; a função de
validação não tem `seed_split` na assinatura e devolve outro tipo, então
não encaixa nos eixos da grade nem na decomposição — a proteção é
estrutural, não disciplinar. `scripts/validate_against_paper.py` segue em
uso como checagem pontual, fina camada sobre
`evaluate_against_literature`, e não como implementação temporária a ser
substituída. Implementado em 14/09/2026 em
`src/tcc/validation.py` (`evaluate_against_literature`), com o núcleo
compartilhado com `evaluate()` via `protocol._fit_and_score` e testes em
`tests/test_validation.py`.
