# Verificação 3 — a extensão do que muda com o alvo correto

*Rodrigo Fernandes — 27/10/2026; seção da divergência fechada em 04/11/2026*

> **O que foi pedido:** Rode o pipeline completo com a coluna correta — PGSG inclusive, não só o PLS — para saber a extensão do que muda antes de escrever para o texto.

### Resposta curta

**O PGSG praticamente não muda. Quem muda é o PLS, que melhora.** Por isso a
distância entre os dois cresce: de 5,7% para 9,1%.

Este relatório cobre a Tabela 1 e a Seção 4.2. **A Seção 5.2, a Tabela 2 e
as figuras estão na parte B** (`verificacao_3b_secao_5_2.md`), e lá está o
achado principal: as portas publicadas correspondem às da inicialização, e
o protocolo de treino que o artigo declara não alcança quatro dos oito
valores publicados.

### A Tabela 1 do Tecator, refeita nas duas colunas

As linhas de rede são **mediana [mínimo; máximo]** entre 10 réplicas. O
pipeline original não fixa semente em lugar nenhum, então cada execução dá
um número diferente e uma medida única não diria nada.

| linha | publicado (R²) | coluna 0 = água | coluna 1 = gordura |
|---|---|---|---|
| PLS | 0,919 | **0,919** | **0,946** |
| PLS, 5-fold | 0,921 | 0,922 | 0,955 |
| Ours (ANOVA), teste único | 0,941 | 0,922 [0,80; 0,96] | 0,922 [0,84; 0,94] |
| Ours (ANOVA), 5-fold | 0,862 | 0,869 [0,82; 0,89] | 0,868 [0,68; 0,89] |
| Ours (VIP) | 0,903 | 0,909 [0,89; 0,95] | 0,930 [0,89; 0,95] |
| Ours (RF) | 0,938 | 0,933 [0,86; 0,95] | 0,937 [0,91; 0,97] |
| Random init | 0,871 | 0,888 [0,77; 0,92] | 0,912 [0,79; 0,93] |
| Plain CNN | 0,235 | −0,019 [−2,59; 0,21] | 0,005 [−0,53; 0,17] |

**Validação do protocolo.** A coluna 0 reproduz o publicado: PLS teste único
dá 0,919 / 0,296, e PLS em 5-fold dá 0,922 contra os 0,921 do manuscrito. Isso
valida a **partição, o escalonamento, a seleção de coluna e o H** — que é o
que o PLS exercita. Não valida o laço de treino das redes: para elas, o
publicado apenas cai dentro da dispersão entre sementes. No caso da Plain
CNN, na cauda dela: com as 10 réplicas da tabela o R² publicado (0,235)
fica logo acima da maior (0,21); com 50 sementes, fica no percentil 96 —
dentro da faixa, perto do topo (segundo anexo,
`scripts/verificar_divergencia_redes.py`). Uma versão anterior deste
relatório dizia "fora da faixa", conclusão tirada de 10 sementes; a
correção foi apontada pela orientação em 01/10.

### O H do PLS teve de ser refeito

O manuscrito determina, na linha 386, que "*Reported PLS results use H\*
throughout*", com H\* pela regra de um erro-padrão sobre LOO no treino. O
**H = 10 é o H\* da água**. Refazendo a regra para a gordura, com os mesmos
candidatos de 1 a 15:

| coluna | H\* | R² no teste |
|---|---|---|
| 0, água | 10 | 0,919 |
| 1, gordura | **12** | **0,946** |

A implementação da regra se valida contra a saída do próprio autor: para a
coluna 0 ela reproduz `H_min = 14`, `RMSECV = 0,2093`, `SE = 0,0269`,
`H\* = 10`, exatamente o que está em `revision_r1/one_se_output.txt`.

Isto corrige um número: com a gordura o PLS dá **0,946**, e não 0,9489 — este
último usa H = 10, que é o H da água.

### A distância entre o PGSG e o PLS

O manuscrito resume como "*a performance gap of approximately 6%*", comparando
o PGSG em 5-fold contra o PLS em teste único. O próprio manuscrito fornece o
número justo na linha 388 — PLS em 5-fold —, e a comparação correta é essa:

| | PLS 5-fold | PGSG 5-fold | lacuna |
|---|---|---|---|
| água | 0,922 | 0,869 | **5,7%** |
| gordura | 0,955 | 0,868 | **9,1%** |

A lacuna cresce cerca de 60%. **Não dobra** — a dispersão entre réplicas é
grande, e a mediana é a medida honesta aqui.

O mecanismo fica claro na comparação das réplicas: o PGSG em 5-fold vai de
0,869 (água) para 0,868 (gordura) — Wilcoxon pareado por semente p = 0,846,
Mann-Whitney p = 0,910. O pareamento aqui é legítimo: com a mesma semente as
camadas partem dos mesmos pesos (a porta vem do prior, sem sorteio) e as
folds são as mesmas; o Mann-Whitney vai junto para a conclusão não depender
disso. **Trocar o alvo não muda o PGSG.** O PLS,
que é determinístico, vai de 0,919 para 0,946. O aumento da distância vem
inteiramente do PLS.

A causa desse contraste não foi medida. Uma leitura plausível é que, com
ρ = −0,988 entre gordura e água, um modelo flexível atinge desempenho
equivalente prevendo qualquer das duas, enquanto o PLS, linear e calibrado
por H\*, se beneficia do alvo com melhor estrutura linear. **Isto é
interpretação, não resultado**; o que a tabela mostra é o contraste, não a
sua razão.

### O prior ANOVA ganha da inicialização aleatória?

| coluna | ANOVA | aleatório | diferença | Mann-Whitney |
|---|---|---|---|---|
| 0, água | 0,922 | 0,888 | +0,033 | **p = 0,021** |
| 1, gordura | 0,922 | 0,912 | +0,010 | p = 0,307 |

Na coluna publicada a vantagem existe. Na gordura, não se distingue do ruído.
Com duas ressalvas. Os dois braços usam critérios de parada diferentes — o
ANOVA para por paciência, o aleatório roda as 200 épocas —, o que favorece o
primeiro. E são 10 sementes por braço: na gordura, a mediana do ANOVA em
teste único varia de 0,908 a 0,942 entre blocos de 10 sementes (segundo
anexo), então a comparação nessa coluna é frágil. Na água, a mesma mediana
fica entre 0,921 e 0,924.

### Divergência com a reprodução da orientação (01/10; Plain CNN fechada em 04/11)

A orientação refez a reprodução de forma independente. **Bate exatamente**
em tudo o que é determinístico: coluna 0 = água; PLS 0,9191 / 0,2957;
RMSECV 0,2093 ± 0,0269 com H\* = 10; gordura com H\* = 12, 0,9462 /
0,2428. **Diverge em três braços de rede:**

| braço | esta reprodução | orientação |
|---|---|---|
| Plain CNN, gordura | 0,005 [−0,53; 0,17] | 0,410 [−0,02; 0,80] |
| PGSG 5-fold, gordura | 0,868 | 0,859 |
| PGSG ANOVA teste único, água | 0,922 | 0,932 |

Os quatro pontos de protocolo que ela pediu para conferir estão iguais aos
dela: `torch.manual_seed(s)` antes de instanciar o modelo, sementes 0 a 9;
`y` em 1-D na perda; a Plain CNN é o `BandSelectNet` do `band_select_net.py`,
com porta e prior; a paciência observa o teste no teste único e a fold no
5-fold.

Para saber se a diferença é só de semente, as mesmas linhas foram rodadas
com mais sementes, olhando a mediana de cada bloco de 10 (segundo anexo):

| braço | mediana por bloco de 10 sementes | orientação |
|---|---|---|
| ANOVA teste único, água (50 sementes) | 0,921 a 0,924 | 0,932 |
| PGSG 5-fold, gordura (30 sementes) | 0,868 a 0,876 | 0,859 |
| Plain CNN, gordura (50 sementes) | −0,001 a 0,071, máximo 0,17 | 0,410 |

Nos dois primeiros a diferença é pequena, mas fica fora da variação entre
blocos: provavelmente não é só a escolha das sementes. Na Plain CNN a
distribuição desta reprodução é **incompatível** com a dela — em 50
sementes nenhum treino passa de 0,17. Além da receita original, nove
variações de protocolo foram testadas nesse braço: 100 épocas, sem parada,
paciência 30, weight decay, a receita do modelo leve, lr 0,001, o prior da
água, o `y` sem padronizar e voltar ao melhor estado no teste. A mais
próxima, voltar ao melhor estado, dá mediana 0,161. Nenhuma chega a 0,41.

**Em aberto até 29/10.** Sem o script da orientação, não dava para saber de
que lado estava a diferença. Ela não afeta o PLS, nem as portas não
treinadas, nem a conclusão sobre a Seção 5.2.

#### A causa, na Plain CNN (29/10)

A orientação identificou a causa ao enviar o script dela
(`verify_plaincnn.py`, recebido em 29/10, não versionado aqui;
*atualização de 12/11: versionado, como chegou, em
`scripts/orientacao/verify_plaincnn.py`, com a autorização da orientação*). **A
diferença não está no protocolo de treino, e sim na inicialização da porta,
por um erro de chamada na reprodução da orientação.** As duas fábricas de
modelo do repositório do artigo não têm a mesma assinatura:

```
create_model_light(n_bands, n_outputs=1, prior_path=None)
create_model(n_bands, n_outputs=1, prior_type='anova', prior_path=None)
```

A reprodução da orientação chamou as duas com o caminho do prior como
terceiro argumento posicional:
- **no modelo leve**, ele cai em `prior_path`, o que está certo;
- **no modelo pesado**, cai em `prior_type`, e `prior_path` fica `None`.

Sem prior, a camada de porta começa em `randn(n_bands) * 0.01`, e o termo
KL é tomado contra uma referência uniforme. Ou seja, a Plain CNN da
orientação não tinha prior. Nenhuma das nove variações acima mexia na
inicialização da porta, e por isso nenhuma chegava a 0,41.

Conferido no código do artigo, por leitura:
- as duas assinaturas estão em `src/models/band_select_net_light.py:76` e
  `src/models/band_select_net.py:155`;
- o `scripts/train_proper.py`, a receita do modelo pesado, chama
  `create_model` com `prior_path=` nomeado. O modelo do artigo, portanto,
  tinha prior.

A implementação deste relatório instancia
`BandSelectNet(n_bands=100, n_outputs=1, prior_scores=prior)` direto, que é
a forma correta.

O script cruza dois fatores, a inicialização da porta e a receita de
treino, com 10 sementes por célula. Rodei aqui duas vezes, com resultado
idêntico (torch 2.14.1 em CPU; saída no terceiro anexo). Mediana [mínimo;
máximo]:

| alvo | porta | receita | orientação | esta máquina |
|---|---|---|---|---|
| gordura | ANOVA | `train_proper` (a deste relatório) | 0,000 [−1,49; 0,12] | 0,005 [−0,53; 0,17] |
| gordura | ANOVA | `train_light` | 0,056 [−6,74; 0,49] | −0,308 [−6,02; 0,13] |
| gordura | sem prior | `train_proper` | 0,039 [−0,02; 0,44] | −0,004 [−0,12; 0,45] |
| gordura | sem prior | `train_light` (a da orientação) | 0,361 [−0,02; 0,82] | 0,226 [−0,02; 0,85] |
| água | ANOVA | `train_proper` | 0,100 [−0,03; 0,17] | −0,019 [−2,59; 0,21] |
| água | ANOVA | `train_light` | −0,160 [−2,36; 0,40] | −0,038 [−94,25; 0,19] |
| água | sem prior | `train_proper` | 0,002 [−0,00; 0,35] | 0,004 [−0,00; 0,26] |
| água | sem prior | `train_light` | 0,037 [−5,92; 0,47] | 0,291 [−0,00; 0,64] |

As duas reproduções se encaixam, cada uma na sua célula. Nas duas
máquinas, "sem prior + `train_light`" é a única célula da gordura com
mediana claramente acima de zero, com faixa até 0,82–0,85, onde estão os
0,410 [−0,02; 0,80] da orientação. A célula deste relatório dá aqui
exatamente o que estava reportado: 0,005 [−0,53; 0,17]. A célula "ANOVA +
`train_light`" na gordura também repete, nesta máquina, a variação "receita
do modelo leve" do segundo anexo: −0,308 [−6,02; 0,13].

**O mesmo script, em máquinas diferentes, dá medianas diferentes nesse
braço.** Na água com porta ANOVA e `train_proper`, deu 0,100 na máquina da
orientação e −0,019 nesta. É evidência direta da instabilidade da Plain
CNN. Com essa troca, a observação da orientação de que o prior melhoraria a
Plain CNN na água (0,100 contra 0,002) inverte de direção nesta máquina
(−0,019 contra 0,004). Ela foi retirada pela orientação em 30/10.

**O que se conclui:**
- Nenhum fator sozinho explica a diferença: é interação entre a
  inicialização da porta e a receita.
- Nada disso é comparação entre braços. As faixas vão de −94 a +0,85, e
  diferenças de centésimos entre medianas de 10 sementes são ruído.
- O 0,235 publicado continua sendo um sorteio de uma distribuição com essa
  dispersão: percentil 96 em 50 sementes, como está acima. A conclusão
  qualitativa do artigo (a CNN pesada falha) se sustenta, e o número não.

**O que continua sem causa.** As outras duas linhas da primeira tabela
desta seção usam o modelo leve, em que a chamada da orientação estava
certa:
- o PGSG em 5-fold na gordura: 0,868 contra 0,859;
- o ANOVA em teste único na água: 0,922 contra 0,932.

A causa acima não as explica. A diferença de ambiente que aparece na Plain
CNN é candidata plausível, mas não foi medida nessas duas linhas.

### Ressalvas obrigatórias sobre estes números

1. **Nenhuma linha desta tabela é medida limpa de desempenho.** Os braços de
   teste único param observando o RMSE do próprio conjunto de teste, e o
   modelo final é o da última época. A linha de 5-fold tem o mesmo problema
   contra a fold de validação, e além disso usa um prior calculado sobre os
   172 do treino, que contêm as folds de validação. Reproduzi o protocolo
   como está, sem corrigir: o objetivo é medir o efeito do alvo com todo o
   resto igual.
2. **Duas réplicas colapsam** na coluna da gordura (uma fold cai para ~0). Por
   isso a tabela usa mediana; a média ficaria vários pontos deslocada.
3. **O desvio publicado do PLS em 5-fold não corresponde a nada.** O
   manuscrito registra 0,921 ± 0,018; a saída do próprio autor registra
   0,9218 ± 0,0439 nas mesmas folds. O desvio-padrão das cinco folds é
   0,0439 com ddof = 0 e 0,0491 com ddof = 1, e nenhum dos dois é 0,018 —
   valores a que a orientação chegou de forma independente.
4. **O prior também foi calculado sobre a água.** O `compute_priors.py`
   mapeia `'Fat'` para a coluna 0 (`{'Fat': 0, 'Water': 1, 'Protein': 2}`),
   então o arquivo `tecator_fat_anova.npy` do artigo é o prior da umidade —
   não só os resultados, o prior ANOVA, VIP e RF também. Achado da
   orientação, em 01/10. Nesta reprodução os priors são calculados sobre a
   coluna de cada linha da tabela: a coluna 0 com o prior da água, a coluna
   1 com o da gordura.
5. **A afirmação de semente fixa.** A linha 390 do manuscrito diz que os
   experimentos usam semente fixa 42 e que sementes diferentes produzem
   variação "<0,02 em R²". Nenhum script do pipeline do Tecator chama
   `torch.manual_seed`, e o braço ANOVA em teste único varia de 0,80 a 0,96
   entre as réplicas.

---

## Anexo 1 — saída de `scripts/verificar_pipeline_tecator.py`

Reproduzível com:

```bash
python scripts/verificar_pipeline_tecator.py
```

```
==============================================================================
 VERIFICACAO 3 - O PIPELINE DO TECATOR COM O ALVO CORRETO
==============================================================================

  replicas por linha: 10   (o pipeline original nao
  fixa semente; cada execucao dele da um numero diferente)

==============================================================================
 CONFERENCIA: PEGUEI OS MODELOS CERTOS?
==============================================================================

  O manuscrito declara as contagens de parametros. Se batem, o
  mapeamento 'Ours' = leve e 'Plain CNN' = pesada esta certo.

  Ours, Tecator (leve, 100 bandas)        1,765  manuscrito    1,765  ok
  Ours, Gasoline (leve, 401 bandas)       6,882  manuscrito    6,882  ok
  Plain CNN (pesada, 100 bandas)        109,221  manuscrito  109,221  ok

  nota: a 'Plain CNN' tambem tem a camada de portas e o prior
  ANOVA - e a versao pesada do mesmo modelo, nao uma CNN sem
  gating. O rotulo da tabela e deles; reproduzi o que o
  train_proper.py faz.

==============================================================================
 COLUNA 0 (rotulada 'Fat') = AGUA
==============================================================================

  treino (172, 100)  teste (43, 100)
  priors calculados sobre esta coluna:
   Computing ANOVA F-statistic...
   Computing Random Forest importance (100 trees)...

  H* por LOO+1SE: H_min=14, RMSECV=0.2093, SE=0.0269 -> H*=10
  Ours (ANOVA), teste unico    ok (10 replicas)
  Ours (VIP), teste unico      ok (10 replicas)
  Ours (RF), teste unico       ok (10 replicas)
  Random init, teste unico     ok (10 replicas)
  Plain CNN, teste unico       ok (10 replicas)
  Ours (ANOVA), 5-fold         ok (10 replicas)

==============================================================================
 COLUNA 1 (rotulada 'Water') = GORDURA
==============================================================================

  treino (172, 100)  teste (43, 100)
  priors calculados sobre esta coluna:
   Computing ANOVA F-statistic...
   Computing Random Forest importance (100 trees)...

  H* por LOO+1SE: H_min=14, RMSECV=0.1874, SE=0.0245 -> H*=12
  Ours (ANOVA), teste unico    ok (10 replicas)
  Ours (VIP), teste unico      ok (10 replicas)
  Ours (RF), teste unico       ok (10 replicas)
  Random init, teste unico     ok (10 replicas)
  Plain CNN, teste unico       ok (10 replicas)
  Ours (ANOVA), 5-fold         ok (10 replicas)

==============================================================================
 TABELA 1, TECATOR - PUBLICADO x AGUA x GORDURA REAL
==============================================================================

  As linhas de rede sao MEDIANA [minimo;maximo] entre replicas.
  O publicado e uma medida unica, e o +- dele e entre folds.

  nota sobre o 'PLS, 5-fold': o manuscrito (linha 388) publica
  0.921 +- 0.018, mas a saida do proprio autor
  (revision_r1/one_se_output.txt) registra 0.9218 +- 0.0439 nas
  mesmas folds. A media bate; o desvio, nao.

                                PUBLICADO             col 0 = agua          col 1 = gordura
  R2                          
  PLS                               0.919                    0.919                    0.946
  PLS, 5-fold                       0.921                    0.922                    0.955
  Ours (ANOVA), teste unico         0.941        0.922 [0.80;0.96]        0.922 [0.84;0.94]
  Ours (ANOVA), 5-fold              0.862        0.869 [0.82;0.89]        0.868 [0.68;0.89]
  Ours (VIP), teste unico           0.903        0.909 [0.89;0.95]        0.930 [0.89;0.95]
  Ours (RF), teste unico            0.938        0.933 [0.86;0.95]        0.937 [0.91;0.97]
  Random init, teste unico          0.871        0.888 [0.77;0.92]        0.912 [0.79;0.93]
  Plain CNN, teste unico            0.235      -0.019 [-2.59;0.21]       0.005 [-0.53;0.17]

  RMSE                        
  PLS                               0.296                    0.296                    0.243
  PLS, 5-fold                         ---                    0.262                    0.203
  Ours (ANOVA), teste unico           ---        0.291 [0.21;0.47]        0.292 [0.25;0.41]
  Ours (ANOVA), 5-fold              0.361        0.352 [0.32;0.40]        0.357 [0.32;0.50]
  Ours (VIP), teste unico           0.323        0.314 [0.24;0.34]        0.277 [0.23;0.34]
  Ours (RF), teste unico            0.258        0.269 [0.23;0.39]        0.262 [0.19;0.32]
  Random init, teste unico          0.373        0.347 [0.29;0.50]        0.310 [0.27;0.48]
  Plain CNN, teste unico            0.909        1.049 [0.93;1.97]        1.044 [0.95;1.29]

==============================================================================
 REPLICAS ANOMALAS NO 5-FOLD
==============================================================================

  Antes de comparar qualquer coisa: alguma replica colapsou? Uma
  fold que colapsa move a media da replica inteira, e a media
  entre replicas depois.

  col 0 = agua:
    nenhuma
  col 1 = gordura:
    semente 5: media 0.678  folds [0.883, 0.903, 0.83, 0.786, -0.013]
    semente 7: media 0.694  folds [0.865, 0.877, 0.859, 0.876, -0.008]

  -> e por isso que a tabela acima usa MEDIANA, nao media.

==============================================================================
 A DISTANCIA ENTRE O PGSG E O PLS
==============================================================================

  O manuscrito resume como 'a performance gap of approximately
  6%' (PGSG 0.862 contra PLS 0.919). Essa conta compara 5-fold
  com teste unico. O proprio manuscrito da o numero justo na
  linha 388: PLS em 5-fold = 0.921+-0.018. Refaco das duas
  formas, para as duas colunas.

  col 0 = agua  (H* = 10)
    contra PLS teste unico  PLS 0.919   PGSG 0.869   lacuna mediana 5.5%  faixa [2.8;10.5]
    contra PLS 5-fold       PLS 0.922   PGSG 0.869   lacuna mediana 5.7%  faixa [3.0;10.8]

  col 1 = gordura  (H* = 12)
    contra PLS teste unico  PLS 0.946   PGSG 0.868   lacuna mediana 8.3%  faixa [5.8;28.4]
    contra PLS 5-fold       PLS 0.955   PGSG 0.868   lacuna mediana 9.1%  faixa [6.6;29.0]

  PGSG 5-fold, agua x gordura: Wilcoxon pareado p=0.846, Mann-Whitney p=0.910
  medianas: agua 0.869  gordura 0.868
  -> o PGSG praticamente nao muda. Quem muda e o PLS, que
     melhora; e e dai que vem o aumento da lacuna.

==============================================================================
 O PRIOR ANOVA GANHA DA INICIALIZACAO ALEATORIA?
==============================================================================

  O artigo argumenta que sim, comparando 0.941 com 0.871 - duas
  medidas unicas. Com replicas:

  O teste e Mann-Whitney, de amostras independentes, e NAO um
  pareado por semente: a mesma semente nao emparelha nada entre
  os dois bracos, porque o braco sem prior sorteia as gates
  primeiro e as camadas seguintes acabam com pesos diferentes.

  col 0 = agua       ANOVA 0.922   aleatorio 0.888   dif das medianas +0.033   Mann-Whitney p=0.021
  col 1 = gordura    ANOVA 0.922   aleatorio 0.912   dif das medianas +0.010   Mann-Whitney p=0.307

  ressalva: o braco ANOVA para observando o proprio teste e o
  aleatorio roda as 200 epocas. Sao criterios de parada
  diferentes, e isso favorece o braco com parada.

==============================================================================
 TABELA 2 - AS GATES SAO APRENDIDAS?
==============================================================================

  Duas coisas separadas, para nao confundir o que e leitura de
  codigo com o que e medida:

  (a) POR LEITURA: o analyze_gates.py cria um modelo novo e le as
      gates. Nao ha torch.load ali, e nenhum script do pipeline
      do Tecator chama torch.save - logo nao existe modelo
      treinado para carregar. O que ele reporta e a inicializacao.

  (b) POR MEDIDA: quanto o treino move as gates? SEMENTE 0 SO -
      ilustracao. A medida em 10 sementes, e com outros lr, epocas
      e KL, esta em scripts/verificar_varredura_treino.py.

  coluna 0 (agua):
    sem treinar        banda topo  40 (931 nm, peso 0.215)  corr. com o prior 0.348
    depois de treinar  banda topo  40 (931 nm, peso 0.219)  corr. com o prior 0.335
    logits: faixa inicial 32.2 (de -16.1 a 16.1)
            deslocamento no treino: maior 1.47, mediano 0.12
            referencia do Adam em 200 passos a lr=0.01: ~2.0 (ordem de grandeza, nao teto rigido)
            distancia do 2o ao 1o colocado: 11.47

  coluna 1 (gordura):
    sem treinar        banda topo  40 (931 nm, peso 0.217)  corr. com o prior 0.353
    depois de treinar  banda topo  40 (931 nm, peso 0.216)  corr. com o prior 0.342
    logits: faixa inicial 32.2 (de -16.1 a 16.1)
            deslocamento no treino: maior 1.93, mediano 0.12
            referencia do Adam em 200 passos a lr=0.01: ~2.0 (ordem de grandeza, nao teto rigido)
            distancia do 2o ao 1o colocado: 11.61

  publicado na Tabela 2: 931 nm (0.215), corr. com o prior 0.348
```

## Anexo 2 — saída de `scripts/verificar_divergencia_redes.py`

Reproduzível com:

```bash
python scripts/verificar_divergencia_redes.py
```

```

==============================================================================
 1. OS OITO VALORES DA TABELA 2, UM A UM, NO PROTOCOLO DECLARADO
==============================================================================

  train_light.py: lr 0.01, 200 epocas, paciencia 30 no teste, KL 0.001.
  10 sementes. 'reproduz' = igual ao publicado na precisao publicada.
   Computing ANOVA F-statistic...

  TECATOR
    banda do topo (nm)         publicado     931   reproduz em 10/10   medido 931 a 931
    peso da banda do topo      publicado   0.215   reproduz em  3/10   medido 0.213 a 0.219
    correlacao com o prior     publicado   0.348   reproduz em  0/10   medido 0.332 a 0.34
    regiao C-H (%)             publicado     7.4   reproduz em  0/10   medido 7.2 a 7.3
    regiao O-H (%)             publicado     3.5   reproduz em  5/10   medido 3.5 a 3.6
   Computing ANOVA F-statistic...

  GASOLINE
    banda do topo (indice)     publicado     154   reproduz em 10/10   medido 154 a 154
    peso da banda do topo      publicado    0.13   reproduz em  0/10   medido 0.102 a 0.11
    correlacao com o prior     publicado   0.507   reproduz em  0/10   medido 0.487 a 0.5

  -> 4 compativeis (reproduzem em ao menos uma semente), 4 excluidos (em nenhuma)

==============================================================================
 2. QUANTO A MEDIANA DE 10 REPLICAS DEPENDE DAS SEMENTES
==============================================================================

  Mesmo protocolo do verificar_pipeline_tecator.py, mais sementes.
  Se as medianas por bloco de 10 variam pouco, uma diferenca maior que
  essa variacao nao se explica so pela escolha das sementes.
   Computing ANOVA F-statistic...
   Computing Random Forest importance (100 trees)...

  coluna 0 (agua)
    Plain CNN, teste unico   50 sementes: mediana   0.025  faixa [-82.16; 0.28]
                             medianas por bloco de 10: -0.019, 0.113, 0.096, -0.053, 0.063
                             0.235 publicado: percentil 96 das 50
    ANOVA, teste unico       50 sementes: mediana   0.923  faixa [0.80; 0.96]
                             medianas por bloco de 10: 0.922, 0.921, 0.924, 0.921, 0.922
   Computing ANOVA F-statistic...
   Computing Random Forest importance (100 trees)...

  coluna 1 (gordura)
    Plain CNN, teste unico   50 sementes: mediana   0.010  faixa [-1.70; 0.17]
                             medianas por bloco de 10: 0.005, 0.023, -0.001, 0.007, 0.071
                             0.235 publicado: percentil 100 das 50
    ANOVA, teste unico       50 sementes: mediana   0.930  faixa [0.84; 0.97]
                             medianas por bloco de 10: 0.922, 0.908, 0.942, 0.936, 0.937
    PGSG 5-fold              30 sementes: mediana   0.872  faixa [0.67; 0.91]
                             medianas por bloco de 10: 0.868, 0.869, 0.876

  a orientacao obteve: ANOVA teste unico na agua 0.932, PGSG 5-fold na
  gordura 0.859, Plain CNN na gordura 0.410 [-0.02; 0.80]

==============================================================================
 3. PLAIN CNN NA GORDURA - VARIACOES DE PROTOCOLO, 10 SEMENTES
==============================================================================

  train_proper.py: 200 epocas, paciencia 20 no teste, KL 1e-4, sem
  weight decay, modelo da ultima epoca. Cada linha muda uma coisa.

   Computing ANOVA F-statistic...
   Computing Random Forest importance (100 trees)...
  train_proper como esta                   mediana   0.005  faixa [-0.53; 0.17]
  100 epocas (default do train_model)      mediana   0.005  faixa [-0.50; 0.19]
  sem parada antecipada                    mediana  -0.945  faixa [-11.42; 0.06]
  paciencia 30                             mediana   0.007  faixa [-1.45; 0.13]
  weight decay 1e-4                        mediana   0.009  faixa [-0.24; 0.25]
  receita do modelo leve                   mediana  -0.308  faixa [-6.02; 0.13]
  lr 0.001                                 mediana  -0.021  faixa [-2.91; 0.90]
   Computing ANOVA F-statistic...
   Computing Random Forest importance (100 trees)...
  prior da agua, alvo gordura              mediana   0.006  faixa [-10.23; 0.20]
  voltar ao melhor estado no teste         mediana   0.161  faixa [0.01; 0.27]
  y sem padronizar (preprocessing.py)      mediana  -1.727  faixa [-6.33; -0.19]

  a orientacao obteve mediana 0.410, faixa [-0.02; 0.80]
```

## Anexo 3 — saída de `verify_plaincnn.py` (script da orientação, 29/10)

Rodado duas vezes em 29/10, com saída idêntica; torch 2.14.1+cpu, numpy
2.5.2, scikit-learn 1.9.0.

```
python verify_plaincnn.py --repo <código do artigo>
==============================================================================
 PLAIN CNN (heavy BandSelectNet), Tecator -- gate init x training recipe
==============================================================================
  10 seeds per cell.  Published Table 1 value: 0.235

  --- column 0 = water (what was published) ---
  gate init             recipe             median R2  range               
  ANOVA prior           train_proper     -0.019  [-2.59; 0.21]
  ANOVA prior           train_light      -0.038  [-94.25; 0.19]
  randn*0.01 (no prior) train_proper      0.004  [-0.00; 0.26]
  randn*0.01 (no prior) train_light       0.291  [-0.00; 0.64]

  --- column 1 = fat (the correct target) ---
  gate init             recipe             median R2  range               
  ANOVA prior           train_proper      0.005  [-0.53; 0.17]
  ANOVA prior           train_light      -0.308  [-6.02; 0.13]
  randn*0.01 (no prior) train_proper     -0.004  [-0.12; 0.45]
  randn*0.01 (no prior) train_light       0.226  [-0.02; 0.85]

==============================================================================
 WHY: the gate the heavy CNN starts from
==============================================================================
  ANOVA prior    logits [ -16.12;  16.12]   top gate 0.2166   on the top band 21.7% of the weight
                 bands with |logit| > 10: 3.0%   gate entropy 4.058 (max 4.605)
  randn*0.01     logits [  -0.03;   0.03]   top gate 0.0101   on the top band 1.0% of the weight
                 bands with |logit| > 10: 0.0%   gate entropy 4.605 (max 4.605)
```
