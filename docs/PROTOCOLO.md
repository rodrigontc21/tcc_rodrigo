# Protocolo de avaliação

## Status

**Provisório.** Congela na semana 11 (~27/10/2026). Até lá, qualquer item
marcado como "decidido" reflete o que já está implementado e pode ainda
mudar; qualquer item marcado como "em aberto" ou "provisório" é pendência
declarada, não descuido.

Depois de congelado, qualquer mudança exige declaração explícita e
justificativa. Motivo padrão de pré-registro: ajustar o protocolo depois
de ver resultados invalida os testes de equivalência (TOST) e as
hipóteses pré-registradas H1–H7 da proposta.

---

## Eixos de semente (decidido, [ADR 001](ADR/001-folds-da-cv-interna-derivam-de-seed-split.md))

- `seed_split` controla a partição treino/teste e as folds da CV interna.
- `seed_algo` controla apenas a aleatoriedade interna do braço.
- Os dois derivam de fontes independentes (`SeedSequence(seed_split).spawn(2)`
  para partição e folds; `seed_algo` alimenta um gerador à parte). O braço
  nunca recebe `seed_split`.

**Justificativa.** Variar `seed_algo` com `seed_split` fixo mede
instabilidade algorítmica pura, sem contaminação por mudança de folds.

---

## Partição (provisório)

- `test_size = 0.25`, sem estratificação.

**Em aberto**
- O paper de referência usa 20%; com o Gasoline (n=60), 25% deixa só 15
  amostras de teste e o R² fica instável.
- Estratificação por quantil de `y`: sem ela, uma partição azarada pode
  deixar o teste com faixa estreita do alvo.

---

## Validação cruzada interna (decidido)

- 5 folds, geradas por `evaluate` a partir de `seed_split` e injetadas no
  braço via `cv_folds`.
- Nenhum braço constrói as próprias folds.

**Em aberto**
- As folds não são observáveis no `Result`, então nada detecta um braço
  que use CV própria em vez das folds injetadas.

---

## Pré-processamento (em aberto, Estágio 1)

- Hoje: `IdentityPreprocessor`, placeholder sem efeito.
- Decidido para quando o método real entrar: único para todos os braços —
  comparar braços sob pré-processamentos diferentes invalida o benchmark.
- Ajustado apenas em `X_train`, aplicado ao teste.

**Restrição a registrar.** Com o ajuste na posição atual (antes das folds
da CV interna), só pré-processadores por amostra são seguros. SNV e
derivadas são linha a linha e não vazam; centragem e autoscaling são
entre-amostras e vazariam para a CV interna se aplicados nessa posição.
A escolha do método real decide se o contrato de `evaluate` precisa mudar.

---

## Métricas (decidido, [ADR 003](ADR/003-result-sem-campo-rmse.md))

- `rmsep` — erro no teste externo, unidades originais.
- `rmse_cv` — erro da CV interna, propriedade do braço
  ([ADR 002](ADR/002-rmse-cv-e-propriedade-de-fittedarm.md)).
- `r2` — no teste externo.
- O campo `rmse` do contrato do pipeline foi omitido por redundância com
  `rmsep`.

---

## Orçamento (decidido, com limitação)

- `n_fits` contado por `Budget`, incrementado pelo próprio braço.
- `wall_time` medido em `evaluate`, cobrindo `fit` + `predict`.

**Limitação conhecida.** `n_fits` é autodeclarado, não verificável de
fora — um braço que reporte errado não é detectável pelo protocolo.

---

## Piso de ruído de partição (medido em 28/08/2026)

- Tecator, baseline da média (`MeanArm`), 100 `seed_split`: desvio-padrão
  do R² = 0,0382; desvio-padrão do RMSEP = 0,9761.
- Nenhum efeito da decomposição menor que esse piso é interpretável.
- É a âncora empírica da margem δ do TOST, que até aqui não tinha
  critério objetivo.

**Pendente.** Medir o mesmo piso nos outros três conjuntos: Gasoline
(Estágio 1), Mango e bioprocesso (dependem da pergunta nº 4 de
`estudo_rodrigo/PERGUNTAS.md`).

---

## Decisões em aberto

Referência às perguntas pendentes em `docs/estudo_rodrigo/PERGUNTAS.md`:

| # | Pergunta | Bloqueia |
|---|---|---|
| 1 | Eixo de semente e a H5 — Jaccard deve ser medido no eixo `seed_split`, não `seed_algo` | Congelamento do protocolo |
| 2 | Formato do resumo da revisão dirigida | Não bloqueia o protocolo |
| 3 | Repositório do modelo de referência (B4) | Estágio 3 |
| 4 | Origem de Mango DMC v3 e do conjunto de bioprocesso | Estágio 1 (para esses dois conjuntos) |
| 5 | Proveniência do Tecator — faixa do alvo divergente do paper | Estágio 1 (camada de dados) |
| 6 | Linguagem dos braços clássicos (Python vs. R/`rpy2`) | Estágio 2 |
| 7 | Cálculo do prior dentro da CV interna, como os selecionadores clássicos | Estágio 3 |
| 8 | Semente algorítmica na grade principal — diagonal vs. média sobre réplicas | Estágio 5 |

Nenhuma dessas oito tem decisão registrada até o momento. Onde este
documento cita um item de partição, pré-processamento ou orçamento como
"em aberto" sem apontar para uma pergunta específica, é pendência interna
ainda não formalizada como pergunta à orientação.
