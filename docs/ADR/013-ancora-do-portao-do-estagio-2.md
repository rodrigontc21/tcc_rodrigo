# ADR 013 — Âncora do portão do Estágio 2, após o achado do alvo do Tecator

**Data:** 2026-09-30
**Status:** aceito (04/11/2026). A orientação condicionou o aceite, em
29/10, aos acréscimos da seção "O que o Δ mede": "Com essas adições, o ADR
013 passa a aceito." A parte do decaimento de peso nessa seção veio da
mensagem dela de 30/10, e a nota sobre a Plain CNN é acréscimo meu. As duas
ainda não foram vistas por ela.

## Contexto

O portão de validação do Estágio 2 (ADR 005, modo
`evaluate_against_literature`) previa comparar os resultados deste trabalho
no Tecator contra os valores publicados em pgsg_0 — R² 0,919 e RMSE 0,296.

Em 29/09 ficou estabelecido que aqueles valores descrevem **água**, não
gordura. O `data/raw/tecator/targets.csv` do repositório declarado na
publicação tem o cabeçalho e o conteúdo em ordens diferentes: a coluna 0,
rotulada `Fat`, contém a água. Todos os scripts selecionam `y[:, 0]`.

A orientação aceitou o achado no mesmo dia, e determinou, palavra dela:

> o portão de validação do Estágio 2 previa comparação contra os valores
> publicados do Tecator. Esses valores estão suspensos até a verificação
> fechar. Você deve usar como âncora a própria reexecução do protocolo do
> artigo com o alvo correto, e registrar isso em ADR.

As três verificações que ela pediu foram fechadas em 29 e 30/09 e estão
registradas no DIARIO. Este ADR registra a âncora que substitui os valores
suspensos.

## Decisão

**O portão do Estágio 2 deixa de comparar contra os números publicados de
pgsg_0 no Tecator.** A âncora passa a ser a reexecução do protocolo daquele
artigo, feita neste trabalho, com o alvo correto.

O protocolo da âncora é o do artigo, lido do código dele e reproduzido em
`scripts/verificar_pipeline_tecator.py`:

- partição `train_test_split(test_size=0.2, random_state=42)`, 172/43;
- Z-score de X e de y, ajustado no treino (`src/data/preprocessing_fixed.py`);
- PLS com **H\* pela regra de um erro-padrão sobre LOO no treino**, candidatos
  de 1 a 15, `SE(RMSE) = SE(MSE) / (2·RMSE)`, como `manuscript_R2.tex:386`
  determina — e **não** H = 10 fixo, que é o H\* da água;
- alvo **selecionado por nome**, nunca por posição, como o ADR 004 já exige.

Valores de referência medidos em 30/09, com a gordura:

| medida | água (o que foi publicado) | **gordura (a âncora)** |
|---|---|---|
| H\* por LOO + 1SE | 10 | **12** |
| PLS, teste único: R² / RMSE | 0,919 / 0,296 | **0,946 / 0,243** |
| PLS, 5-fold no treino: R² / RMSE | 0,922 / 0,262 | **0,955 / 0,203** |

A coluna da água é mantida na tabela como controle: ela reproduz os números
publicados na terceira casa, o que é a prova de que o protocolo reproduzido
é o do artigo, e não uma aproximação.

## Consequências

Este ADR está **proposto**. Tudo que segue é consequência *condicionada à
aprovação da orientação* — um ADR proposto não altera por si o que já foi
aceito. *(Nota de 04/11: o ADR passou a aceito. O que depende dos ADRs 005
e 010, nos dois primeiros itens abaixo, continua dependendo do parecer
sobre eles.)*

- **ADR 005** (status: aceito, implementado em 14/09) — o modo
  `evaluate_against_literature` continua existindo, mas para o Tecator a
  referência passaria a ser esta tabela, e não a Tabela 1 de pgsg_0. A
  divisão sequencial 172/43 do Tecator, aprovada em 01/09, **não é a do
  artigo** — o código dele usa `train_test_split(test_size=0.2,
  random_state=42)` nos dois conjuntos. Retirá-la de uso depende de parecer
  sobre o ADR 005, que é aceito; até lá, o fato fica registrado e nada muda.
  O Gasoline não é afetado: tem alvo único (octano), e o PLS com H\* = 5
  reproduz os valores publicados (R² 0,9752, RMSE 0,1453).
- **ADR 010** (status: proposto) — a inferência que ele fazia sobre a divisão
  do Gasoline ganha fonte no código. Isso reforça o ADR 010, mas ele segue
  proposto e depende do mesmo parecer.
- **ADR 004** — a conclusão "nenhum resultado do paper está comprometido"
  não se sustenta; o ADR 004 ganhou, em 30/09, um adendo datado que registra
  isso, sem mudar a decisão dele para este trabalho. Não é decisão deste ADR.
- **Estágio 3, braço B4** — reproduzir o modelo publicado passa a significar
  reproduzir um modelo treinado em água. Se o objetivo do B4 for comparar
  contra o artigo, ele herda o alvo do artigo; se for comparar contra o
  melhor PLS possível, usa a gordura. São coisas diferentes e a escolha
  precisa ser explícita. O desdobramento do B4 pedido pela orientação está
  na seção "O braço B4", abaixo.

## O braço B4 (acrescentado em 21/10/2026)

Pedido do parecer da orientação de 01/10: o braço que reproduz o modelo
publicado "precisa ser desdobrado em dois braços explícitos — inicialização
pura, sem nenhum passo de treino, e PGSG treinado com o protocolo
declarado", porque "o modelo publicado corresponde ao primeiro deles".
"Com essa adição, o ADR pode passar a aceito." (Mais abaixo, a seção mostra
que o artigo mistura os dois: as portas publicadas correspondem ao primeiro,
os R² ao segundo.)

**O desdobramento:**

- **Porta na inicialização.** A porta fica fixa no valor inicial do PGSG,
  `softmax(logit(clip(s)) / τ)`, com `s` o prior ANOVA normalizado por
  mínimo e máximo, `clip` em `[1e-7, 1 − 1e-7]` e `τ = 5`, sem gradiente;
  o restante da rede é treinado com o mesmo protocolo e o mesmo orçamento
  do PGSG treinado, para que os dois braços difiram só pelo gradiente na
  porta.
- **PGSG treinado.** A porta parte do mesmo valor e é treinável, com os
  hiperparâmetros declarados no artigo: lr 0,01, 200 épocas, paciência 30,
  peso do KL 0,001. **Com uma diferença obrigatória:** no artigo a
  paciência observa o próprio conjunto de teste (`train_light.py`); aqui ela
  observa uma fold de validação interna, porque o protocolo deste trabalho
  não deixa o braço ver o teste externo (contrato `Arm` do Estágio 0:
  `Arm.fit` não recebe o teste). Na reexecução fiel do artigo, para comparação, a parada fica como
  no original.

**Leitura adotada para "inicialização pura".** "Sem nenhum passo de treino"
é lido como **a porta** sem nenhum passo de treino. Uma rede inteira sem
treino não prevê, então não há R² a comparar nesse braço. Se a orientação
quis dizer outra coisa, este parágrafo muda.

**Consequência para o desenho.** Com essa leitura, o braço "porta na
inicialização" é o **B2** do pipeline ("ponderação fixa pelo prior, sem
gradiente na porta"), desde que a ponderação fixa do B2 seja exatamente a
porta inicial acima, e não o prior `s` bruto. As duas não são a mesma coisa:
no Tecator, a porta inicial põe 21,5% do peso numa só banda, por causa da
saturação do `clip` no máximo do prior, enquanto o prior bruto, normalizado
para somar 1, põe 2,4% na maior. Este ADR fixa a primeira. Com isso, o "PGSG treinado" é o B4, e
`Δ_aprendizado = B4 − B2` passa a medir diretamente o que a orientação
propôs como hipótese: se o aprendizado da porta é nulo por construção.
*(Afirmação corrigida em 04/11: o Δ sozinho não mede isso. Ver a seção
"O que o Δ mede", abaixo.)*

**O que "reproduzir o modelo publicado" passa a significar.** O critério do
pipeline ("B4 reproduz o braço de referência") deixa de ser bem definido,
porque o artigo mistura os dois braços:

- as **portas** publicadas (Tabela 2, Fig. 1) correspondem à porta na
  inicialização — `analyze_gates.py` instancia um modelo novo e lê as
  portas sem treinar;
- os **R²** publicados das redes (Tabela 1) vêm de modelos treinados — o
  `train_light.py` e o `cross_validate.py` treinam antes de avaliar — e
  caem dentro da dispersão entre sementes de cada braço treinado
  correspondente (`results/verificacao_3_pipeline_com_o_alvo_correto.md`).

A verificação contra o artigo passa a ser feita por partes: as portas
contra o braço "porta na inicialização", e os R² contra o braço "PGSG
treinado", como faixa entre sementes e não como ponto. A divergência ainda
aberta com a reprodução da orientação nos braços de rede (relatório 3, seção
"Divergência com a reprodução da orientação")
afeta esta segunda parte.

O braço com a inicialização corrigida, também pedido no parecer, é um braço
novo, e não um desdobramento do B4. Entra no protocolo, não neste ADR.

## O que o Δ mede (acrescentado em 04/11/2026)

Pedido da orientação em 29/10, que concordou com a leitura do B2 acima e
condicionou o aceite a estes acréscimos: "Com essas adições, o ADR 013 passa
a aceito." A parte do decaimento de peso veio da mensagem de 30/10, depois
de uma observação minha sobre o código.

**O confundidor.** No PGSG, a porta entra direto na primeira camada linear:

```
fc1(x ⊙ g) = (W1 · diag(g)) · x + b1
```

A porta é uma reescala das colunas de `W1`, e essas colunas são livres.
Qualquer primeira camada efetiva que o B4 alcance movendo a porta, o B2
também alcança reescalando `W1`. Os dois braços têm a mesma classe de
funções. O BatchNorm depois da `fc1` normaliza cada unidade oculta, não as
colunas, e não muda isso. O argumento vale para o modelo leve, em que a
`fc1` vem logo depois da porta, e não para a Plain CNN, que tem convolução
depois da porta.

**Consequência.** Δ_aprendizado ≈ 0 é o resultado esperado por mais de um
caminho, e o Δ sozinho não distingue entre eles:

- **(a) a porta não anda o bastante.** No Tecator, a banda campeã começa
  11,5 logits à frente da segunda, e o passo do Adam limita o quanto cada
  logit anda em 200 passos de lr 0,01. Não é gradiente pequeno: no topo, a
  derivada do softmax com temperatura, `g(1 − g)/τ`, vale cerca de 0,034
  com g = 0,215 e τ = 5, mais que numa banda típica. Gradiente atenuado por
  `s(1 − s)` é o mecanismo da porta sigmoide, de outro modelo. Por isso este
  ADR não usa "saturação" para o que trava o topo: a palavra fica só para o
  `clip` do prior.
- **(b) a porta anda e o MLP absorve,** pela reescala de colunas acima.
- **(c) o que se move é encolhimento.** O `train_light.py` aplica
  `weight_decay=1e-4` a `model.parameters()`, que inclui os logits da porta.
  L2 num logit puxa para zero, isto é, puxa a porta para o uniforme. Isso não
  é aprendizado nem trava. Medido no Tecator (orientação, 30/10, e repetido
  aqui; `results/verificacao_3b_secao_5_2.md`, seção "O mecanismo"), é a
  maior parte do movimento: o maior deslocamento é de cerca de 1,7 logit com
  o decaimento do artigo, e de cerca de 0,3 com a porta isenta. No Gasoline
  (medido em 05/11, mesmo relatório) o encolhimento é cerca de metade, de
  1,34 para 0,66. Com a porta isenta, a maioria das bandas se afasta de zero
  em vez de encolher. O peso de (c) muda de um conjunto para outro.

**O papel que sobra para a porta.** Pela equivalência acima, a porta não
acrescenta funções. Ela muda a regularização: o decaimento incide sobre
`W1`, não sobre `W1 · diag(g)`. Com g_j pequeno, a coluna j precisa ser
grande para ter o mesmo efeito, e paga quadraticamente por isso. A porta
redistribui o orçamento de regularização entre as bandas. É um papel real,
mas não é "aprender quais bandas importam".

**As medidas que acompanham o Δ.** O Δ_aprendizado é reportado sempre junto
com o deslocamento da porta, medido direto:

- o **deslocamento** θ_final − θ_inicial, em logits, por banda, com o
  maior e a mediana do valor absoluto;
- a **correlação desse vetor entre sementes**, em vez da correlação da porta
  final. A porta final carrega a inicialização, que é a mesma em todas as
  sementes, e pareceria estável sem ter aprendido nada;
- as duas **estatísticas de direção** de cada semente: a fração de bandas
  cujo |θ| diminuiu e a correlação entre o deslocamento e −θ_inicial.
  Encolhimento puro leva as duas a 1.

O deslocamento só separa (a) de (c) se for medido **com a porta isenta de
L2**. Com o decaimento do artigo na porta, ele mede sobretudo o
encolhimento.

**Decaimento na porta: B2 e B4 diferem em mais do que o gradiente.** No B2
congelado, a porta não sofre decaimento; no B4 com a receita do artigo,
sofre. O Δ desse B4 inclui o encolhimento. A orientação propôs dois B4 para
as duas perguntas:
- **B4 fiel**, com decaimento na porta, para comparar contra o artigo;
- **B4 limpo**, com a porta isenta, para medir o gradiente na porta sozinho.

A escolha vai ao protocolo, antes de rodar, e não a este ADR. Qualquer que
seja ela, o relatório do Δ declara se a porta do B4 sofreu decaimento.

**Três ajustes ao desenho acima:**

- **Δ_ponderação = B2 − B1.** Com o B2 definido como a porta inicial do
  PGSG, e não o prior bruto, esse termo mede o efeito de ponderar as bandas
  pela porta inicial, com a concentração que o `clip` cria (21,5% numa só
  banda no Tecator). Não mede o efeito do prior como distribuição.
- **O KL é inerte no B2.** O termo KL depende só da porta, e com a porta
  congelada ele é constante e não manda gradiente para nada. O λ não faz
  nada no B2. Por isso os dois braços diferem exatamente pelo gradiente na
  porta, e, no B4 fiel, também pelo decaimento nela.
- **"Mesmo orçamento"** entre B2 e B4 significa a mesma regra de parada (a
  mesma paciência sobre a mesma fold de validação interna), e não o mesmo
  número de épocas. Com menos parâmetros no otimizador, o B2 pode parar em
  outra época.

## Ressalva obrigatória

Os valores desta âncora foram medidos **antes** de resolver o problema das
réplicas do Tecator registrado em `docs/PENDENCIAS.md`, item A1: o conjunto
tem 22 pares de espectros idênticos, e a partição aleatória com semente 42
deixa 7 desses pares atravessarem a divisão treino/teste. Os 22 pares têm
também o `y` idêntico: são réplicas da mesma amostra, não coincidência de
espectro. O efeito medido sobre o PLS é pequeno — com H\* = 12 mantido, a
gordura vai de 0,946 para 0,943, tanto tirando do teste os 7 membros que
têm o gêmeo no treino (R² 0,9426, 36 amostras de teste) quanto tirando do
treino os 7 gêmeos (0,9428) —, mas não é nulo e não foi medido sobre os
demais braços. Medido em `scripts/verificar_replicas_tecator.py`.

A âncora acima é a reexecução **fiel** do protocolo do artigo, com as
propriedades dele, inclusive essa. Ela serve para comparar este trabalho
contra aquele artigo. Não serve como medida limpa de desempenho, e o
protocolo próprio deste trabalho (ADR 009) não deve herdá-la.
