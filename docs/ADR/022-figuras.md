# ADR 022 — As figuras (Estágio 8)

**Data:** 2026-11-13
**Status:** proposto

## Contexto

O Estágio 8 do pipeline (`docs/fontes/pipeline_tcc_rodrigo.md`) pede sete
figuras:
1. a cascata da decomposição, de A1 até B4;
2. os intervalos de confiança ao lado da margem de equivalência, um por
   termo;
3. desempenho × reprodutibilidade, um ponto por braço (a figura da H5);
4. o Jaccard nos dois eixos de semente, lado a lado, com os
   determinísticos marcados;
5. as bandas de cada método sobre o espectro médio e as janelas químicas;
6. o custo por braço, em escala log;
7. a decomposição por regime amostral (a figura da H7).

As figuras finais só saem da grade final (`seed_split` ≥ 100), que espera o
congelamento do protocolo. O que dá para fazer antes é o código, testado, e
uma rodada com o piloto só para olhar.

## Decisão proposta

`src/tcc/figures.py`, uma função por figura, e `tests/test_figures.py`.

- **As funções não calculam resultado.** Recebem o que as métricas (ADR
  019) e a decomposição (ADR 020) já calcularam e devolvem uma figura do
  matplotlib. Assim o que é testado aqui é só o desenho.
- **A cascata e a figura por regime usam a média dos termos, não a
  mediana.** Só a média é aditiva: a média de B4 − A1 é a soma das médias
  dos três termos, e a barra final da cascata (A1 + soma) é a média do B4.
  Com a mediana a barra do B4 deixa de ser o B4. No piloto do Tecator, A1
  + soma das medianas dá 0,97088, e a mediana real do B4 é 0,97305; com a
  média, as duas contas dão 0,97112. A média é também o que o TOST testa
  (ADR 020).
- **Custo pelo tempo**, não pelo `n_fits`: o `n_fits` de rede conta 1 por
  treino e não é comparável com o dos braços clássicos (ADR 017).
- **Cores:** azul (#2a78d6) e laranja (#eb6834), validados juntos para as
  três formas de daltonismo; cinza para o que é referência (A1 e B4 na
  cascata, faixa ±δ, janelas químicas); texto sempre em tinta neutra, nunca
  na cor da série. Na cascata e por regime, azul é ganho e laranja é perda;
  na figura 3, azul é braço clássico e laranja é rede, com legenda.
- **Números escritos na figura em formato brasileiro** (vírgula decimal)
  onde o texto é nosso: rótulos de custo e eixo log.

### Testes

25 testes com entrada sintética, lendo de volta o que foi desenhado:
- as bases e alturas das barras da cascata (acumuladas a partir do A1) e a
  cor pelo sinal;
- a faixa exatamente em ±δ;
- a ordem dos termos e os rótulos de equivalência;
- a cor de cada braço e o lado do rótulo;
- as barras dos dois eixos de Jaccard e o rótulo dos determinísticos;
- o traço do acaso só onde há barra;
- as posições das bandas;
- a escala log sem traços menores e a ordem crescente;
- a ordem dos painéis por n;
- o título geral sem cobrir os títulos dos painéis.

19 mutações no código, todas pegas.

### Rodada com o piloto

`scripts/figuras_piloto.py`, com a grade de conferência do Tecator (ADR 021)
e um eixo `seed_algo` pequeno, grava as sete em `results/figuras_piloto/`,
fora do git. Os números são piloto e não entram no texto. O δ (0,01 em R²)
e a meia largura das janelas (±10 nm) são ilustrativos.

## Em aberto (para a orientação)

- **A métrica das figuras 1, 2 e 7** segue a do δ, que ainda não foi
  decidida (R² ou RMSEP).
- **Separador decimal nos eixos:** os rótulos escritos por nós saem com
  vírgula; os valores dos eixos lineares ainda saem com ponto, no formato do
  matplotlib. Proposta: vírgula em tudo na versão final.
- **Formato para o manuscrito:** proposta de PDF vetorial; os PNG de agora
  são só para olhar.
- **Figura 3:** o eixo x usa a mediana de ΔR² contra o PLS. Ali não há
  soma, então a mediana serve, mas pode mudar para a média por
  consistência com a cascata.

## Consequências

- O Estágio 8 fica com o código pronto e testado. As figuras do texto saem
  depois da grade final, rodando as mesmas funções.
- Olhar as figuras do piloto já serviu para achar cinco erros de desenho e
  o da mediana na cascata (DIARIO, 13/11). Nenhum mudava número, mas o da
  cascata fazia a figura mostrar um B4 que não era o B4.
