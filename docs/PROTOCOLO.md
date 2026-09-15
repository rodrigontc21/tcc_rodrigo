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

**Decidido: `test_size = 0.25` uniforme nos quatro conjuntos** (confirmado
pela orientação em 14/09/2026). Não se adotam os 20% do artigo de
referência. Justificativa: a uniformidade entre conjuntos vale mais que o
alinhamento com o split do artigo, porque a decomposição soma termos entre
conjuntos e um `n_test` diferente introduziria variação que não é do
método. No Gasoline (n=60) isso dá 45 treino / 15 teste — apertado, mas
nem por isso pior que as 12 amostras de teste do artigo. A comparação com
o valor publicado acontece à parte, no modo "protocolo da literatura"
([ADR 005](ADR/005-dois-modos-de-protocolo.md)), que reproduz ali o split
80/20 daquele artigo; o protocolo principal não se dobra a ele. (Esse modo
hoje só tem divisão definida para o Tecator, 172/43; a do Gasoline entra
quando aquele braço for ao portão de validação, no Estágio 2.)

**Em aberto**
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

## Pré-processamento (decidido com evidência, aplicação adiada para o Estágio 2)

- Hoje: `IdentityPreprocessor` continua em vigor; **SNV→derivada** é a
  escolha registrada para quando o Estágio 2 começar.
- Decidido: único para todos os braços — comparar braços sob
  pré-processamentos diferentes invalida o benchmark.
- Ajustado apenas em `X_train`, aplicado ao teste.

**Decisão da reunião de 01/09/2026.** Comparar SNV, derivada e a
combinação SNV→derivada empiricamente, e escolher com evidência — a
orientação observou que SNV costuma dar resultados melhores, mas a escolha
não é a priori. Isso mudou o Estágio 1 de "escolher um e registrar" para
"comparar e decidir com evidência".

**Escolha: SNV→derivada, com evidência empírica no Tecator** (PLSArm com
busca de componentes por CV interna, `seed_split` 0–29, `seed_algo=0`;
tabela completa em `results/preprocessing_comparison_tecator.md`):

| pré-processador | R² média | R² dp | RMSEP média | RMSEP dp |
|---|---|---|---|---|
| snv | 0,9658 | 0,0125 | 2,2159 | 0,4586 |
| derivative | 0,9477 | 0,0176 | 2,7379 | 0,4671 |
| **snv_derivative** | **0,9699** | **0,0092** | **2,0940** | **0,4038** |

A combinação vence nos quatro indicadores e bate o SNV puro em 21 das 30
partições pareadas (ΔR² médio +0,0041); a margem sobre o SNV é pequena,
mas consistente em direção e com variância menor.

**Decisão pré-registrada, não descoberta a partir dos resultados**
(aprovada pela orientação em 14/09/2026). A escolha de SNV→derivada foi
registrada **antes** de a grade final do Estágio 5 rodar, e a evidência
que a motivou vem exclusivamente das `seed_split` 0–29 — a faixa
exploratória reservada a decisões metodológicas (ver "Faixas de
seed_split"), disjunta das `seed_split` ≥ 100 da grade final. Ou seja: o
pré-processamento não é conclusão extraída dos resultados da grade, e
nenhuma partição usada nesta decisão reaparece na avaliação final. A
orientação aprovou essa sequência em 14/09/2026.

**Escopo da evidência e adiamento deliberado.** A evidência acima é SÓ do
Tecator. Com a aprovação de 14/09/2026, SNV→derivada está confirmada como
a escolha a seguir; a troca de `IdentityPreprocessor` por
`snv_derivative()` como default de `evaluate()` continua adiada para o
início do Estágio 2, e a validade da escolha nos outros três conjuntos
segue não medida — só a do Tecator foi. Até lá, `IdentityPreprocessor`
continua sendo o comportamento real do protocolo — não é regressão, é
decisão deliberada de não aplicar cedo demais.

**Restrição a registrar.** Com o ajuste na posição atual (antes das folds
da CV interna), só pré-processadores por amostra são seguros. SNV e
derivadas são linha a linha e não vazam; centragem e autoscaling são
entre-amostras e vazariam para a CV interna se aplicados nessa posição.
A escolha do método real decide se o contrato de `evaluate` precisa mudar.

**Limitação declarada (plausibilidade química no Tecator).** Gordura e
água são espectralmente quase indistinguíveis no Tecator (correlação
−0,988, ver [ADR 004](ADR/004-proveniencia-do-tecator.md)), então
qualquer "verdade química" para avaliar bandas selecionadas é ambígua
nesse conjunto. Não afeta o Jaccard entre partições (comparação interna),
mas enfraquece a leitura química das bandas — declarado como limitação
desde já.

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

## Piso de ruído de partição (medido nos 4 conjuntos)

Baseline da média (`MeanArm`), 100 `seed_split` por conjunto (Tecator em
28/08/2026, os demais em 14/09/2026; tabelas completas em
`results/mean_baseline_<dataset>.md`):

| conjunto | RMSEP média ± dp | dispersão relativa | R² dp | n_test |
|---|---|---|---|---|
| gasoline | 1,4772 ± 0,1750 | ~11,8% | 0,1466 | 15 |
| tecator | 12,6858 ± 0,9761 | ~7,7% | 0,0382 | 54 |
| mango | 2,4417 ± 0,0231 | ~0,95% | 0,0005 | 3.003 |
| bioprocess | 6,2394 ± 0,0596 | ~0,96% | 0,0012 | 1.618 |

- Nenhum efeito da decomposição menor que o piso do respectivo conjunto é
  interpretável.
- Propriedade verificada por teste automatizado
  (`test_mean_arm_r2_offset_matches_theory`): a média do R² do MeanArm é
  ≈ −1/n_test em cada conjunto — nunca 0,000, que indicaria vazamento na
  métrica (diagnóstico da orientação de 27/08).

---

## Margem de equivalência δ (regras fixadas antes do Estágio 7)

- **δ é declarado por conjunto, não como valor único global.** A dispersão
  relativa do piso de ruído varia mais de 10× entre conjuntos (mango
  ~0,95% e bioprocess ~0,96% contra gasoline ~11,8%); um δ global seria
  frouxo demais nos conjuntos grandes e apertado demais nos pequenos.
- **O piso de ruído medido é um LIMITE INFERIOR empírico para δ, não o
  próprio δ.** δ abaixo do desvio-padrão do RMSEP do MeanArm entre
  partições seria indistinguível de ruído; o δ final também considera o
  custo/benefício prático da equivalência (que diferença importaria a um
  analista?), não só o ruído de partição.
- **Limitação declarada desde já (Estágio 7).** Gasoline tem n=60
  (n_test=15 com o `test_size` atual) — amostra pequena demais para
  sustentar um teste de equivalência (TOST) com poder estatístico útil.
  Registrado como limitação conhecida agora, para não ser descoberto só
  no Estágio 7.

---

## Faixas de seed_split (regra do protocolo, fixada a priori)

Vazamento em nível de protocolo: reutilizar na grade final as mesmas
partições de teste que decidiram uma escolha metodológica contamina a
avaliação — não é vazamento de dados, é reuso de partição entre decisão e
avaliação. Fixação a priori, por ser mais simples e defensível:

- `seed_split` **0–29**: reservadas exclusivamente para decisões
  exploratórias/metodológicas (a comparação SNV vs. SNV→derivada no
  Tecator já usou essa faixa).
- Grade final do Estágio 5: `seed_split` **≥ 100** (faixa disjunta).
  Nenhuma semente usada numa decisão de pré-processamento, seleção de
  features etc. pode reaparecer na avaliação final.
- Regra documental por ora: nenhum default de semente muda em
  `protocol.py`; o executor da grade (Estágio 5) a implementa quando
  existir.

---

## Protocolo da literatura (decidido, [ADR 005](ADR/005-dois-modos-de-protocolo.md), implementação pendente)

- Segundo modo de avaliação, exclusivo do portão de validação contra
  valores publicados (Estágio 2) — nunca entra na grade nem na
  decomposição.
- Divisão fixa 172/43 no Tecator, uniforme para todos os braços validados
  contra a literatura, independente do split de cada artigo original.
- Arquitetura aprovada em 01/09: função separada em `src/tcc/validation.py`,
  tipo de retorno distinto do `Result`, núcleo compartilhado com
  `evaluate()`. Ainda não implementada; até lá,
  `scripts/validate_against_paper.py` é o substituto temporário.

---

## Decisões em aberto

Referência às perguntas pendentes em `docs/estudo_rodrigo/PERGUNTAS.md`:

| # | Pergunta | Bloqueia |
|---|---|---|
| 1 | Eixo de semente e a H5 — Jaccard deve ser medido no eixo `seed_split`, não `seed_algo` | Congelamento do protocolo |
| 2 | Formato do resumo da revisão dirigida | Não bloqueia o protocolo |
| 3 | Repositório do modelo de referência (B4) | Estágio 3 |
| 4 | Origem de Mango DMC v3 e do conjunto de bioprocesso | Estágio 1 (para esses dois conjuntos) |
| 5 | ~~Proveniência do Tecator — faixa do alvo divergente do paper~~ **Resolvida em 03/09** ([ADR 004](ADR/004-proveniencia-do-tecator.md)): fonte confirmada equivalente (OpenML 505 = fda.usc); "7–76%" era erro de prosa | — |
| 6 | Linguagem dos braços clássicos (Python vs. R/`rpy2`) | Estágio 2 |
| 7 | Cálculo do prior dentro da CV interna, como os selecionadores clássicos | Estágio 3 |
| 8 | Semente algorítmica na grade principal — diagonal vs. média sobre réplicas | Estágio 5 |

Das oito, só a nº 5 tem decisão registrada até o momento (ADR 004). Fora
dessa fila numerada, a Tarefa D — dois modos de protocolo — também já foi
decidida, em reunião de orientação e não por pergunta escrita
([ADR 005](ADR/005-dois-modos-de-protocolo.md)). Onde este documento cita
um item de partição, pré-processamento ou orçamento como "em aberto" sem
apontar para uma pergunta específica, é pendência interna ainda não
formalizada como pergunta à orientação.
