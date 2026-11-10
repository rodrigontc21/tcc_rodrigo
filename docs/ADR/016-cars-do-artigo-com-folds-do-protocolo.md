# ADR 016 — CARS do artigo, com as folds do protocolo

**Data:** 2026-11-05
**Status:** proposto

## Contexto

Quarto e último braço clássico do Estágio 2, depois do iPLS (ADR 012), do
VIP (ADR 014) e do GA-PLS (ADR 015). O ADR 008 (proposto) mandou tirar o
CARS do libPLS, dos autores do método. Conferido em 05/11, nenhuma versão do
código dos autores serve como está (adendo de 05/11 do ADR 008):

- o `carspls.r` do GitHub depende do `ceil` do pacote `Hmisc`, que o
  repositório não declara, e é a versão simplificada, sem os sorteios;
- o `carsplsorigin.r` tem o algoritmo original, mas com três diferenças em
  relação ao MATLAB (a curva EDF deslocada um passo, o arredondamento e o
  denominador do RMSECV);
- o `carspls.m` do libPLS 1.95, a distribuição oficial, tem como padrão uma
  versão sem os dois sorteios (`originalVersion = 0`), que não é o método
  publicado;
- as três fazem a própria validação cruzada, sem as folds do protocolo e
  sem os grupos do ADR 009. É o mesmo problema que tirou o
  `plsVarSel::ga_pls` do GA-PLS.

O pipeline manda seguir o artigo original onde for preciso implementar,
registrar o que ele deixa em aberto e levar à validação cruzada interna o
"número de execuções de Monte Carlo e razão de amostragem (CARS)".

**O que foi lido.**

- **Li, Liang, Xu e Cao (2009),** *Anal. Chim. Acta* 648(1):77–84, na
  cópia pessoal que os autores publicaram no projeto `carspls` do Google
  Code (arquivado). As Seções 2.2 a 2.6 e a Fig. 3 descrevem o algoritmo;
  a Seção 4.1 e a Fig. 5 tratam do número de execuções.
- **O código do grupo,** linha a linha:
  - `carspls.m` do `CARS.rar` (2010) e da versão 1.50 (2011) do mesmo projeto;
  - `carspls.m` do libPLS 1.95;
  - `carspls.r` e `carsplsorigin.r` do GitHub.

  Os hashes estão no adendo do ADR 008.
- **O pacote R `carspls_1.0.0` (2009),** do mesmo projeto: o código é
  idêntico ao do GitHub.
- **O `pls.m`, o `pls_nipals.m`, o `plscvfold.m` e o `pretreat.m`** da
  versão 1.50, que o `carspls.m` chama:
  - os coeficientes saem de W(P'W)⁻¹q, a mesma conta do `coef_path`;
  - `'center'` só subtrai a média;
  - o RMSECV é a raiz do PRESS somado sobre o total de amostras, e o
    número de componentes é o de menor RMSECV;
  - os segmentos da CV são formados com as amostras ordenadas por `y`, em
    rodízio.

**O algoritmo do artigo.** São N execuções. Em cada uma, a partir das
variáveis que sobraram da anterior (na primeira, todas):

1. **Amostragem Monte Carlo:** um PLS com uma fração fixa das amostras de
   calibração, sorteadas sem reposição. O artigo diz "usually 80–90%"; os
   códigos usam 0,9.
2. **Pesos:** w_i = |b_i| / Σ|b_j|, com b os coeficientes do PLS (eq. 3).
   Variáveis já eliminadas têm peso zero.
3. **EDF, eliminação forçada:** mantém a fração r_i = a·e^(−k·i) das p
   variáveis, as de maior |b|, com a = (p/2)^(1/(N−1)) e k = ln(p/2)/(N−1).
   Assim r_1 = 1 e r_N = 2/p (eqs. 4 a 6). Nos códigos 1.50 e 1.95, a
   execução i usa r_(i+1): a primeira ajusta com todas as variáveis e
   corta para r_2. Os dois descrevem a mesma sequência de subconjuntos.
4. **ARS, eliminação competitiva:** p sorteios com reposição, com
   probabilidade proporcional aos pesos. Seguem para a próxima execução as
   variáveis sorteadas ao menos uma vez.
5. **Escolha:** o subconjunto, entre os N, com o menor RMSECV.

No artigo, X e y são centrados na média (Seção 2.1); os exemplos usam 10
segmentos de CV e 100 execuções.

## Decisão

Implementar o CARS do artigo em Python, como o GA-PLS: motor e regras do
artigo, avaliação com as folds do protocolo, conferido contra o `carspls.m`
1.50 e o 1.95 com `originalVersion = 1`.

- **Algoritmo:** os passos 1 a 5 acima, na forma dos códigos 1.50 e 1.95
  (`ratio = a·exp(−b·(iter+1))`, `K = round(p·ratio)`), que é a versão que
  os autores distribuíram.
- **Sorteios:** os dois (amostras e ARS) saem de `rng_algo`, o gerador do
  `seed_algo`. A mesma semente dá a mesma seleção, e sementes diferentes
  dão seleções diferentes (ADR 008, Consequências).
- **Coeficientes para os pesos:** PLS só com centragem, como no artigo e no
  padrão `method = 'center'` dos códigos. O modelo entregue continua sendo
  o `PLSRegression` autoescalado do A1 (`_fit_pls`), como nos outros braços.
  É a mesma diferença de geometria entre seletor e regressor do iPLS
  (pergunta 13), declarada aqui pelo mesmo motivo.
- **RMSECV dos N subconjuntos:** nas folds do protocolo. Dentro de cada fold
  externo, nas folds internas (`_inner_folds`), como no GA-PLS, que
  respeitam os grupos do ADR 009. O RMSECV é a raiz do PRESS somado nas
  folds sobre o total de linhas de validação, como o `plscvfold` do
  `carspls.m`, e o subconjunto escolhido é o de menor RMSECV, como no
  artigo.
- **Componentes** (revisto em 05/11, depois da verificação no milho;
  ver Consequências):
  - O teto A dos PLS internos é um fator vezes o número de componentes
    do A1 (regra de um erro-padrão do `PLSArm`), recortado pelo teto da
    busca do `PLSArm`. O fator vai à CV interna.
  - O RMSECV de cada subconjunto usa o número de componentes de menor
    RMSECV até A, como no artigo.
  - O modelo final usa o número de componentes que o CARS escolheu para o
    subconjunto vencedor, nos dois modos.
- **Hiperparâmetros na CV interna (pipeline):** número de execuções
  N ∈ {50, 100}, razão de amostragem ∈ {0,8, 0,9} e fator do teto ∈
  {1, 2, 3}, doze candidatos declarados a priori:
  - 50 é o padrão dos códigos e 100, o do artigo. Pela Fig. 5, de 50 a 500
    o desempenho não muda.
  - 0,8 e 0,9 são as pontas da faixa do artigo.
  - O fator existe porque o teto decide se o CARS acha a combinação de
    bandas: no milho do artigo, com teto 2 não acha nenhuma vez em 30, e
    com 10 acha todas. O artigo não informa o teto que usou, e o padrão
    do `carspls.m` é 2.

  A escolha segue a regra de um erro-padrão, e entre os candidatos dentro
  do limite fica o de menos bandas em média, o mesmo critério do VIP e do
  GA-PLS.
- **Auditoria de fold (ADR 011):** `cv_selections` com o subconjunto
  escolhido em cada fold, e o verificador anti-vazamento com a
  configuração (N, razão, fator) e o número de componentes do A1 fixos.
- **Custo:** cada execução ajusta um PLS (os pesos), e cada subconjunto é
  avaliado nas folds internas. Um ajuste com h componentes dá a curva de
  RMSECV de 1 a h (`coef_path`), sem reajustar para cada número de
  componentes. Mesmo assim, `n_fits` conta h ajustes por fold, como o
  `PLSArm`, para o orçamento ficar comparável entre os braços.

### Dois modos: `protocolo` e `fiel`

As adaptações acima podem, em tese, deixar o CARS mais fraco que o
publicado. O pipeline é explícito: "se o CARS implementado for pior que o
CARS publicado, o benchmark é inválido". Para medir isso em vez de supor, o
braço tem dois modos, como o B4-fiel e o B4-limpo do PROTOCOLO.

| | `protocolo` (padrão) | `fiel` |
|---|---|---|
| para que serve | a comparação com os outros braços | o portão contra o artigo, e medir o efeito das adaptações |
| algoritmo (passos 1 a 5) | o do artigo | o do artigo |
| N, razão de amostragem e fator do teto | por CV interna, entre {50, 100} × {0,8, 0,9} × {1, 2, 3} | fixos: N = 100 (artigo, Seção 4.1), razão 0,9 (os códigos) e fator 3 (o maior da grade) |
| componentes no RMSECV de cada subconjunto | o de menor RMSECV até o teto A | o de menor RMSECV até o teto A |
| modelo final | `PLSRegression` autoescalado (`_fit_pls`), com os componentes que o CARS escolheu | PLS só centrado, com os componentes que o CARS escolheu, como o `carspls.m` |
| folds, grupos e seleção aninhada (ADR 009 e 011) | sim | sim |

Os dois modos compartilham o mesmo código do algoritmo e diferem só nas
linhas da tabela. Nos dois, a seleção é aninhada e usa as folds do
protocolo: isso não é adaptação negociável, porque sem ela as réplicas
vazam.

Uso previsto:
- **O portão:** o modo `fiel` nos dados de milho do artigo, para comparar
  com a Tabela 2. Feito em 05/11 com o algoritmo (ver Consequências).
- **O efeito das adaptações:** os dois modos com as mesmas sementes. Se o
  `protocolo` não ficar pior que o `fiel`, as adaptações não enfraqueceram
  o método. Feito em 06/11 no Tecator e no Gasoline, em 10 partições (ver
  Consequências).

## Em aberto, a confirmar com a orientação

1. **Componentes no RMSECV de cada subconjunto e no modelo final.** O
   artigo usa o menor RMSECV; o libPLS 1.95 passou a usar por padrão a
   regra de um desvio-padrão (`selectLV = 1`), e o resto do protocolo usa a
   regra de um erro-padrão. A proposta segue o artigo dentro do CARS e no
   modelo final, nos dois modos. A regra de um erro-padrão entra só no
   número de componentes do A1, que define o teto.
2. **Faixa de N, da razão de amostragem e do fator do teto.**
3. **Centragem para os pesos contra autoescala no modelo final:** a mesma
   questão da pergunta 13, do iPLS.
4. **O portão de validação (pergunta 11):**
   - **No Gasoline,** há uma referência, Zhong et al. (2023), e o nosso
     CARS a reproduz na mesma divisão (ver Consequências). Se uma
     referência basta, é decisão da orientação.
   - **No Tecator,** não achei RMSEP publicado de CARS.
   - **No milho do artigo original,** o algoritmo reproduz o achado
     publicado, mas isso confere o algoritmo, e não o braço no protocolo
     deste trabalho.

## Consequências

- Nenhum código do libPLS é executado nem versionado (adendo de 05/11 do
  ADR 008).
- A conferência contra o MATLAB é por leitura linha a linha, sem rodar o
  código deles. Rodar exigiria o GNU Octave (`sudo apt`), uma decisão de
  ambiente que fica para depois, se a leitura não bastar.
- **Implementado em 05/11/2026** em `src/tcc/arms/cars.py`, com
  `tests/test_cars.py`.
  - São 30 testes: a EDF contra a fórmula do `carspls.m`, o `round` do
    MATLAB, o PLS centrado contra o sklearn, o RMSECV como PRESS somado,
    o sorteio de amostras, a semente, o sinal negativo, o teto, o número
    de componentes do modelo final, a recusa de N < 2 e de razão fora de
    (0, 1] e a seleção aninhada, inclusive uma versão vazada que o
    verificador reprova.
  - Doze mutações do código foram pegas pelos testes, com o arquivo
    restaurado e o hash conferido.
  - Custo medido com `scripts/medir_custo_cars.py` nos quatro conjuntos
    (`seed_split` 0).
    - No bioprocess, o braço rodou de ponta a ponta em 06/11: 1.605,7 s
      no `protocolo` e 435,8 s no `fiel`, contra 195,7 s do PLS completo.
    - A estimativa prévia (`scripts/estimar_custo_cars_bioprocess.py`) era
      de cerca de 36 min e 7 min.
    - Nessa partição, o `fiel` subiu a 18 componentes, teve o menor
      RMSECV interno e o pior R² de teste (0,8361), enquanto o
      `protocolo` ficou em 0,8771 com 63 bandas, contra 0,8677 do PLS
      completo.
- **Conferência nos dados do artigo (05/11),** com
  `scripts/verificar_cars_milho.py`:
  - Os dados são o `corn_m51.mat` dos autores (milho no instrumento m5,
    umidade, 80 × 700), em `docs/fontes/cars/`, fora do git.
  - A receita é a do artigo: só centrado, 10 segmentos formados como no
    `plscvfold.m` (ordenados por `y`, em rodízio), N = 100, razão 0,9, 30
    repetições.
  - Com teto 10, o nosso CARS escolheu 1908 nm e 2108 nm juntas em 30 de
    30 repetições, o achado do artigo (500 de 500). RMSECV 0,0003 ±
    0,0000, contra 0,0006 do artigo; o PLS completo deu 0,0191, contra
    0,0229.
  - Com teto 5, 27 de 30; com teto 2, o padrão do `carspls.m`, 0 de 30,
    com RMSECV 0,2395.

  O algoritmo reproduz o artigo. O teto, que o artigo não informa, decide
  o resultado. Por isso o fator do teto passou à CV interna, e o modelo
  final, a usar os componentes que o CARS escolheu.

- **CARS contra o PLS em 10 partições (06/11),** com
  `scripts/comparar_cars_particoes.py` (`seed_split` 0 a 9, comparação
  pareada; DIARIO de 06/11):
  - **Tecator:** ΔR² mediano de +0,0016 no `protocolo` e +0,0001 no `fiel`,
    com cerca de 10 bandas. *Com a regra de réplicas de 09/11 (ADR 009;
    rodado de novo em 10/11):* +0,0012 no `protocolo` (8 de 10 não abaixo
    do PLS; p = 0,232) e +0,0018 no `fiel` (8 de 10; p = 0,037), com 6 e
    11 bandas medianas. O `protocolo` passou a ficar 0,0016 abaixo do
    `fiel` na mediana (de −0,0126 a +0,0114).
  - **Tecator nas 30 partições de exploração (10/11),** como a orientação
    pediu em 09/11, com `scripts/rodar_bracos_tecator_30.py`
    (`results/bracos_tecator_30_particoes.csv`), que nas `seed_split` 0 a
    9 reproduz os números acima: +0,0008 no `protocolo` (de −0,0124 a
    +0,0090; 20 de 30 não abaixo do PLS; p = 0,382; 8 bandas medianas) e
    +0,0020 no `fiel` (de −0,0518 a +0,0088; 20 de 30; p = 0,164; 12
    bandas). O `protocolo` fica 0,0011 abaixo do `fiel` na mediana (de
    −0,0179 a +0,0522). Com 30 partições, nenhum dos dois modos se
    distingue do PLS.
  - **Gasoline:** −0,0048 no `protocolo` (4 de 10 partições não abaixo do
    PLS; Wilcoxon p = 0,193) e −0,0123 no `fiel` (2 de 10; p = 0,020).
  - **O `protocolo` fica acima do `fiel` no Gasoline** (+0,0078 na
    mediana) e no bioprocess (uma partição). No Tecator, com a regra de
    réplicas nova, fica 0,0016 abaixo na mediana em 10 partições e 0,0011
    abaixo em 30, dentro da variação entre partições. Não há indício de
    que as adaptações enfraqueçam o método, mas também não há vantagem consistente delas.
  - **O RMSEP publicado:** Zhong et al. (2023), *Molecules* 28(15):5672,
    no mesmo Gasoline (divisão Kennard-Stone 45/15, só centragem, uma
    execução), dá 0,240 para o CARS-PLS e 0,180 para o PLS completo.
    Também ali o CARS fica abaixo do PLS completo. O nosso `protocolo`
    tem RMSEP mediano de 0,236 (faixa de 0,167 a 0,331) em 10 partições,
    com o valor publicado dentro da faixa. É uma referência só, e com
    outra divisão. No Tecator, ainda não há RMSEP publicado de CARS.
  - **Na divisão do artigo (06/11),** com `scripts/comparar_cars_zhong.py`:
    - O Kennard-Stone que começa pela amostra mais perto da média
      reproduz os três números do PLS completo da Tabela 3 (RMSEC 0,150,
      RMSECV 0,252, RMSEP 0,180), então a divisão é a mesma.
    - Com só centragem e leave-one-out, em 20 sementes, o nosso CARS deu
      RMSEP mediano de 0,226 com teto 5 (≤ 0,240 em 18 de 20) e 0,210 com
      teto 10 (19 de 20), contra 0,240 publicado.
    - O CARS, portanto, não fica abaixo do publicado no Gasoline. Uma
      primeira tentativa, com a variante do libPLS, não reproduzia o
      controle; está no DIARIO.
