# ADR 018 — A camada de seleção (Estágio 4)

**Data:** 2026-11-13
**Status:** proposto

## Contexto

O Estágio 4 do pipeline converte a saída de qualquer braço num conjunto de
bandas comparável entre métodos, para as métricas de seleção do Estágio 6
(Jaccard, H5 e H6):

```python
def to_selection(arm_output, k: int) -> set[int]
```

- métodos com seleção explícita (iPLS, CARS, GA-PLS): o conjunto que
  devolvem;
- VIP e portas contínuas: as `k` bandas de maior escore/peso;
- `pls_full` e `mlp_full`: sem seleção, fora das métricas de seleção.

**Cardinalidade pareada:** `k` é fixado no protocolo e igual ao número
médio de bandas retidas pelos métodos clássicos no conjunto, porque Jaccard
entre conjuntos de tamanhos diferentes é enganoso. **Critério de aceitação:**
as conclusões de reprodutibilidade se mantêm para `k` numa faixa declarada
(por exemplo ±50%); se não se mantiverem, isso é resultado.

Até aqui o `Result.selection` ficava `None`. Os braços clássicos de seleção
já expunham as bandas finais (`selection`), e os de porta e o VIP, o escore
por banda (`band_scores`).

## Decisão proposta

`src/tcc/selection.py` e `tests/test_selection.py`.

- **O `evaluate()` grava em `Result.selection`** a seleção explícita do
  braço, quando existe (iPLS, VIP, GA-PLS e CARS), e `None` nos outros.
  Nenhum número muda: é só o campo que estava vazio.
- **`to_selection(result, k)`**, pela regra do pipeline, decidida pelo que
  o `Result` traz:
  - com `band_scores` (VIP, B2, B2', B3, B4 e B5): as `k` de maior escore;
  - sem escore e com `selection` (iPLS, GA-PLS e CARS): o conjunto do
    método, do tamanho que ele escolheu, qualquer que seja `k`;
  - sem nenhum dos dois (PLS completo, MLP sem porta): `None`.

  O VIP tem as duas coisas, e o pipeline manda usar o escore, não o corte
  por limiar do braço.
- **Desempate no top-k:** entre escores iguais, fica a banda de menor
  índice. A seleção depende só da ordem dos escores.
- **`paired_k(results)`:** a média, arredondada com 0,5 para cima, do
  tamanho da seleção dos braços iPLS, VIP, GA-PLS e CARS `protocolo`. O CARS
  `fiel` fica de fora: ele existe para o portão contra o artigo, e quem
  entra na comparação é o `protocolo` (ADR 016).
- **`k_grid(k, p)`:** a faixa da análise de sensibilidade, com os fatores
  0,5, 0,75, 1, 1,25 e 1,5 de `k`, arredondados e recortados a [1, p].

**Testes (20):** top-k, desempate, invariância a transformação monótona,
recusa de `k` fora da faixa e de `nan`; a regra do pipeline nos três casos,
inclusive o escore valendo sobre a seleção explícita; o `k` pareado com
arredondamento para cima e só com os braços clássicos; os nomes dos braços
clássicos conferidos contra os braços; a faixa de `k`; e o `evaluate()`
gravando a seleção, `None` para quem não seleciona e o top-k da porta no
Tecator. Sete mutações, todas pegas, arquivos restaurados com o hash
conferido. Suíte inteira: 213 passaram, 1 pulado.

## Em aberto, a confirmar com a orientação

1. **De onde sai o `k`.** Proposta: das execuções clássicas da própria
   grade final (`seed_split` ≥ 100), por conjunto. O `k` depende só do
   tamanho das seleções, não do desempenho, mas sair do piloto (0–29)
   faria um parâmetro do protocolo depender de números de piloto, o que a
   orientação pediu para não fazer em 12/11.
2. **Média de quê:** de todas as execuções juntas (cada braço pesa pelo
   número de execuções, que é igual entre eles) ou a média das medianas
   por braço. A proposta é a primeira, que é o que "número médio" diz.
3. **Os tamanhos explícitos não são `k`.** O iPLS, o GA-PLS e o CARS
   devolvem o tamanho que escolheram, e no piloto esses tamanhos são bem
   diferentes entre si (no Mango, de cerca de 50 a 140 bandas). O Jaccard
   entre um deles e um top-k ainda compara conjuntos de tamanhos
   diferentes. O pipeline aceita isso; a ressalva fica declarada.
4. **Os fatores da faixa de sensibilidade** (0,5 a 1,5), que o pipeline
   dá só como exemplo.

## Resposta da orientação (25/11/2026)

1. **De onde sai o `k`: do piloto** (`seed_split` 0–29), declarado antes da
   grade. A orientação desfez a própria frase de 12/11: a regra é que nada
   muda com base em **resultado** de piloto, e **tamanho de seleção não é
   resultado**. A faixa 0–29 existe exatamente para fixar parâmetro de método,
   e o `k` é um. Tirar o `k` da grade final seria pior: faria o parâmetro da
   métrica ser função dos dados que ela mede. A proposta deste ADR (tirar da
   grade final) fica superada.
2. **Média de todas as execuções juntas** (média agrupada): aprovado.
3. **Os tamanhos explícitos não são `k`:** declarar, junto com o Jaccard do
   acaso casado em tamanho (`expected_jaccard`, ADR 019).
4. **Os fatores de 0,5 a 1,5:** aprovados. O critério de aceitação do
   pipeline (as conclusões se mantêm na faixa de `k`, ou a falha é resultado)
   é reportado de todo modo.

**O valor do `k` ainda não sai dos CSVs do piloto atual.** O `k` é a média do
tamanho das seleções do iPLS, do VIP, do GA-PLS e do CARS `protocolo`, e as
decisões de 25/11 mudam essas seleções antes da grade: a banda 663 sai do
bioprocess (ADR 007), o iPLS passa a desempatar pelo menor número de bandas e a
selecionar com `scale = TRUE` (ADR 012), e os braços clássicos passam a
entregar o modelo nas mesmas linhas das redes (ADR 017). Os CSVs de
`results/bracos_*_30_particoes.csv` são de antes disso, e o VIP neles ainda é
da grade antiga (ADR 014). Então o `k` é calculado depois de os braços
clássicos rodarem de novo nas `seed_split` 0–29 com o código final, e é
escrito no PROTOCOLO antes da grade. A regra da conta (`paired_k`) não muda.

Status: segue **proposto**. A orientação decidiu os itens, e não escreveu
"aceito".
