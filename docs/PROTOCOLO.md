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

**Proposto ([ADR 009](ADR/009-particao-agrupada-por-amostra-fisica.md)),
já implementado, pendente de aprovação:** partição e folds agrupadas por
amostra física. Tecator, Mango e bioprocess têm réplicas (várias medições
da mesma amostra), que nunca ficam em lados diferentes do treino/teste nem
das folds; o Gasoline não tem evidência de réplicas. O piso de ruído dos 4
conjuntos e a comparação de pré-processamento foram refeitos com a
partição agrupada em 21/09/2026 (seções "Piso de ruído de partição" e
"Pré-processamento"). A tabela original do pré-processamento, calculada
com a partição anterior, fica registrada porque foi com ela que a decisão
foi tomada.

**Em aberto**
- Estratificação por quantil de `y`: sem ela, uma partição azarada pode
  deixar o teste com faixa estreita do alvo.

---

## Validação cruzada interna (decidido)

- 5 folds, geradas por `evaluate` a partir de `seed_split` e injetadas no
  braço via `cv_folds`.
- Nenhum braço constrói as próprias folds.
- Número de componentes latentes do PLS escolhido pela **regra de um
  erro-padrão**, não pelo argmin puro do erro de CV (Hastie, Tibshirani &
  Friedman, *The Elements of Statistical Learning*, 2ª ed., §7.10; mesma
  família do `selectNcomp(method="onesigma")` do pacote R `pls`, usado no
  artigo de referência). Por candidato, calculam-se o RMSE de cada fold, a
  média e o erro-padrão; escolhe-se o **menor** candidato cujo RMSE médio
  fica dentro de um erro-padrão do mínimo — o modelo mais simples ainda
  estatisticamente indistinguível do melhor. Implementada em
  `PLSArm._search`, com teste e verificação por mutação em
  `tests/test_pls.py`; adotada depois de a orientação apontar, em
  14/09/2026, que o seletor usava argmin puro. Foi essa correção que
  reverteu a escolha de pré-processamento (ver "Pré-processamento").

**Parcialmente resolvido ([ADR 011](ADR/011-selecao-por-fold-observavel.md),
28/09/2026).** `FittedArm` passou a expor `cv_selections` — as bandas
escolhidas dentro de cada fold —, e com isso a armadilha central do
Estágio 2 virou verificável: `assert_selection_is_fold_local`, em
`tests/test_selection_leakage.py`, falha se a seleção de um fold mudar
quando as linhas de validação daquele fold são perturbadas. O campo não
entra no `Result`: auditoria de fold é contrato, não métrica.

**Em aberto**
- O caso grosseiro do achado do ADR 001 é detectado (um braço cujo
  `cv_selections` não tem o mesmo comprimento das folds injetadas), mas
  um braço que reconstrua folds equivalentes por conta própria continua
  indetectável, e `cv_selections` é autodeclarado como `n_fits` e
  `rmse_cv`.
- Braços sem seleção de variáveis (`pls_full`, `mlp_full`) devolvem
  `None` e ficam fora dessa auditoria, por não terem o que auditar.

---

## Pré-processamento (decidido com evidência, em vigor desde 28/09/2026)

- **SNV puro** é o pré-processamento do protocolo, e desde 28/09/2026 é o
  default de `evaluate()` — a troca prevista para o início do Estágio 2,
  aprovada pela orientação em 17/09/2026 ("Use SNV puro").
- Decidido: único para todos os braços — comparar braços sob
  pré-processamentos diferentes invalida o benchmark.
- Ajustado apenas em `X_train`, aplicado ao teste.
- `IdentityPreprocessor` continua no código como o nível "sem
  pré-processamento", inclusive para reproduzir números dos Estágios 0 e
  1; não é mais o comportamento padrão.

**Decisão da reunião de 01/09/2026.** Comparar SNV, derivada e a
combinação SNV→derivada empiricamente, e escolher com evidência — a
orientação observou que SNV costuma dar resultados melhores, mas a escolha
não é a priori. Isso mudou o Estágio 1 de "escolher um e registrar" para
"comparar e decidir com evidência".

**Primeira rodada (14/09/2026, seletor de componentes com argmin puro):
SNV→derivada vencia por margem pequena.** A comparação nessa configuração
dava SNV→derivada à frente por pouco, mas com significância no teste
pareado (R² 0,9699 vs. 0,9658, p≈0,01). Essa conclusão **se revelou
artefato** e foi revertida — ver abaixo.

**Causa raiz identificada (17/09/2026).** A vantagem do SNV→derivada não
era um efeito real do pré-processamento: era a instabilidade do argmin
puro na seleção do número de componentes do PLS. O teste pareado estava
aritmeticamente correto, mas comparava dois pré-processamentos **com o
número de componentes escolhido de forma ruidosa por cima** — não dois
pré-processamentos isolados. A derivada provavelmente estabilizava a
curva de RMSECV e, por tabela, a seleção de componentes; corrigido o
seletor (regra de um erro-padrão, ver "Validação cruzada interna"), o
efeito desaparece.

**Escolha final: SNV puro, com evidência empírica no Tecator, seletor de
componentes já com a regra de um erro-padrão** (PLSArm, `seed_split`
0–29, `seed_algo=0`; tabela completa em
`results/preprocessing_comparison_tecator.md`):

| pré-processador | R² média | R² dp | RMSEP média | RMSEP dp |
|---|---|---|---|---|
| **snv** | **0,9689** | **0,0068** | **2,1285** | **0,2782** |
| derivative | 0,9445 | 0,0139 | 2,8361 | 0,3874 |
| snv_derivative | 0,9680 | 0,0068 | 2,1629 | 0,3156 |

Com o seletor corrigido, SNV puro empata ou vence a combinação (ΔR² =
−0,0009, p=0,27 bicaudal no teste pareado; ΔRMSEP p=0,26) — não há
diferença a defender. A derivada sozinha fica nitidamente pior (0,9445),
sugerindo que não agrega informação neste conjunto. Repare também no
desvio-padrão do R² do SNV: caiu de 0,0125 (rodada com argmin puro) para
0,0068 — a regra de um erro-padrão cortou pela metade a variabilidade
entre partições. E, neste conjunto, sem custo: com o SNV, o RMSEP médio
também melhorou (2,2159 → 2,1285) e o R² médio subiu (0,9658 → 0,9689).
A regra troca, em princípio, um pouco de viés por menos variância; aqui
nem houve troca, sinal de que os componentes extras que o argmin escolhia
eram sobreajuste à curva de CV, não informação.

**Refeita com a partição agrupada do ADR 009 (21/09/2026).** A tabela
acima foi calculada com a partição anterior, que deixava réplicas da mesma
amostra caírem em treino e teste. Com a partição agrupada, mesmas
`seed_split` 0–29 (tabela completa em
`results/preprocessing_comparison_tecator.md`):

| pré-processador | R² média | R² dp | RMSEP média | RMSEP dp |
|---|---|---|---|---|
| snv | 0,9686 | 0,0071 | 2,1267 | 0,2861 |
| derivative | 0,9463 | 0,0145 | 2,7676 | 0,3844 |
| snv_derivative | 0,9688 | 0,0076 | 2,1208 | 0,3166 |

O empate continua, agora com a combinação ligeiramente à frente (ΔR² =
+0,0003, p=0,76; ΔRMSEP p=0,83), e a derivada sozinha continua nitidamente
pior. A decisão não muda: sem diferença a defender, a parcimônia decide
por SNV puro.

**Decisão pré-registrada, não descoberta a partir dos resultados.** A
escolha original, SNV→derivada, foi aprovada pela orientação em
14/09/2026; em 17/09/2026 ela foi **revertida** para SNV puro, depois da
correção do seletor de componentes (motivo acima). Tanto a escolha
original quanto a reversão foram registradas **antes** de a grade final
do Estágio 5 rodar, e a evidência de ambas vem exclusivamente das
`seed_split` 0–29 — a faixa exploratória reservada a decisões
metodológicas (ver "Faixas de seed_split"), disjunta das `seed_split` ≥
100 da grade final. Ou seja: o pré-processamento não é conclusão extraída
dos resultados da grade, e nenhuma partição usada nesta decisão reaparece
na avaliação final.

**Não é escolha livre — é parcimônia.** Com ΔR² = −0,0009 e p=0,27 não há
diferença a defender, e nesse caso a parcimônia decide: um passo a menos
no pré-processamento é um fator a menos que um revisor pode questionar.

**Escopo da evidência: decisão de protocolo para os 4 conjuntos, não
resultado por conjunto.** A comparação acima é SÓ do Tecator (NIR). Fixar
SNV a priori para os quatro conjuntos é a opção defensável — mas é
**decisão de protocolo**, não resultado medido nos outros três. Ressalva
registrada pela orientação: o Raman do bioprocess tem características
diferentes do NIR, onde SNV pode não ser a escolha óbvia — a validade da
escolha nesse conjunto segue não medida. A troca de `IdentityPreprocessor`
por `SNVPreprocessor()` como default de `evaluate()` foi feita em
28/09/2026, no início do Estágio 2, como estava previsto.

**O que mudou de número com a troca.** Nada nos resultados versionados. O
piso de ruído e a sonda de vazamento versionada usam o `MeanArm`, que
ignora X por completo, então SNV não altera métrica nenhuma neles
(conferido: `results/permuted_y_tecator.csv` fica idêntico fora do
`wall_time`). A comparação de pré-processamento injeta o candidato
explicitamente e também não depende do default. A sonda com PLS, que usa
X de verdade, muda: R² médio de −0,0474 para −0,0265 nas `seed_split`
0–29, com dp de 0,0849 para 0,1254. O invariante do teste (R² médio ≤ 0)
continua valendo, com margem menor — registrado no docstring de
`test_permuted_y_wrapping_pls_has_no_skill_on_average`.

**Pendência aberta pela troca.** O modo "protocolo da literatura"
(`validation.py`) NÃO aplica SNV: ele reproduz o desenho do artigo, que
usa só Z-score. Isso é deliberado — o portão compara contra os números
publicados, não contra o protocolo deste trabalho —, mas significa que os
dois modos passaram a diferir também no pré-processamento, e não só na
partição. A consequência para o portão do Estágio 2 é que uma diferença
de RMSEP contra a literatura não pode ser atribuída ao pré-processamento
sem essa ressalva.

**Restrição a registrar.** Com o ajuste na posição atual (antes das folds
da CV interna), só pré-processadores por amostra são seguros. SNV é linha
a linha e não vaza; centragem e autoscaling são entre-amostras e
vazariam para a CV interna se aplicados nessa posição.

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

Baseline da média (`MeanArm`), 100 `seed_split` por conjunto, com a
partição agrupada do ADR 009 (Tecator, Mango e bioprocess regenerados em
21/09/2026; Gasoline em 14/09/2026, que não tem réplicas e por isso não
muda; tabelas completas em `results/mean_baseline_<dataset>.md`):

| conjunto | RMSEP média ± dp | dispersão relativa | R² dp | n_test |
|---|---|---|---|---|
| gasoline | 1,4772 ± 0,1750 | ~11,8% | 0,1466 | 15 |
| tecator | 12,6382 ± 0,9755 | ~7,7% | 0,0409 | 54–55 |
| mango | 2,4585 ± 0,0393 | ~1,60% | 0,0023 | 2.923–2.928 |
| bioprocess | 6,2422 ± 0,0782 | ~1,25% | 0,0030 | 1.618–1.620 |

- Nenhum efeito da decomposição menor que o piso do respectivo conjunto é
  interpretável.
- Propriedade verificada por teste automatizado
  (`test_mean_arm_r2_offset_matches_theory`): a média do R² do MeanArm é
  ≈ −1/n_ef em cada conjunto, com n_ef o tamanho efetivo de Kish do teste
  (ADR 009) — nunca 0,000, que indicaria vazamento na métrica (diagnóstico
  da orientação de 27/08).

---

## Margem de equivalência δ (regras fixadas antes do Estágio 7)

- **δ é declarado por conjunto, não como valor único global.** A dispersão
  relativa do piso de ruído varia cerca de 9,5× entre conjuntos
  (bioprocess ~1,25% e mango ~1,60% contra gasoline ~11,8%); um δ global seria
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

## Protocolo da literatura (decidido, [ADR 005](ADR/005-dois-modos-de-protocolo.md), implementado)

- Segundo modo de avaliação, exclusivo do portão de validação contra
  valores publicados (Estágio 2) — nunca entra na grade nem na
  decomposição.
- Divisão fixa 172/43 no Tecator, uniforme para todos os braços validados
  contra a literatura, independente do split de cada artigo original.
- Arquitetura aprovada em 01/09: função separada em `src/tcc/validation.py`
  (`evaluate_against_literature`), tipo de retorno distinto do `Result`
  (`LiteratureResult`), núcleo compartilhado com `evaluate()` via
  `protocol._fit_and_score`. Implementada; `scripts/validate_against_paper.py`
  segue em uso como script de checagem pontual, não mais como substituto.

---

## Decisões em aberto

Referência às perguntas pendentes em `docs/estudo_rodrigo/PERGUNTAS.md`:

| # | Pergunta | Bloqueia |
|---|---|---|
| 1 | Eixo de semente e a H5 — Jaccard deve ser medido no eixo `seed_split`, não `seed_algo` | Congelamento do protocolo |
| 2 | Formato do resumo da revisão dirigida | Não bloqueia o protocolo |
| 3 | Repositório do modelo de referência (B4) | Estágio 3 |
| 4 | ~~Origem de Mango DMC v3 e do conjunto de bioprocesso~~ **Respondida em 17/09/2026.** Mango aceito ([ADR 006](ADR/006-curadoria-do-mango-safras-1-4.md)); bioprocess aprovado com pendência: a aprovação definitiva depende da confirmação da distribuição dos 488 espectros sem glicose ([ADR 007](ADR/007-alvo-do-bioprocess-glicose.md)) | Fechamento do Estágio 1 (ADR 007) |
| 5 | ~~Proveniência do Tecator — faixa do alvo divergente do paper~~ **Resolvida em 03/09** ([ADR 004](ADR/004-proveniencia-do-tecator.md)): fonte confirmada equivalente (OpenML 505 = fda.usc); "7–76%" era erro de prosa | — |
| 6 | Linguagem dos braços clássicos (Python vs. R/`rpy2`) | Estágio 2 |
| 7 | Cálculo do prior dentro da CV interna, como os selecionadores clássicos | Estágio 3 |
| 8 | Semente algorítmica na grade principal — diagonal vs. média sobre réplicas | Estágio 5 |
| 9 | Divisão 48/12 do Gasoline no protocolo da literatura — `train_test_split(test_size=0.2, random_state=42)`, inferida pela reprodução dos números publicados ([ADR 010](ADR/010-divisao-de-literatura-do-gasoline.md), proposto) | Portão de validação do Estágio 2 (ADR 010) |
| 10 | Critério de número de componentes no iPLS — o `mdatools` só oferece argmin e Wold, não a regra de um erro-padrão que o `PLSArm` usa ([ADR 012](ADR/012-ipls-via-mdatools.md), proposto) | Portão de validação do Estágio 2 (ADR 012) |
| 11 | O portão do Estágio 2 é executável como está escrito? Busca preliminar não achou RMSEP publicado de iPLS nem de CARS no Tecator ou no Gasoline — os artigos originais usam cerveja e milho | Critério de aceitação do Estágio 2 |

Das nove, as nº 4 e 5 têm decisão registrada até o momento: ADR 004 e
ADR 006 aceitos; ADR 007 aprovado com pendência (distribuição dos 488). Fora
dessa fila numerada, a Tarefa D — dois modos de protocolo — também já foi
decidida, em reunião de orientação e não por pergunta escrita
([ADR 005](ADR/005-dois-modos-de-protocolo.md)). Onde este documento cita
um item de partição, pré-processamento ou orçamento como "em aberto" sem
apontar para uma pergunta específica, é pendência interna ainda não
formalizada como pergunta à orientação.
