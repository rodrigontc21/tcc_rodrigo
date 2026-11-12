# Protocolo de avaliação

## Status

**Provisório.** O congelamento espera a aprovação da mudança de desenho do
parecer de 01/10 (pergunta 14). Até lá, qualquer item marcado como
"decidido" reflete o que já está implementado e pode ainda mudar; qualquer item marcado como "em aberto" ou "provisório" é pendência
declarada, não descuido.

Depois de congelado, qualquer mudança exige declaração explícita e
justificativa. Motivo padrão de pré-registro: ajustar o protocolo depois
de ver resultados invalida os testes de equivalência (TOST) e as
hipóteses pré-registradas H1–H7 da proposta, e a H8 proposta depois do
parecer de 01/10 (seção "Hipóteses e braços").

**12/11/2026:** a orientação respondeu à maior parte da pergunta 14 e listou
o que falta antes do congelamento: o rótulo de piloto nos braços, a frase
do poder discriminante na seção do δ, os ajustes nos ADRs 009 e 013, a
grade de `c` declarada com o valor do TOST por conjunto e a varredura de
`c` refeita sob este protocolo. A grade e a regra do `c` do TOST foram
declaradas em 12/11; falta medir o `c` do TOST de cada conjunto. "Faça a lista acima e mande o protocolo
para congelamento."

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

**Regra de réplicas do Tecator corrigida (09/11/2026), por decisão da
orientação.** A regra original só juntava linhas vizinhas; a corrigida
junta, sempre com alvos idênticos, vizinhas, espectros idênticos ou
espectros próximos (max |dx| < 0,30), em componentes conexas. Os grupos do
Tecator vão de 208 a 180, e o piso de ruído, a comparação de
pré-processamento e a sonda de y permutado do Tecator foram regenerados em
10/11/2026. Detalhes no adendo do ADR 009, que continua proposto: a
orientação decidiu a correção, não o ADR.

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
- **Adendo (28/10/2026) — o teto da busca. Decisão minha, ainda não vista
  pela orientação.** Os candidatos vão de 1 a `MAX_COMPONENTS`, recortado
  pelo posto do bloco de treino. O teto era 20 e não estava declarado em
  lugar nenhum além do código. No Mango ele limitava a escolha: com teto 20
  a regra escolhia exatamente 20 (RMSECV 1,034); com teto 40 escolhe 32
  (RMSECV 0,919). Passou a **40**, acima do maior H\* medido. O `PLSArm`
  agora avisa (`RuntimeWarning`) quando a escolha cai no teto, para o
  mesmo problema não passar calado em outro conjunto; o aviso tem teste,
  conferido por mutação. Consequência: o `n_fits` do PLS completo muda (no
  Tecator, 101 → 201), e as razões de custo medidas com o teto antigo
  precisam ser refeitas.

**As réplicas do Tecator na CV interna (medido em 10/11; leitura da
orientação em 12/11).** Com a partição fixa em cada `seed_split` 0–29 e as
réplicas espalhadas por folds diferentes, o RMSECV ficou mais otimista em
27 de 30 (mediana −0,066, cerca de 3%; p < 0,001), o H\* do PLS mudou em 15
de 30 (no pior caso, de 3 para 14) e o R² de teste não se moveu (p = 0,73;
ADR 009, adendo de 10/11). Duas declarações:
- **Achado:** no Tecator, a superfície de desempenho do PLS é plana em H em
  volta do ótimo, e por isso escolher outro H não custa R² de teste. Um
  seletor que vai de 3 para 14 componentes escolheu outro modelo; não
  sofreu só uma perturbação. Nada garante a mesma planura em outro
  conjunto.
- **Não medido:** o efeito desse mesmo erro interno nos braços que o usam
  para escolher bandas, onde o erro de seleção muda o que entra no modelo
  em vez de se diluir num hiperparâmetro.

O defeito corrompia a escolha do modelo e deixava o desempenho no teste
intacto, o modo de falha invisível a quem olha só R². Por isso a medida do
lado do teste (+0,001 no PLS, 05/11) não podia decidir a correção de 09/11.

**Parcialmente resolvido em código, com o ADR ainda `proposto`
([ADR 011](ADR/011-selecao-por-fold-observavel.md), 28/09/2026).**
`FittedArm` passou a expor `cv_selections` — as bandas escolhidas dentro
de cada fold —, e com isso a armadilha central do Estágio 2 virou
verificável: `assert_selection_is_fold_local`, em
`tests/test_selection_leakage.py`, falha se a seleção de um fold mudar
quando as linhas de validação daquele fold são perturbadas. O campo não
entra no `Result`: auditoria de fold é contrato, não métrica.

Ressalva de status, para esta subseção não ser lida como decidida: o
ADR 011 **não foi aprovado pela orientação** — o código está implementado
e testado, e a aprovação é pendente, como nos ADRs 008, 009, 010 e 012.
O cabeçalho "(decidido)" desta seção vale para as folds derivarem de
`seed_split`, que é o ADR 001, aceito.

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

**Refeita com a regra de réplicas de 09/11/2026 (ADR 009).** A partição
agrupada deixava 20 dos 22 pares de espectros idênticos do Tecator em
grupos diferentes. Com a regra corrigida (180 grupos em vez de 208), as
mesmas `seed_split` 0–29 dão (`results/preprocessing_comparison_tecator.md`):

| pré-processador | R² média | R² dp | RMSEP média | RMSEP dp |
|---|---|---|---|---|
| snv | 0,9664 | 0,0083 | 2,1918 | 0,3053 |
| derivative | 0,9393 | 0,0173 | 2,9339 | 0,4159 |
| snv_derivative | 0,9660 | 0,0058 | 2,2147 | 0,2517 |

O empate continua, agora com o SNV ligeiramente à frente: ΔR²
(SNV→derivada − SNV) = −0,0004, p=0,64 no teste t pareado; ΔRMSEP
+0,023, p=0,46. A derivada sozinha continua nitidamente pior, e a
decisão pelo SNV puro não muda.

**O sinal do efeito (frase da orientação, 12/11).** O sinal do ΔR² entre SNV
e SNV→derivada já inverteu três vezes entre configurações de partição: a
combinação à frente com o argmin, a combinação à frente com o ADR 009, e
o SNV à frente com a regra de réplicas de 09/11. Um efeito cujo sinal
depende da partição é a melhor evidência possível de que não existe. É
isso, mais que qualquer p, que sustenta a escolha do SNV.
- **O teste:** o p da tabela anterior não saía de nenhum script; o teste
  t pareado reproduz os dois valores (0,76 e 0,83) com o arquivo antigo,
  e foi o usado aqui.
- **O teto de componentes:** esta rodada já usa o teto de 40 do PLS
  (adendo de 28/10). Com teto 20 e a regra nova, o SNV dá o mesmo 0,9664
  e o SNV→derivada, 0,9661. A mudança em relação à tabela anterior vem
  da regra de réplicas, e não do teto.

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

**O custo é resultado (orientação, 30/10/2026).** O `n_fits` e o
`wall_time` de cada braço entram no trabalho como resultado, na figura de
custo computacional por braço do pipeline (escala log), e não só como
obstáculo. Nenhuma redução de sementes ou partições é feita em silêncio.
Qualquer corte, por custo ou por outro motivo, entra declarado, com o
motivo, antes de rodar.

---

## Piso de ruído de partição (medido nos 4 conjuntos)

Baseline da média (`MeanArm`), 100 `seed_split` por conjunto, com a
partição agrupada do ADR 009 (Mango e bioprocess regenerados em
21/09/2026; Tecator de novo em 10/11/2026, com a regra de réplicas de
09/11; Gasoline em 14/09/2026, que não tem réplicas e por isso não muda;
tabelas completas em `results/mean_baseline_<dataset>.md`):

| conjunto | RMSEP média ± dp | dispersão relativa | R² dp | n_test |
|---|---|---|---|---|
| gasoline | 1,4772 ± 0,1750 | ~11,8% | 0,1466 | 15 |
| tecator | 12,6753 ± 1,1288 | ~8,9% | 0,0517 | 54–57 |
| mango | 2,4585 ± 0,0393 | ~1,60% | 0,0023 | 2.923–2.928 |
| bioprocess | 6,2422 ± 0,0782 | ~1,25% | 0,0030 | 1.618–1.620 |

- Nenhum efeito da decomposição menor que o piso do respectivo conjunto é
  interpretável.
- **O Tecator antes de 09/11:** com a regra antiga (208 grupos), o piso
  era 12,6382 ± 0,9755 (~7,7%, R² dp 0,0409, n_test 54–55). Com grupos
  de até 4 amostras, o tamanho do teste passa a variar de 54 a 57 (81 das
  100 partições com 54), e o piso sobe para ~8,9%.
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
- **O limite inferior do Tecator foi redeclarado em 12/11/2026,** antes da
  grade: com a regra de réplicas de 09/11, o piso passou de ~7,7% para
  ~8,9% do RMSEP, cerca de 15% acima.
- **Poder discriminante, como propriedade do desenho (declarado em
  12/11/2026, antes da grade).** No Tecator, o piso de partição de ~8,9% do
  RMSEP fica acima das diferenças entre braços: no piloto, convertidas em
  RMSEP, elas foram de cerca de −1,6% (iPLS) a +3,0% (CARS `fiel`), na
  conta da orientação. Qualquer δ honesto nesse conjunto
  tende a declarar os braços equivalentes, não porque sejam iguais, mas
  porque o conjunto não tem resolução para separá-los. Somado à limitação
  do Gasoline (n = 60, piso ~11,8%), **o poder de distinguir os braços
  deste trabalho está no Mango e no bioprocess** (pisos de ~1,60% e
  ~1,25%). Equivalência declarada no Tecator e no Gasoline deve ser lida
  com essa ressalva.

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
- **Os braços clássicos rodados em 0–29 são piloto** (Tecator, Gasoline e
  Mango, 10 a 12/11/2026; ADRs 012 a 016): nenhum desses números entra no
  texto como resultado, e nada deste protocolo muda com base neles. Os
  cinco Wilcoxon contra o PLS completo são piloto e por isso não levam
  correção de multiplicidade; "não se distingue do PLS" no Wilcoxon não é
  equivalência, que é o TOST com δ, na grade.
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

## Hipóteses e braços: ajustes depois do parecer de 01/10/2026 (proposto)

**Status: proposto.** Nada aqui foi aprovado pela orientação. É a
transcrição, para o protocolo, das três consequências de desenho do parecer
de 01/10, com as escolhas que o parecer deixa em aberto declaradas como
proposta. Precisa estar fixado antes da grade, como o próprio parecer exige.

**Por quê.** As verificações de 29–30/09 mostraram que a porta do PGSG fica
imóvel no topo por construção: a cadeia min-max → `clip` → logit põe a
banda campeã 11,5 logits à frente da segunda, e o treino declarado move um
logit no máximo de 1,45 a 1,92 (Tecator, 10 sementes,
`results/verificacao_3b_secao_5_2.md`). **Correção (04/11):** esse
deslocamento é, na maior parte, encolhimento dos logits pelo decaimento de
peso do `train_light.py`, que incide também sobre a porta. Com a porta
isenta de L2, o maior deslocamento cai para cerca de 0,3 (medido pela
orientação em 30/10 e repetido aqui; mesmo relatório, seção "O mecanismo").
O topo é ainda mais imóvel do que o número anterior sugeria. No Gasoline
(medido em 05/11), o encolhimento é só cerca de metade: o maior
deslocamento cai de 1,34 para 0,66 com a porta isenta, e o topo continua
imóvel (distância de 12,2). O parecer conclui que o termo
"aprendizado da porta" pode ser nulo por construção, e que a tarefa do
trabalho passa a ser medir isso com rigor.

**Terminologia (04/11, a pedido da orientação em 30/10).** Neste protocolo,
"saturação" quer dizer só o efeito do `clip` sobre o prior: o máximo do
prior, que vale 1 pela normalização min-max, vira logit 16,12. Isso põe a
banda campeã 11,5 logits à frente da segunda e concentra a porta inicial
numa banda só. **Não quer dizer gradiente atenuado.** No softmax com
temperatura, a derivada no topo, `g(1 − g)/τ`, vale cerca de 0,034 (g =
0,215, τ = 5), mais que numa banda típica. Gradiente atenuado por
`s(1 − s)` é a história da porta sigmoide, de outro modelo. O que trava o
topo é a distância de 11,5 logits contra o passo do Adam. "Saturação
removida", abaixo, quer dizer essa distância desfeita.

**As hipóteses pré-registradas H1–H7 da proposta** (`docs/fontes/tcc_rodrigo.pdf`,
Seção 5) ficam como estão. O ajuste é este:

- **H8 (nova; ajustada em 04/11, a pedido da orientação em 30/10).**
  Δ_aprendizado = R²(B4-limpo) − R²(B2) é estatisticamente equivalente a
  zero pela margem δ declarada, por TOST, como H2–H4. Mesma direção
  deflacionária de H1–H4. A proposta não tinha hipótese para esse termo: o
  H4 é outro, a porta contra a melhor seleção clássica.

  **O Δ não identifica o mecanismo.** Há três caminhos para Δ ≈ 0
  ([ADR 013](ADR/013-ancora-do-portao-do-estagio-2.md), seção "O que o Δ
  mede"):
  - **(a)** a porta não anda o bastante: o topo está a 11,5 logits da
    segunda banda, contra o passo do Adam;
  - **(b)** a porta anda e o MLP absorve, porque a porta é uma reescala das
    colunas da primeira camada;
  - **(c)** o que se move é encolhimento L2 dos logits em direção ao
    uniforme, que não é aprendizado nem trava.

  A H8 é reportada sempre com as medidas que separam os três, todas no
  B4-limpo:
  - o deslocamento θ_final − θ_inicial por banda (maior e mediana do valor
    absoluto), e a correlação desse vetor entre sementes;
  - a fração de bandas cujo |θ| diminuiu;
  - a correlação entre o deslocamento e −θ_inicial.
- **H5 e H6, reinterpretadas, não retiradas.** Com o topo imóvel, Jaccard
  alto da porta é, nas palavras do parecer, "o esperado de modelos que
  partem da mesma inicialização", e **não é, sozinho, evidência de seleção
  robusta** ("a métrica continua válida; o que muda é o que ela permite
  concluir"). Uma ressalva de medida: entre folds a inicialização é de fato
  a mesma (o prior é calculado uma vez sobre o treino); entre partições o
  prior é recalculado em cada treino, e o quanto ele varia de uma partição
  para outra ainda não foi medido — é a primeira coisa a medir no piloto.
  O mesmo raciocínio vale para a H6: a vantagem do B4 sobre o B3 em
  reprodutibilidade pode vir da saturação do prior, e não de aprendizado. A
  leitura de H5 e H6 passa a exigir a comparação com o B5, abaixo: só a
  reprodutibilidade que sobrevive com a saturação removida conta a favor da
  porta. O parecer cita só a H5; a extensão à H6 é inferência deste
  trabalho, a confirmar com a orientação.

**Os braços neurais, com o desdobramento do B4** ([ADR 013](ADR/013-ancora-do-portao-do-estagio-2.md),
seções "O braço B4" e "O que o Δ mede", aceito em 04/11):

| braço | ponderação | porta treinável | inicialização da porta |
|---|:---:|:---:|---|
| B1 | não | — | — |
| B2 | sim | não | **a porta inicial do PGSG**, `softmax(logit(clip(s))/τ)` — não o prior bruto |
| B3 | sim | sim | uniforme |
| B4-fiel | sim | sim | a porta inicial do PGSG, treino com o protocolo declarado, **com** decaimento de peso na porta, como no `train_light.py` |
| B4-limpo | sim | sim | a porta inicial do PGSG, treino com o protocolo declarado, porta **isenta** de decaimento |
| **B5 (novo)** | sim | sim | **porta inicial corrigida**, sem a saturação |
| **B2' (novo, proposta deste trabalho)** | sim | não | a mesma porta corrigida do B5, congelada |

O B2 é a "porta na inicialização" do parecer, e o B4 é o "PGSG treinado".
"Protocolo declarado" quer dizer os hiperparâmetros do artigo (lr 0,01,
200 épocas, paciência 30, KL 0,001), com a parada antecipada observando uma
fold de validação interna — nunca o teste, como o `train_light.py` do
artigo faz. Vale para B2, B3, B4, B5 e B2', com o mesmo orçamento.
"Mesmo orçamento" quer dizer a mesma regra de parada, e não o mesmo número
de épocas: com menos parâmetros no otimizador, os braços congelados podem
parar em outra época (ADR 013).

**Decaimento de peso e os dois B4 (proposta de 04/11, a partir da mensagem
da orientação de 30/10).** O `train_light.py` aplica `weight_decay=1e-4` a
todos os parâmetros, inclusive aos logits da porta. Na porta, isso puxa os
logits para zero, isto é, a porta para o uniforme. Medido no Tecator, isso
é a maior parte do movimento da porta no treino do artigo
(`results/verificacao_3b_secao_5_2.md`, seção "O mecanismo"). Isentar a
porta não custou desempenho: R² de teste 0,913 e 0,941, contra 0,922 e
0,922 com o decaimento em tudo, mediana de 10 sementes, água e gordura.

Como o B2 congelado não sofre esse encolhimento, um B4 com decaimento na
porta mistura o encolhimento no Δ. São duas perguntas, e o protocolo tem os
dois braços, como a orientação sugeriu:

- **B4-fiel**: decaimento 1e-4 em todos os parâmetros, como no artigo. Serve
  para comparar contra o artigo (o critério "B4 reproduz o braço de
  referência" e a âncora do ADR 013). O Δ calculado com ele inclui o
  encolhimento, e isso é declarado sempre que ele aparece.
- **B4-limpo**: decaimento 1e-4 só no MLP, com a porta isenta. É o braço da
  H8, e o Δ calculado com ele mede o gradiente na porta sem o encolhimento.

Onde este protocolo diz só "B4" (H6, `R²(B5) − R²(B4)`), vale o
B4-limpo, salvo na comparação contra o artigo, que usa o B4-fiel.

O MLP tem decaimento 1e-4 em todos os braços. **Em aberto:** a mesma
questão vale para os outros braços de porta treinável. No B5 e no B3, o
decaimento na porta também puxa para o uniforme, e no B3 isso é puxar de
volta para a própria inicialização. A proposta é que eles usem a porta
isenta, como o B4-limpo, porque é o B4-limpo que eles acompanham nas
comparações. Fica a confirmar com a orientação, perguntada em 29/10 para o
B5 e o B2', sem resposta ainda.

**Respondido em 12/11/2026: B3 e B5 com a porta isenta.** A orientação
concorda, com um motivo de desenho, mais forte que "acompanham o B4-limpo":
- **O L2 na porta é um regularizador duplicado e não declarado.** O
  regularizador declarado da porta é o termo KL, com λ, que a ancora no
  prior. O `weight_decay` nos logits é um segundo regularizador, que puxa
  para o uniforme, na direção contrária. Isentar a porta não retira
  regularização: retira a duplicada e fica com a declarada.
- **O L2 nem é a mesma coisa entre braços:** no B4 ele briga com o KL; no
  B3, cuja porta começa uniforme, vira penalidade sobre afastar-se do
  uniforme, exatamente o que o B3 existe para medir.

Duas explicitações, que não são mudança:
- **No B3 o KL não é inerte** (ao contrário do B2) e ancora no uniforme,
  onde a porta começa: o B3 é "porta ancorada no uniforme", com o λ do
  protocolo, e não "porta livre". Porta livre exigiria λ = 0, outro braço,
  que não entra agora.
- **Em cada braço de porta treinável, reportar se isentar a porta custou
  desempenho.**
O B5 é o braço que o parecer pede para "medir se a porta aprende alguma
coisa quando o mecanismo de saturação é removido".

O **B2'** não está no parecer: é acréscimo deste trabalho, pela regra do
Estágio 3 de que dois braços comparados diferem numa característica só.
Sem ele, B5 − B2 mistura duas mudanças, a correção da porta e o gradiente.
Com ele, `Δ_aprendizado,corrigido = R²(B5) − R²(B2')` isola o gradiente com
a saturação removida, e `R²(B5) − R²(B4)` mede o efeito da correção em si.
Fica proposto, a confirmar com a orientação (pergunta 14).

**A correção do B5 (proposta).** O parecer oferece três: escalar os logits,
não recortar no extremo, ou usar a temperatura. Proposta deste trabalho:
**escalar os logits iniciais** por um fator `c < 1`, porque ataca a causa
direta — a distância entre o 1º e o 2º logit, 11,5, contra os ~2 que o
treino alcança. Critério proposto para `c`: a distância inicial entre os dois
primeiros logits fica na ordem do deslocamento medido do treino declarado.
O valor de `c` é fixado antes da grade, no conjunto de exploração
(`seed_split` 0–29), nunca olhando o desempenho no teste. Escolha e valor
vão à orientação (pergunta 14).

**Atenção (04/11): esse critério foi escrito sobre o deslocamento com
decaimento na porta.** Os "~2 que o treino alcança" são, na maior parte,
encolhimento L2. Com a porta isenta, o maior deslocamento é de cerca de
0,3. Com o critério como está escrito, `c` sai de um número que muda cerca de
seis vezes conforme o decaimento na porta (Tecator; no Gasoline, cerca de
duas vezes, de 1,34 para 0,66, medido em 05/11). O critério precisa dizer em qual
dos dois deslocamentos se baseia, de forma coerente com a escolha do
decaimento para o B5 (em aberto, acima). Fica para a pergunta 14.

**Resposta da orientação sobre o `c` (12/11/2026).** O critério se baseia no
deslocamento **com a porta isenta**, por conjunto. A orientação rodou uma
varredura de `c` (`verify_b5_logit_scale.py`; Tecator e Gasoline, 10
sementes, receita do artigo, porta isenta) e mediu duas coisas:
- **O critério não é circular:** o maior deslocamento quase não depende de
  `c` (0,25 a 0,36 no Tecator, 0,46 a 0,59 no Gasoline), porque o passo do
  Adam é normalizado. Dá para fixar `c` pela medida em `c` = 1: cerca de
  0,026 no Tecator e 0,04 a 0,05 no Gasoline.
- **O critério é necessário, não suficiente:** com o topo alcançável, a
  banda do topo não trocou em nenhuma semente, em nenhum `c` > 0, e o Δ
  continuou nulo. E no `c` que torna o topo alcançável, a massa da porta
  no topo fica quase uniforme: ou a porta carrega o prior como
  distribuição, ou o topo é móvel, não as duas.

**Decisão da orientação: `c` vira um eixo varrido, com grade declarada.**
O B5 vira uma família B5(c), com `c` = 1 recuperando o B4-limpo e `c` → 0
tendendo ao B3. Restrições de pré-registro:
- a grade de `c` é declarada antes de rodar (declarada abaixo, em 12/11);
- **um** valor por conjunto é o do TOST: o do critério com a porta isenta;
  o resto da curva é contexto, não escolha a posteriori.

**A grade de `c` (declarada em 12/11/2026, antes de qualquer execução do
B5 sob este protocolo).**
- **Grade fixa, a mesma em todo conjunto em que o B5 roda:** a da
  orientação, `c` ∈ {1; 0,5; 0,3; 0,17; 0,10; 0,054; 0,026; 0}. Cada valor
  é cerca de metade do anterior, de modo que a curva cobre do saturado
  (`c` = 1, o B4-limpo) ao uniforme (`c` = 0).
- **Mais um valor por conjunto, o `c` do TOST,** calculado pelo critério
  com a porta isenta: `c_TOST` = mediana, nas `seed_split` 0–29 com
  `seed_algo` 0, de `d_s / g_s`, calculada partição a partição, onde
  - `d_s` é o maior deslocamento |θ_final − θ_inicial| dos logits da porta
    no treino com `c` = 1 e porta isenta (o B4-limpo), sob este protocolo
    (partição agrupada, folds internas, parada pela fold interna), na
    partição `s`;
  - `g_s` é a distância inicial entre o 1º e o 2º logit da porta em `c` = 1
    na mesma partição, que muda com ela porque o prior é recalculado em
    cada treino.

  *(Forma fixada em 12/11, antes de medir: a primeira redação falava em
  "mediana" de `d` sem dizer como `g`, que varia com a partição, entrava.)*
- **O `c_TOST` só usa o deslocamento da porta, nunca o desempenho no
  teste.** Ele é calculado e escrito neste protocolo antes de rodar a
  varredura; se coincidir com um valor da grade até a terceira casa, não
  se acrescenta nada.
- **O `c` = 0 deste protocolo não é o B3.** Em B5(0) a porta começa
  uniforme, mas o KL continua ancorado no prior; no B3 o KL ancora no
  uniforme. B5(0) é reportado como ponto da curva, e o B3 continua um
  braço próprio.
- **Referência da orientação, piloto:** pela conta dela, `c_TOST` ≈ 0,026
  no Tecator (já na grade) e ≈ 0,04 a 0,05 no Gasoline (fora da grade).
  Esses valores não entram aqui: o protocolo usa os medidos sob ele.

**Os `c_TOST` medidos (12/11/2026, antes da varredura)** com
`scripts/medir_c_tost.py` (`results/c_tost.csv`; B4-limpo, `seed_split`
0–29, `seed_algo` 0, sem olhar o teste):

| conjunto | `d` mediano | `g` mediano | **`c_TOST`** = mediana de `d_s / g_s` | faixa de `d_s / g_s` | o topo trocou |
|---|---|---|---|---|---|
| Tecator | 0,351 | 11,67 | **0,0306** | 0,0178 a 0,0453 | 0 de 30 |
| Gasoline | 0,462 | 16,01 | **0,0289** | 0,0172 a 0,0590 | 0 de 30 |
| Mango | 0,486 | 11,50 | **0,0417** | 0,0008 a 0,0559 | 0 de 30 |
| bioprocess | 1,603 | 14,15 | **0,1140** | 0,0859 a 0,1326 | 0 de 30 |

Nenhum coincide com um valor da grade até a terceira casa, então **cada
conjunto roda a grade fixa mais o seu `c_TOST`**, e é esse o valor do TOST
daquele conjunto.

**Ressalva do Mango:** em 7 das 30 partições, a melhor época no conjunto
de parada foi cedo (1, 1, 2, 10, 14, 16 e 18); nas duas primeiras, a rede
piorou logo depois do primeiro passo e não voltou dentro da paciência.
Nelas a porta quase não treinou, e o `d_s / g_s` fica perto de zero. A
mediana já absorve isso, e a regra não muda depois de medir. Mas a receita
do artigo (lr 0,01, lote único, paciência 30) foi feita para 172 amostras,
e no Mango a parada às vezes corta o treino na primeira época. É questão de
desenho, observada só no treino, e vai à orientação.

**Atualização de 12/11, depois da varredura (piloto):** no Mango, a receita
falha também no teste (R² de rede em torno de 0,5, contra 0,86 do PLS
completo; ADR 017, item 7). **O `c_TOST` do Mango fica suspenso** até a
orientação decidir sobre a receita de treino nesse conjunto.

Os números da orientação são piloto (parada olhando o teste, partição
172/43 fixa, e o `c` = 0 dela não é o B3 deste protocolo). **A varredura
precisa ser refeita sob este protocolo** antes de qualquer coisa ir para o
texto.

---

## Decisões em aberto

Referência às perguntas pendentes em `docs/estudo_rodrigo/PERGUNTAS.md`:

| # | Pergunta | Bloqueia |
|---|---|---|
| 1 | Eixo de semente e a H5 — Jaccard deve ser medido no eixo `seed_split`, não `seed_algo` | Congelamento do protocolo |
| 2 | Formato do resumo da revisão dirigida | Não bloqueia o protocolo |
| 3 | Repositório do modelo de referência (B4). **Adendo de 27/10/2026:** respondida na prática — a orientação cedeu o código-fonte do artigo em 29/09 (`docs/fontes/prior-guided-spectral-gating-main/`, fora do versionamento); falta a vendorização com SHA-256 que o pipeline pede | Estágio 3 |
| 4 | ~~Origem de Mango DMC v3 e do conjunto de bioprocesso~~ **Respondida em 17/09/2026.** Mango aceito ([ADR 006](ADR/006-curadoria-do-mango-safras-1-4.md)); bioprocess aprovado com pendência: a aprovação definitiva depende da confirmação da distribuição dos 488 espectros sem glicose ([ADR 007](ADR/007-alvo-do-bioprocess-glicose.md)) | Fechamento do Estágio 1 (ADR 007) |
| 5 | ~~Proveniência do Tecator — faixa do alvo divergente do paper~~ **Resolvida em 03/09** ([ADR 004](ADR/004-proveniencia-do-tecator.md)): fonte confirmada equivalente (OpenML 505 = fda.usc); "7–76%" era erro de prosa. **Adendo de 30/09/2026:** a conclusão sobre o paper caiu — os resultados publicados do Tecator foram calculados sobre a água (achado aceito pela orientação em 29/09; ver o adendo de 30/09 no ADR 004). A decisão para este trabalho não muda | — |
| 6 | Linguagem dos braços clássicos (Python vs. R/`rpy2`) | Estágio 2 |
| 7 | Cálculo do prior dentro da CV interna, como os selecionadores clássicos | Estágio 3 |
| 8 | Semente algorítmica na grade principal — diagonal vs. média sobre réplicas | Estágio 5 |
| 9 | Divisão 48/12 do Gasoline no protocolo da literatura — `train_test_split(test_size=0.2, random_state=42)`, inferida pela reprodução dos números publicados ([ADR 010](ADR/010-divisao-de-literatura-do-gasoline.md), proposto) | Portão de validação do Estágio 2 (ADR 010) |
| 10 | Critério de componentes DENTRO da busca de intervalos do iPLS — o `mdatools` decide por intervalo pelo `ncomp.selcrit`, e trocá-lo muda a seleção; o `glob.ncomp` da nossa regra é só teto ([ADR 012](ADR/012-ipls-via-mdatools.md), proposto) | Portão de validação do Estágio 2 (ADR 012) |
| 11 | O portão do Estágio 2 é executável como está escrito? Busca preliminar não achou RMSEP publicado de iPLS nem de CARS no Tecator ou no Gasoline — os artigos originais usam cerveja e milho | Critério de aceitação do Estágio 2 |
| 12 | Critério de escolha do número de intervalos do iPLS — a regra em vigor fica com o menor `int.num`, que retém MAIS bandas: a parcimônia está invertida ([ADR 012](ADR/012-ipls-via-mdatools.md), proposto) | Estágio 2 (ADR 012) |
| 13 | Escalonamento na seleção de intervalos — o mdatools pontua sem autoescalonamento e o PLS final autoescala; Jaccard médio de 0,63 entre as duas configurações, o que atinge a H5 ([ADR 012](ADR/012-ipls-via-mdatools.md), proposto) | Estágio 2 e leitura da H5 |
| 14 | Os ajustes do parecer de 01/10 (seção "Hipóteses e braços", acima): a H8 nova; a correção do B5 — escalar os logits, com o critério para `c`, que precisa dizer em qual deslocamento se baseia (com ou sem decaimento na porta); a porta isenta de decaimento no B3 e no B5, como no B4-limpo; o braço B2', acréscimo deste trabalho; e a extensão da reinterpretação à H6. **Respondida em 12/11/2026:** porta isenta no B3 e no B5, aceita; critério do `c` pela porta isenta, por conjunto, com `c` como eixo varrido. Sobre o resto, nas palavras dela: "ela fica reduzida ao B2' e à extensão da reinterpretação à H6, que eu confirmo também: a extensão à H6 é sua inferência e está correta". Grade de `c` declarada em 12/11 (a da orientação, mais o `c_TOST` de cada conjunto pela regra da seção "A grade de `c`"). **Falta:** medir o `c_TOST` de cada conjunto sob este protocolo, escrevê-lo aqui antes da varredura, e refazer a varredura | Congelamento do protocolo e Estágio 3 |

Das catorze, as nº 4 e 5 têm decisão registrada até o momento: ADR 004 e
ADR 006 aceitos; ADR 007 aprovado com pendência (distribuição dos 488). Fora
dessa fila numerada, a Tarefa D — dois modos de protocolo — também já foi
decidida, em reunião de orientação e não por pergunta escrita
([ADR 005](ADR/005-dois-modos-de-protocolo.md)). Onde este documento cita
um item de partição, pré-processamento ou orçamento como "em aberto" sem
apontar para uma pergunta específica, é pendência interna ainda não
formalizada como pergunta à orientação.
