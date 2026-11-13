# ADR 020 — Decomposição pareada e equivalência (Estágio 7)

**Data:** 2026-11-13
**Status:** proposto

## Contexto

O Estágio 7 do pipeline:
- **Decomposição:** cada termo é calculado pareado, por (conjunto,
  `seed_split`), e só depois agregado: Δ_não-lin = B1 − A1, Δ_ponderação =
  B2 − B1, Δ_aprendizado = B4 − B2, e Δ_prior = B4 − B3 como contraste
  complementar, fora da soma. Calcular a partir de médias marginais quebra
  o pareamento. Exige um teste que verifique a identidade aditiva por
  (conjunto, semente).
- **Equivalência (TOST):** dois testes unilaterais contra ±δ; "equivalente"
  só se os dois rejeitarem; o intervalo de confiança sempre ao lado da
  margem. A margem é escolhida antes de ver resultados.
- **Comparação global:** Friedman entre braços sobre os conjuntos, com
  pós-teste pareado e correção para múltiplas comparações.

## Decisão proposta

`src/tcc/decomposition.py` e `tests/test_decomposition.py`.

- **`decompose(results, metric)`:** os quatro termos e o total B4 − A1 por
  (conjunto, `seed_split`), na métrica pedida (R² por padrão). O B4 é o
  B4-limpo (`gate_prior`), como o PROTOCOLO manda onde diz só "B4". Uma
  partição sem algum dos cinco braços sai de **todos** os termos, e não só
  dos que usam o braço que falta, para todos os termos ficarem sobre as
  mesmas partições; as excluídas são listadas.
- **Célula repetida é erro:** mais de um `seed_algo` na mesma (conjunto,
  `seed_split`, braço) precisa ser reduzido antes, e como reduzir é a
  pergunta 8 do protocolo, ainda aberta.
- **`paired_differences(results, a, b)`:** a diferença pareada entre dois
  braços quaisquer, para os contrastes fora da decomposição (H6, B5 − B4;
  H8 com o B5 e o B2').
- **`tost(d, delta, alpha)`:** TOST de teste t sobre as diferenças
  pareadas. Devolve a média, o intervalo de 1 − 2α, os dois p unilaterais e
  o p do TOST (o maior). Equivalente se e só se o intervalo cabe em
  (−δ, δ).
- **`holm`, `friedman`, `posthoc_wilcoxon_holm`:** Friedman do scipy sobre
  uma tabela blocos × braços; pós-teste de Wilcoxon pareado em todos os
  pares, com Holm.

**Dependência nova:** `statsmodels` 0.15.0, instalado em 13/11, só para
conferir o TOST e o Holm contra uma implementação independente nos testes.
Entrou no `requirements.txt` com as três dependências que trouxe.

**Testes (12):** a identidade aditiva em toda partição, em R² e RMSEP
(diferença abaixo de 1e-12); os termos num caso feito à mão; a partição
incompleta saindo de todos os termos; a média marginal diferente da
pareada quando falta uma partição; célula repetida; **o TOST igual ao
`ttost_paired` do statsmodels**; a equivalência igual ao intervalo dentro
da margem, em 300 sorteios; casos conhecidos do TOST; **o Holm igual ao
`multipletests` do statsmodels**; Holm num caso à mão; o Friedman
detectando uma ordem consistente; e o pós-teste cobrindo todos os pares.
Oito mutações, todas pegas. Suíte inteira: 241 passaram, 1 pulado.

## Em aberto, a confirmar com a orientação

1. **Em que métrica vai o δ.** O PROTOCOLO declara o limite inferior do δ
   pelo piso de ruído do RMSEP, em porcentagem; a decomposição do pipeline
   é em R². O TOST precisa usar a mesma métrica do δ. Ou se declara o δ
   também em R², ou a decomposição e o TOST vão em RMSEP relativo.
2. **Como reduzir vários `seed_algo` numa célula** (pergunta 8): diagonal
   ou média sobre réplicas. O código recusa até isso ser decidido.
3. **TOST de teste t.** Supõe diferenças aproximadamente normais. As
   alternativas são o TOST por Wilcoxon ou por bootstrap; a proposta é o
   t, com a forma das diferenças conferida no piloto.
4. **Os blocos do Friedman.** O pipeline diz "sobre os conjuntos": são 4
   blocos. Com 4 blocos, o menor p possível de um Wilcoxon pareado é
   0,125, e nenhum pós-teste seria significativo depois de Holm. A
   alternativa é usar (conjunto, `seed_split`) como bloco. Precisa ser
   decidido antes da grade.
5. **α = 0,05,** o padrão.

## Conferência (13/11/2026)

- **Contra o R base,** sem pacote novo: o TOST bate com dois `t.test`
  unilaterais e o intervalo de 90% com o `t.test` bilateral; o Holm com o
  `p.adjust`; o Friedman com o `friedman.test`; o Wilcoxon com o
  `wilcox.test` pareado. Quatro testes permanentes; o arquivo passou a 16.
- **Em dados reais,** `scripts/conferir_decomposicao_tecator.py` (Tecator,
  `seed_split` 0–9, piloto): a identidade aditiva fecha com diferença zero
  nas 10 partições; os termos e um TOST com δ só ilustrativo estão no
  DIARIO de 13/11.

