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
