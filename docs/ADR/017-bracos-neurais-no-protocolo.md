# ADR 017 — Os braços neurais no protocolo

**Data:** 2026-11-12
**Status:** proposto

## Contexto

O Estágio 3 do pipeline pede os braços neurais: `mlp_full` (B1),
`mlp_weighted` (B2), `gate_uniform` (B3) e `gate_prior` (B4), com três
critérios de aceitação:
1. o B2 com a porta congelada em 1,0 reproduz o B1;
2. o B4 reproduz o modelo de referência;
3. um teste compara os hiperparâmetros efetivos dos braços e falha se
   divergirem além do permitido.

E uma regra: o regressor é "byte a byte o mesmo" em todos os braços (mesma
arquitetura, inicialização dada a semente, otimizador e orçamento). Entre
B1 e B2 só muda a ponderação; entre B2 e B4, o gradiente na porta; entre B3
e B4, a inicialização da porta.

Depois do parecer de 01/10, do ADR 013 e da resposta de 12/11, o PROTOCOLO
tem sete braços de rede: B1, B2, B2'(c), B3, B4-fiel, B4-limpo e B5(c).
Nenhum existe no código. **Eles são o que falta para congelar o protocolo:**
o `c` do TOST de cada conjunto sai do deslocamento da porta no B4-limpo
medido sob este protocolo (PROTOCOLO, "A grade de `c`").

Este ADR propõe o desenho antes de qualquer código. Duas perguntas abertas
desde agosto entram aqui: a 3 (vendorizar o modelo de referência) e a 7 (o
prior dentro da validação cruzada).

**O que foi lido** no código do artigo (`docs/fontes/prior-guided-spectral-gating-main/`,
fora do git, sem alteração):
- `src/models/band_select_net_light.py`: a porta `SpectralGatingLayer` e o
  `BandSelectNetLight` (porta → `fc1` 16 → BatchNorm → ReLU → dropout 0,5 →
  `fc2`), cerca de 2 mil parâmetros;
- `scripts/train_light.py`: Adam, lr 0,01, `weight_decay` 1e-4 em todos os
  parâmetros, KL 0,001, até 200 épocas em lote único, paciência 30
  **olhando o teste**;
- `src/data/compute_priors.py`: o prior ANOVA (`f_regression`, normalizado
  por mínimo e máximo);
- `src/data/preprocessing_fixed.py`: Z-score de X e de y ajustado no treino.

**Três detalhes do código que pesam no desenho:**
- **O modelo final é o da última época, não o da melhor.** O
  `train_light.py` para quando a paciência acaba e avalia os pesos daquele
  momento, 30 épocas depois do melhor ponto.
- **Sem prior, a porta começa em `randn(p) × 0,01`**, sorteada antes da
  `fc1` ser criada. Um B3 assim gasta números aleatórios que o B4 não gasta,
  e a `fc1` dos dois sai diferente com a mesma semente.
- **A referência do KL é o prior com `clip`, sem normalizar para somar 1.**
  Com prior, `prior_probs` é `clip(s)`; sem prior, é o uniforme `1/p`.

## Decisão proposta

### O modelo

**Usar o `BandSelectNetLight` do artigo sem editar**, só o arquivo
`band_select_net_light.py`, vendorizado em `src/tcc/vendor/pgsg/` com o
SHA-256 registrado e um teste que falha se o hash mudar. Os braços
envolvem o modelo e ajustam a porta **depois** de construí-lo, sem tocar
no arquivo. **Depende de autorização** (Em aberto, item 1).

**Construção igual em todo braço.** O modelo é sempre construído do mesmo
jeito (`prior_scores=None`, com a mesma semente), para que a sequência de
números aleatórios até a `fc1` seja idêntica. Depois a porta de cada braço
é escrita por cima. Assim a `fc1`, o BatchNorm e a `fc2` saem byte a byte
iguais entre os braços, e um teste confere isso.

### Os braços

Todos usam o mesmo regressor, otimizador, regra de parada e orçamento. Só
mudam as quatro colunas:

| braço | porta | porta inicial | gradiente na porta | L2 na porta | referência do KL |
|---|---|---|---|---|---|
| B1 | não há (multiplicador 1) | — | — | — | sem KL |
| B2 | sim | `logit(clip(s))` | não | — | inerte |
| B2'(c) | sim | `c · logit(clip(s))` | não | — | inerte |
| B3 | sim | 0 (uniforme exato) | sim | não | uniforme `1/p` |
| B4-fiel | sim | `logit(clip(s))` | sim | **sim** | `clip(s)` |
| B4-limpo | sim | `logit(clip(s))` | sim | não | `clip(s)` |
| B5(c) | sim | `c · logit(clip(s))` | sim | não | `clip(s)` |

- **B3 começa no uniforme exato** (logits zero), e não em `randn × 0,01`,
  pelo motivo do Contexto. Com logits zero, a porta inicial é `1/p`, que é
  também a referência do KL do B3: "porta ancorada no uniforme", como a
  orientação descreveu em 12/11.
- **B2 e B2' com a porta congelada** não recebem gradiente nem L2, e o KL
  é constante. O teste de sanidade do pipeline (B2 com a porta em 1,0
  igual ao B1) entra como teste.
- **O B4-fiel** só difere do B4-limpo pelo L2 na porta. A parada continua
  na fold interna, nunca no teste.
- **B5(1) é o B4-limpo e B2'(1) é o B2**, por construção; um teste confere.

### O treino e a parada

- **Dados:** depois do SNV do `evaluate()`, Z-score de X e de y ajustado no
  subconjunto de ajuste, como no artigo. A previsão volta à escala de y.
- **Parada antecipada numa fold interna:** a validação da primeira fold de
  `cv_folds` é o conjunto de parada; as outras linhas do treino ajustam a
  rede. Lote único, Adam, lr 0,01, até 200 épocas, paciência 30, L2 1e-4 no
  MLP, KL 0,001.
- **Modelo final: os pesos da melhor época** no conjunto de parada, e não os
  da última como no artigo. Escolha minha em 12/11, a confirmar com a
  orientação (Em aberto, item 2).
- **Sem reajuste no treino inteiro:** as linhas da fold de parada não
  ajustam a rede. Reajustar com o número de épocas encontrado é a
  alternativa, registrada e não adotada, porque o número de épocas depende
  do tamanho do conjunto.
- **`rmse_cv`:** o RMSE no conjunto de parada, na melhor época. É otimista,
  porque o mesmo conjunto escolheu a época, e isso é declarado.

### O prior (pergunta 7)

**O prior é calculado só nas linhas que ajustam a rede**, nunca na fold de
parada nem no teste. É a mesma regra dos seletores clássicos: nada que
decide o modelo vê a validação que o julga. O teste anti-vazamento
equivalente ao do ADR 011: perturbar o `y` da fold de parada não pode
mudar o prior nem a porta inicial.

### Sementes e threads

- `rng_algo` gera a semente do torch; com `seed_algo` igual, o treino é
  idêntico (conferido por teste).
- Uma thread no torch (`torch.set_num_threads(1)`), pelo mesmo motivo do
  script de rodar: o `wall_time` é resultado.

### O que cada braço de porta registra

Em `hyperparams`, para as medidas da H8 (PROTOCOLO) e o `c` do TOST: a
época de parada; o deslocamento θ_final − θ_inicial por banda (maior e
mediana do valor absoluto); a fração de bandas com |θ| menor; a correlação
entre o deslocamento e −θ_inicial; e `g`, a distância inicial entre o 1º e
o 2º logit. `band_scores` é a porta final.

### Orçamento

`n_fits` = 1 por treino; as épocas vão em `hyperparams`. Como no GA-PLS,
`n_fits` de rede não é comparável em custo com o dos braços clássicos, e
isso é declarado.

## Em aberto, a confirmar com a orientação

1. **Vendorizar o arquivo do artigo num repositório público.** A cópia
   cedida não tem arquivo de licença. O repositório declarado no artigo é
   público, mas código público sem licença não autoriza cópia. A
   alternativa é reimplementar o modelo, de poucas dezenas de linhas, e testar a
   equivalência numérica contra a cópia local, sem versioná-la.
2. **Melhor época ou última época.** O artigo fica com a última. Escolhi
   a melhor em 12/11, que é o padrão de parada antecipada, em todos os
   braços. O B4-fiel poderia ficar com a última, para estar mais perto do
   artigo; não adotado, a confirmar.
3. **Uma fold de parada, sem reajuste.** A rede deixa de usar cerca de 20%
   do treino.
4. **A definição exata do `c` do TOST.** `g` muda de partição para
   partição, porque o prior muda. Fixado em 12/11, antes de medir:
   `c_TOST` = mediana, nas `seed_split` 0–29, de `d_s / g_s`, calculada
   partição a partição; o PROTOCOLO foi atualizado. A confirmar com a
   orientação junto com a grade.
5. **`n_fits` = 1 por treino.**

## Consequências

- A implementação (F2) só começa depois de decidido o item 1; os itens 2
  e 4 foram escolhidos em 12/11.
- Com os braços prontos, mede-se `c_TOST` nos quatro conjuntos e ele vai
  para o PROTOCOLO antes da varredura (F3), e depois a varredura de `c`
  sob o protocolo (F4).
- A reprodução do B4 contra o artigo (critério 2 do pipeline) usa o modo
  da literatura, com a parada no teste como no original. Fica para depois
  da F2.

## Implementação (12/11/2026)

**Item 1 resolvido pela alternativa, por decisão minha:** o modelo foi
**reimplementado** em `src/tcc/arms/gate.py` (`GateNet`), sem copiar o
arquivo do artigo. A cópia local continua fora do git e serve só de
referência num teste. Se a orientação autorizar a vendorização, dá para
trocar depois.

- **Equivalência com o original** (`tests/test_gate.py`, pulado se a cópia
  local não existir): com a mesma semente, os parâmetros nascem iguais
  (1.765 no Tecator, o número do artigo); com a mesma porta, o KL, a saída
  e dez passos de treino com o Adam do artigo dão resultado idêntico, bit a
  bit. O teste carrega o original sem gravar `__pycache__` na pasta dele.
- **Os braços** são fábricas: `mlp_full` (B1), `mlp_weighted` (B2),
  `mlp_weighted_scaled(c=…)` (B2'), `gate_uniform` (B3),
  `gate_prior_faithful` (B4-fiel), `gate_prior` (B4-limpo) e
  `gate_prior_scaled(c=…)` (B5).
- **18 testes:** a equivalência com o original; o regressor byte a byte
  igual nos sete braços; os hiperparâmetros que podem diferir; B2 com a
  porta em 1,0 igual ao B1; B5(1) igual ao B4-limpo e B2'(1) igual ao B2;
  porta congelada que não anda e treinável que anda; porta inicial e
  referência do KL de cada braço; L2 na porta só no B4-fiel; o prior que
  ignora a fold de parada, com o controle de que ele vê as linhas de
  ajuste; melhor época; semente; orçamento e thread restaurada.
- **Oito mutações, todas pegas:** prior com a fold de parada, B3 com
  `randn`, L2 na porta em todo braço, última época, KL do B3 no prior,
  porta congelada com gradiente, regressor diferente no B3 e `c` ignorado.
  A de vazamento é pega também pelo teste específico, sozinho. Arquivo
  restaurado com o hash conferido.
- **`requirements.txt`:** o torch (2.14.1+cpu) estava instalado desde 01/10,
  mas não listado. Entrou, com o índice do PyTorch.
- **Ponta a ponta pelo `evaluate()`,** Tecator, `seed_split` 0, só para
  conferir o encanamento: os sete braços rodam, cada um em menos de 1 s.
  No B4-limpo, `g` = 11,96 e `d` = 0,344; no B4-fiel, `d` = 0,981; a
  banda do topo não troca no B4 nem no B5(0,026). São números de uma
  partição, piloto.
- Suíte inteira: 192 passaram, 1 pulado.

## O `c` do TOST medido (F3, 12/11/2026)

`scripts/medir_c_tost.py`, B4-limpo, `seed_split` 0–29, `seed_algo` 0,
quatro processos com uma thread; o script não grava nem imprime o
desempenho no teste. `c_TOST`: Tecator 0,0306, Gasoline 0,0289, Mango
0,0417 e bioprocess 0,1140. Tabela e ressalva no PROTOCOLO ("Os `c_TOST`
medidos"). A banda do topo não trocou em nenhuma das 120 partições. Tempo
mediano de um treino: 0,2 s no Gasoline, 0,4 s no Tecator, 2,3 s no Mango
e 11,5 s no bioprocess.

**Em aberto, novo (6):** no Mango, em 7 de 30 partições, a parada
antecipada escolheu uma época de 1 a 18, duas delas a primeira. A receita
do artigo pode não servir a conjuntos grandes em lote único. Não mudei
nada.

## A varredura de `c` (F4, 12/11/2026, piloto)

`scripts/varrer_c.py`, resultados e leitura no DIARIO de 12/11. O
deslocamento não depende de `c`; no `c_TOST` o topo quase não troca; um
pouco abaixo dele, troca. O Δ fica perto de zero no Tecator, no Gasoline e
no bioprocess.

**Em aberto, novo (7), o mais urgente:** no Mango, a receita de treino do
artigo falha sob este protocolo. Os 570 treinos deram R² de teste abaixo
de 0,7 (mediana ~0,5, contra 0,86 do PLS completo), e 114 pararam até a
época 20, com R² mediano de 0,002. O `c_TOST` do Mango foi medido nesse
treino e fica suspenso até a orientação decidir. Agrava o item 6.

**Diagnóstico do item 7 (12/11, só no treino;
`scripts/diagnosticar_rede_mango.py`, DIARIO de 12/11):** no Mango a rede
não ajusta nem o treino em 200 épocas de lote único; com a porta, o começo
é um platô em que a paciência de 30 se esgota; o dropout não é a causa; com
até 2.000 épocas a rede chega ao nível do PLS na fold de parada, mas com
saltos de instabilidade da taxa 0,01. Nenhuma receita foi adotada.

