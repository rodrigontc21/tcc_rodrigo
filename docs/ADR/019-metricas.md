# ADR 019 — As métricas (Estágio 6)

**Data:** 2026-11-13
**Status:** proposto

## Contexto

O Estágio 6 do pipeline pede funções puras sobre os resultados gravados,
nada calculado dentro do treino, em quatro grupos: desempenho (R², RMSE,
RMSEP no teste externo); reprodutibilidade da seleção (Jaccard médio par a
par, separado nos dois eixos de semente, concluindo pelo `seed_split`);
plausibilidade química (fração das `k` bandas em janelas de atribuição
espectroscópica documentada, com as janelas e as fontes tabeladas); e custo
(`n_fits` e `wall_time` por braço, incluindo a busca interna).

**Critério de aceitação:** cada métrica tem teste com entrada sintética de
resposta conhecida. Métrica sem teste não entra no manuscrito.

## Decisão proposta

`src/tcc/metrics.py` e `tests/test_metrics.py`.

- **`performance(y_true, y_pred)`:** R² e RMSE com a mesma conta do
  `evaluate()`. RMSE e RMSEP são o mesmo número no teste externo; os dois
  nomes ficam, porque o pipeline lista os dois.
- **`jaccard`, `mean_pairwise_jaccard`:** Jaccard recusa dois conjuntos
  vazios (0/0 não é definido); a média é sobre todos os pares não
  ordenados.
- **`reproducibility(results, k, axis)`:** converte cada resultado em
  conjunto pela camada de seleção (ADR 018) e agrupa por (conjunto, braço)
  e pela semente do **outro** eixo, fixa. No eixo `seed_split` compara
  partições com a mesma `seed_algo`; no `seed_algo`, sementes do algoritmo
  na mesma partição. Quando há mais de um valor da semente fixa, devolve a
  média dos grupos. Braços sem seleção ficam de fora; resultado repetido é
  erro.
- **`expected_jaccard(a, b, p)`:** o Jaccard esperado entre dois conjuntos
  de tamanhos a e b sorteados entre p bandas, pela interseção
  hipergeométrica, exata. É a referência do acaso, que muda com os
  tamanhos e por isso precisa acompanhar cada Jaccard.
- **`fraction_in_windows(selection, axis, windows)`:** a fração das bandas
  selecionadas cujo valor no eixo espectral cai em alguma janela, limites
  inclusos. Recebe as janelas; a tabela não existe ainda.
- **`cost_summary(results)`:** mediana de `n_fits` e de `wall_time` por
  (conjunto, braço), com o número de execuções.

**Testes (14), todos com entrada sintética de resposta conhecida:** R² e
RMSE em casos feitos à mão; Jaccard em casos feitos à mão, simetria e a
recusa de dois vazios; a média par a par; o Jaccard do acaso conferido por
enumeração completa (p = 6) e por sorteio (p = 100); os dois eixos
separados numa grade em que um braço é estável só na partição e outro só
no algoritmo; a passagem pela camada de seleção; o descarte de braço sem
seleção; duplicatas; as janelas com limite incluso; e o custo pela
mediana. Oito mutações, todas pegas (uma, a média no lugar da mediana do
custo, só depois de trocar os dados do teste, que tinham média igual à
mediana). Suíte inteira: 227 passaram, 1 pulado.

## Em aberto

1. **A tabela de janelas químicas** de cada conjunto, com as fontes. É
   trabalho de leitura (revisão dirigida), não de código, e nenhuma janela
   foi escolhida ainda.
2. **O Jaccard do acaso ao lado de cada Jaccard.** Proposta: reportar
   sempre o par (Jaccard observado, Jaccard esperado pelos mesmos
   tamanhos), porque os tamanhos explícitos do iPLS, do GA-PLS e do CARS
   diferem do `k` (ADR 018, item 3).
3. **A linha de base do prior para a H5** (sugerida à orientação em 12/11):
   o Jaccard do top-k do próprio prior entre partições, calculado do mesmo
   jeito. A função de reprodutibilidade serve, desde que o prior seja
   gravado como um resultado com `band_scores`; fica para quando a
   orientação responder.
4. **Agregação quando a semente fixa tem vários valores:** a média dos
   grupos. Alternativa: reportar cada grupo. A grade decide quantos valores
   existem (pipeline: 10 `seed_algo` com `seed_split` fixo, só nos braços
   estocásticos).

## Conferência (13/11/2026)

- **Contra bibliotecas independentes:** o Jaccard bate com o
  `jaccard_score` do scikit-learn (500 pares sorteados) e o Jaccard do acaso
  com a hipergeométrica do scipy (quatro casos). Dois testes permanentes; o
  arquivo de testes passou a 16.
- **Em dados reais,** `scripts/conferir_metricas_tecator.py` (Tecator,
  piloto, 106 resultados): a métrica de desempenho recalcula o R² e o RMSEP
  de cada `Result` com diferença zero; o B2, porta congelada, dá exatamente
  o Jaccard do top-k do prior (0,835), como deve, por ser função monótona do
  prior. Tabela e leitura no DIARIO de 13/11.

