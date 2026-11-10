# ADR 009 — Partição agrupada por amostra física

**Data:** 2026-09-18
**Status:** proposto

## Contexto

Ao revisar a análise dos 488 espectros sem glicose do ADR 007 (18/09),
apareceu uma estrutura que o protocolo não tratava: no bioprocess, linhas
vizinhas com os 8 alvos idênticos ocorrem muito acima do acaso, ou seja,
há várias medições da mesma amostra física. O catálogo do `raman-data`
marca o conjunto como agrupado (`is_grouped`), mas não expõe a qual
amostra cada espectro pertence.

O diagnóstico foi estendido aos quatro conjuntos, comparando a frequência
de alvos idênticos em linhas vizinhas com a de pares de linhas sorteados:

- **Tecator**: 7 pares de linhas vizinhas com (fat, water, protein)
  idênticos — 3,3% dos vizinhos, contra 0,17% ao acaso —, 2 deles com
  espectro também idêntico (linhas duplicadas). Repetições em linhas
  distantes são compatíveis com coincidência, porque os alvos têm uma casa
  decimal.
- **Gasoline**: 1,7% dos vizinhos repetem a octanagem, contra 1,2% ao
  acaso — sem evidência de réplicas.
- **Mango**: 48% dos vizinhos repetem o DM (5 casas decimais), contra
  0,02% ao acaso. Repetições de DM em linhas distantes trazem os mesmos
  metadados (Season, Region, Date, Type, Cultivar, Pop) em 738 de 749
  casos: são o mesmo fruto. Em geral há 2 leituras por fruto, e até 6.
- **Bioprocess**: 5.089 blocos de linhas vizinhas idênticas, mas só 3.433
  composições distintas — a mesma composição reaparece em linhas
  distantes. Depois do descarte dos espectros sem glicose (ADR 007), toda
  amostra tem 2 ou mais espectros.

`evaluate()` sorteava treino, teste e folds da CV interna espectro a
espectro. Uma réplica podia cair no treino e outra da mesma amostra no
teste: o modelo recebia a resposta de graça, e o R² de qualquer braço
ficava inflado. Pelo mesmo motivo, o piso de ruído estava subestimado.

## Decisão

Regra de protocolo, uniforme para todos os conjuntos: réplicas da mesma
amostra física nunca ficam em lados diferentes — nem entre treino e
teste, nem entre folds da CV interna. O `Dataset` ganha o campo `groups`,
com o identificador de amostra de cada linha, ou `None` quando não há
evidência de réplicas.

A identificação da amostra é feita por conjunto, na camada de dados, com
base na evidência acima: Tecator por linhas vizinhas com os três alvos
idênticos; Gasoline sem grupos; Mango por DM idêntico com os mesmos
metadados; bioprocess pela composição dos 8 alvos.

Algoritmo: cada grupo é representado por uma linha fixa; a ordem dos
grupos vem da posição desse representante na permutação sorteada a
partir de `seed_split`; teste e folds são preenchidos com grupos
inteiros, nessa ordem, até o tamanho-alvo. Com grupos unitários a
partição é idêntica à anterior, e todo grupo tem a mesma chance de ir ao
teste, qualquer que seja o tamanho.

## Consequências

Implementado em `src/tcc/protocol.py` (partição e folds), `src/tcc/data.py`
(`groups` em cada loader) e `src/tcc/validation.py` (folds internas do
modo "protocolo da literatura"; a divisão 172/43 do artigo continua fixa,
e nenhum par de réplicas do Tecator atravessa essa fronteira). Testes
cobrem: nenhum grupo atravessa treino/teste nos três conjuntos com
réplicas; nenhum grupo atravessa folds; grupos unitários reproduzem a
partição antiga; ausência de viés por tamanho de grupo. A primeira versão
do algoritmo ordenava os grupos pela primeira aparição de qualquer membro,
o que favorecia grupos grandes (no Mango, frutos com 6 leituras ocupavam
54% do teste, contra 32% do conjunto); o teste de teoria do R² detectou o
desvio, e a versão final o corrige.

O tamanho do teste pode passar do alvo em até o tamanho de um grupo menos
um: Tecator 54 a 55 (alvo 54), Mango 2.923 a 2.928 (alvo 2.923),
bioprocess 1.618 a 1.620 (alvo 1.618).

O diagnóstico de vazamento na métrica muda de forma: para o `MeanArm`, a
média do R² é ≈ −1/n_ef, com n_ef o tamanho efetivo de Kish do teste, e
não −1/n_test. Com o split antigo, a teoria "por linhas" parecia bater
porque o vazamento correlacionava as médias de treino e teste.

Os números que o `PROTOCOLO.md` registrava tinham sido calculados com a
partição anterior. Com a partição agrupada:

- Piso de ruído (dispersão relativa do RMSEP do `MeanArm`, 100
  `seed_split`): Mango de 0,95% para 1,60%, bioprocess de 0,96% para
  1,25%; Tecator praticamente igual (7,7%); Gasoline não muda. A
  diferença entre conjuntos citada na seção da margem δ cai de cerca de
  12,5× (0,95% contra 11,8%) para cerca de 9,5× (bioprocess 1,25% contra
  gasoline 11,8%).
- Comparação de pré-processamento no Tecator (`seed_split` 0–29): SNV
  0,9686, SNV→derivada 0,9688, ΔR² = +0,0003, p = 0,76. O empate continua,
  e a escolha de SNV puro por parcimônia se mantém.
- Regenerados em 21/09/2026: `results/mean_baseline_{tecator,mango,bioprocess}.*`,
  `results/permuted_y_tecator.*` e `results/preprocessing_comparison_tecator.*`.
  O `PROTOCOLO.md` já traz os valores novos; a tabela original do
  pré-processamento continua lá, porque foi a base da decisão.

Limitação: a identificação das amostras é aproximada, porque Mango e
bioprocess não expõem identificador. Réplicas não detectadas continuariam
vazando; coincidências agrupadas por engano apenas tornam a partição mais
conservadora.

Proposta pendente de aprovação da orientação. O código já está
implementado, e os números do protocolo e os arquivos de resultados já
foram atualizados.

## Adendo (05/11/2026): as réplicas do Tecator que esta regra não pega

Achado de 30/09/2026, registrado até aqui num arquivo de trabalho fora do
git (`docs/PENDENCIAS.md`, item A1) e trazido para cá. **Nada foi alterado
no código.** A correção muda as partições do Tecator e obriga a regenerar
os resultados dele, então espera a palavra da orientação, a quem o achado
ainda não foi levado.

**A premissa do Tecator está errada.** O Contexto diz que repetições em
linhas distantes "são compatíveis com coincidência". Não são. O Tecator tem
22 pares de espectros idênticos bit a bit, nos 100 canais, e nos 22 o
(fat, water, protein) também é idêntico. São réplicas da mesma amostra.
Só 2 desses pares estão em linhas vizinhas, e só esses 2 a regra agrupa.
Os outros 20 ficam em grupos diferentes.

Medido em 05/11 no loader deste trabalho (`load("tecator")`, 215 linhas,
208 grupos) e conferido com `scripts/verificar_replicas_tecator.py`:

| o que | medido |
|---|---|
| pares de espectros idênticos | 22, todos com `y` idêntico |
| no mesmo grupo do ADR 009 | 2 |
| separados pelo ADR 009 | 20 |
| atravessam treino/teste no `evaluate()`, `seed_split` 0–29 | de 3 a 11 por semente, mediana 8; em todas as 30 |
| atravessam a divisão 172/43 do modo da literatura | 7 |

**Também a frase das Consequências está errada.** Lá se lê que "nenhum par
de réplicas do Tecator atravessa essa fronteira" (172/43). Isso vale só
para os pares vizinhos. Dos 22 pares idênticos, 7 atravessam.

**O que isso atinge:** todo número do Tecator deste trabalho calculado com
a partição atual, inclusive o piso de ruído, a comparação de
pré-processamento e os braços do Estágio 2 (PLS, iPLS, VIP e GA-PLS).
Quanto, não foi medido nos braços. Duas medidas parciais:
- Na âncora do artigo (ADR 013, "Ressalva obrigatória"), o efeito sobre o
  PLS foi pequeno: a gordura vai de 0,946 para 0,943.
- Em 28/10 (DIARIO), agrupar os pares na comparação de pré-processamento
  não mostrou otimismo sistemático no H\*, mas o teste ficou confundido,
  porque mudar os grupos muda também a partição.

**O tamanho do efeito no teste, medido em 05/11** com
`scripts/verificar_vazamento_replicas_tecator.py` (duas execuções
idênticas):
- **Como foi medido.** `evaluate()` com o `PLSArm` e a partição atual,
  `seed_split` 0–29. Em cada semente, o mesmo modelo e o mesmo teste, com
  o R² de dois jeitos: no teste inteiro, e sem os espectros cujo gêmeo
  ficou no treino (de 3 a 11 por semente, mediana 8).
- **A referência.** Tirar do teste o mesmo número de amostras sem gêmeo,
  em 200 sorteios por semente, porque mudar o teste muda o R² mesmo sem
  vazamento.
- **Resultado:** o vazamento infla o R² do teste em +0,0010 na mediana
  (faixa de −0,0040 a +0,0056). Ficou positivo em 19 das 30 sementes, o
  que não se distingue do acaso (teste do sinal, p = 0,20). O R² do
  próprio teste inteiro varia de 0,9515 a 0,9821 entre as sementes, cerca
  de trinta vezes a mediana do efeito.
- **No PLS, então, o efeito no teste é pequeno perto da variação entre
  partições.** Duas coisas ficam sem medida:
  - os pares que ficam os dois no treino, em folds diferentes da CV
    interna (de 4 a 13, mediana 9), e que podem otimizar a escolha do
    número de componentes;
  - os outros braços. Um braço que seleciona bandas, ou uma rede, pode
    aproveitar o gêmeo mais do que o PLS.

**Teste que guarda o defeito (05/11).** `tests/test_data.py::test_identical_spectra_with_identical_target_share_a_group` exige que espectro e alvo idênticos fiquem no mesmo grupo, nos quatro conjuntos. Passa no Gasoline, no Mango e no bioprocess. No Tecator falha com "20 de 22" e está marcado como falha esperada estrita: quando a correção entrar, ele passa, e a marca tem de sair.

**Correção proposta, a decidir com a orientação:** agrupar também por
espectro idêntico. No Tecator, a amostra passaria a ser a união de linhas
vizinhas com alvos idênticos e de linhas com espectro idêntico. Depois,
regenerar os resultados do Tecator e declarar a mudança.

**A correção, pronta e desligada (06/11).** Implementada em `src/tcc/data.py`
como a opção `TECATOR_GROUP_IDENTICAL_SPECTRA`, hoje `False`:
- **Ligada,** junta aos grupos das linhas vizinhas as linhas com espectro e
  alvos (fat, water, protein) idênticos.
- **Testes:** dois. Com a opção ligada, os 22 pares ficam no mesmo grupo,
  nenhum grupo antigo é partido e nenhum grupo cruza treino/teste em 10
  partições.
- **Com a opção desligada,** nada muda e a suíte passa inteira.

**Efeito medido** com `scripts/medir_correcao_replicas_tecator.py`:

| | regra atual | com a correção |
|---|---|---|
| grupos | 208 | 188 |
| pares cruzando treino/teste, por partição (0–29) | 3 a 11 | 0 |
| partições com o mesmo conjunto de teste | — | 0 de 30 |
| PLS completo, R² mediano (30 partições) | 0,9692 | 0,9657 |
| PLS completo, RMSEP mediano | 2,139 | 2,205 |
| piso de ruído (`MeanArm`, 100 partições) | 7,7% | 7,8% |

R² com − sem, por semente: mediana −0,0020, faixa de −0,0140 a +0,0087.
Como as partições mudam, essa diferença não é pareada na mesma partição.

**O que os números mostram:**
- **O vazamento inflava o PLS do Tecator,** mas pouco perto da variação
  entre partições.
- **A queda é maior que os +0,001 medidos só no lado do teste,** o que é
  compatível com a correção tirar também o vazamento da CV interna. Isso
  não foi medido em separado.
- **Aplicar a correção muda as 30 partições,** então todo número do
  Tecator teria de ser regenerado: o piso, a comparação de
  pré-processamento e os braços. Para ativar, basta ligar a opção, tirar a
  marca de falha esperada do teste e regenerar.

## Adendo (10/11/2026): a decisão da orientação e a regra em vigor

**A decisão (09/11/2026).** A orientação mandou corrigir agora, antes de
fechar os braços, e ampliar a correção. Os motivos dela:
- o defeito está no `evaluate()`, pelo qual todos os braços passam;
- a medida de 05/11 cobria o vazamento treino/teste no PLS, o braço menos
  capaz de aproveitar um gêmeo, e não o da CV interna;
- corrigir antes de existir resultado de braço não exige justificar
  depois que a mudança não foi dirigida pelos resultados;
- o Tecator é o conjunto mais barato e o único atingido.

O status deste ADR continua "proposto": a orientação decidiu a correção,
não o ADR.

**A regra em vigor** (`src/tcc/data.py`, `_tecator_replicate_groups`). Duas
linhas do Tecator são da mesma amostra se têm (fat, water, protein)
idênticos e mais uma destas condições:
- **A:** são vizinhas (a regra original);
- **B:** o espectro é idêntico bit a bit;
- **C:** o espectro é próximo, com max |dx| < 0,30 na absorbância bruta.

A amostra é a componente conexa dessas ligações, e não o par. O alvo
idêntico é exigido nas três relações, como no teste de 05/11 (nota (c) da
orientação).

**Por que essa regra** (análise da orientação em `verify_tecator_replicates.py`,
reproduzida aqui em 10/11 com os mesmos números):
- **Alvo idêntico sozinho não é evidência:** são 42 pares, contra cerca de
  39 esperados pelo acaso.
- **A conjunção é evidência:** alvo idêntico e espectro entre os mais
  próximos do conjunto aparece 12 vezes, contra cerca de 1 esperada. Nos
  22 pares de espectro idêntico, os 22 têm alvo idêntico, contra 0,01
  esperado.
- **O espectro idêntico é um limiar limpo:** entre 0 e 0,0105 de max |dx|
  não há nenhum par.
- **O limite de C é insensível:** qualquer valor de 0,15 a 0,40 dá os
  mesmos 12 pares e os mesmos 180 grupos. O 0,30 foi declarado antes de
  rodar, no meio desse platô; com 0,10 seriam 182 grupos, e com 0,45, 179.

**Contagens.** São 208 grupos com a regra original, 188 com a correção de
06/11 (A e B) e 180 com a regra em vigor: 148 linhas isoladas, 30 pares,
um trio (linhas 63, 149 e 177) e um quarteto (57, 58, 134 e 191). O
quarteto só se forma por fechamento transitivo: 134 e 191 não se ligam
diretamente.

**As duas frases apontadas no adendo de 05/11, com os números novos:**
- **O tamanho do teste:** com o maior grupo de 4 linhas, o teste do Tecator
  pode ir de 54 a 57 (alvo 54), e não de 54 a 55. Medido em 100 partições:
  81 com 54, 16 com 55, 1 com 56 e 2 com 57.
- **A divisão 172/43 do modo da literatura:** é a divisão fixa do artigo e
  não respeita grupos. Com a regra em vigor, 11 grupos (25 linhas)
  atravessam essa fronteira. É mais uma razão para a âncora do ADR 013
  servir à comparação com o artigo, e não como medida limpa.

**Limitação que fica.** A regra continua aproximada, agora com um limiar.
O par não idêntico mais próximo de todo o conjunto, as linhas 60/68 e 61/68
(max |dx| 0,0105, 0,33% da escala), tem o alvo diferente na primeira
decimal. Pode ser a mesma amostra com a química de referência repetida,
mas agrupar por proximidade espectral com alvo diferente seria outra
regra, sem evidência própria, e não foi adotada.

**Testes.**
- **O teste de 05/11 saiu da falha esperada e passa.**
- **Os testes novos cobrem:**
  - as três relações;
  - as componentes conexas, inclusive uma cadeia em que só o fechamento
    pela raiz dá o grupo certo;
  - os 180 grupos, com o trio e o quarteto;
  - os pares de alvo igual por acaso, que não se juntam;
  - a limitação das linhas 60/68;
  - o platô do limite.
- **Mutações:** cinco, todas pegas.

**Regenerado em 10/11** (PROTOCOLO, `results/` e notas nos ADRs 012 a 016):
- **o piso de ruído do Tecator** passa de ~7,7% a ~8,9%, com o teste
  variando de 54 a 57;
- **a comparação de pré-processamento** continua em empate, agora com o
  SNV ligeiramente à frente (ΔR² −0,0004, p = 0,64 no teste t pareado), e
  a escolha do SNV não muda;
- **a sonda de y permutado** não mostra vazamento;
- **os braços clássicos** no Tecator, nas `seed_split` 0–29
  (`results/bracos_tecator_30_particoes.csv`), ficam no nível do PLS
  completo: ΔR² mediano de −0,0011 no iPLS a +0,0020 no CARS `fiel`, e
  nenhum se distingue do PLS no Wilcoxon pareado (p de 0,070 a 0,382).

**O vazamento na CV interna, medido como a orientação pediu**
(`scripts/medir_vazamento_cv_interna_tecator.py`). Com a partição de cada
`seed_split` 0–29 fixa, as folds do protocolo foram comparadas com as
mesmas folds com as réplicas espalhadas. De 22 a 29 linhas mudam de fold;
nenhuma outra muda.
- **O RMSECV fica mais otimista com as réplicas separadas** em 27 de 30
  partições: mediana −0,066, cerca de 3% (Wilcoxon p < 0,001).
- **O H\* do PLS muda em 15 de 30:** sobe em 13 e cai em 2; no pior caso,
  de 3 para 14.
- **O R² de teste não muda de forma consistente:** mediana 0,0000, p =
  0,73.

O vazamento da CV interna distorce a escolha do modelo, e era isso que a
regra antiga deixava passar. No PLS, a distorção quase não chega ao teste.
Nos braços que selecionam bandas, que usam o mesmo erro interno para
escolher, o efeito não foi medido; com a regra em vigor, ele deixa de
existir.
