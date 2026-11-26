# Revisão dirigida: os quatro seletores clássicos

**Status:** rascunho, 23/11/2026. Item 1 do primeiro semestre na proposta
(`docs/fontes/tcc_rodrigo.pdf`, seção 6.1): seleção de variáveis em PLS
(iPLS, CARS, GA-PLS, VIP). Formato proposto à orientação em 20/08
(`docs/estudo_rodrigo/PERGUNTAS.md`, pergunta 2, sem resposta fechada): uma
ficha por método e uma tabela comparativa no fim.

**Regra deste documento:** só entra o que foi lido na fonte, com a fonte ao
lado. O que vem de fonte secundária está marcado como tal, e o que não foi
lido está na seção "A ler" de cada ficha. Os testes de equivalência e a
comparação de vários algoritmos, a outra metade do item 1 da proposta, ficam
para um segundo documento.

**Fontes lidas para esta versão:**
- Li, Liang, Xu e Cao (2009), *Analytica Chimica Acta* 648, 77–84 (o CARS),
  texto completo, cópia do autor em `docs/fontes/cars/CARS.pdf` (fora do
  versionamento). Lido em 23/11.
- Documentação do `mdatools`, página do iPLS (https://mda.tools/docs/ipls.html).
  Lida em 23/11.
- Mehmood, Sæbø e Liland (2020), *J. Chemometrics* 34, e3226 (acesso aberto).
  Lido em 28/10; o que está aqui vem do registro feito naquela data nos ADRs
  014 e 015. O PDF não está no computador (nota de 06/11 no ADR 014).
- Scrucca (2013), *Journal of Statistical Software* 53(4) (pacote GA), lido
  em outubro; registro no ADR 015.
- Documentação da Eigenvector (PLS_Toolbox, página `Vip`), registro no ADR
  014.

---

## 1. iPLS (PLS por intervalos)

**Origem.** Nørgaard, Saudland, Wagner, Nielsen, Munck e Engelsen (2000),
*Applied Spectroscopy* 54(3), 413–419. **Não lido** (acesso fechado; a
página da editora recusou o acesso automático em 23/11).

**Ideia** (pela documentação do `mdatools`, que atribui o método a Nørgaard
et al., 2000): dividir o espectro em intervalos de mesma largura, ajustar um
PLS local em cada um e comparar o erro de validação cruzada com o do
espectro inteiro. O que importa é a região, e não a banda isolada.

**Algoritmo no `mdatools`** (a implementação usada aqui):
- os intervalos são definidos por número (`int.num`), por largura
  (`int.width`) ou por limites explícitos (`int.limits`);
- duas direções: *forward* (padrão), que parte de nenhum intervalo e
  acrescenta um por vez o que mais reduz o RMSECV; e *backward*, que parte
  de todos e retira um por vez;
- cada modelo local tem até `int.ncomp` componentes, escolhidos pelo
  critério `ncomp.selcrit`; o modelo global usa `glob.ncomp`;
- validação cruzada padrão: blocos venezianos com 10 segmentos;
- parada: no padrão, para quando o RMSECV da iteração seguinte não é menor
  que o atual; com `full = TRUE`, vai até `int.niter` (padrão 30) e fica
  com o mínimo global.

**Parâmetros que ficam com o usuário:** o número (ou a largura) dos
intervalos, a direção, o número de componentes local e global, o critério
de componentes e a regra de parada.

**Dados do artigo original:** não lidos. A busca preliminar de outubro
(DIARIO, ~linha 950), só em resumos, indicou espectros NIR de cerveja, e
não o Tecator nem o Gasoline. A confirmar no texto.

**Neste trabalho** (ADR 012, proposto): `mdatools::ipls` via `rpy2`,
*forward*, folds do protocolo; `int.num` escolhido na CV interna entre
{10, 15, 20, 25, 30}, com a regra de um erro-padrão. Em 17 e 23/11: a escolha
cai na borda de baixo (10) na maioria das partições; no Tecator e no
Gasoline a curva de erro é plana, no Mango o ótimo está mesmo embaixo
(pergunta 10 à orientação, 23/11).

**A ler:**
- o artigo de 2000: o conjunto, o número de intervalos que os autores usaram
  e recomendam, como escolheram os componentes por intervalo, e se
  apresentam *forward*/*backward* ou só o iPLS simples. **O ADR 012 depende
  disso:** a grade de `int.num` foi declarada sem o artigo, e se ele indicar
  outra faixa o ADR é corrigido antes da grade final.

---

## 2. CARS (amostragem competitiva adaptativa e reponderada)

**Origem.** Li, Liang, Xu e Cao (2009), *Analytica Chimica Acta* 648, 77–84.
**Lido por inteiro.**

**Ideia** (Seções 1 e 2): o princípio da "sobrevivência do mais apto". A
importância de cada banda é o valor absoluto do seu coeficiente num PLS, e o
método vai eliminando as menos importantes em rodadas sucessivas, de forma
competitiva, até sobrarem poucas bandas-chave.

**Algoritmo** (Seções 2.2 a 2.6, Fig. 3), em N rodadas de Monte Carlo:
1. **Amostragem do modelo:** em cada rodada, um PLS com uma fração das
   amostras de calibração sorteada ao acaso ("usualmente 80–90%"); X e y
   centrados.
2. **Pesos:** `w_i = |b_i| / Σ|b_j|`, com os coeficientes `b` do PLS; bandas
   já eliminadas ficam com peso zero.
3. **Eliminação forçada por função exponencial decrescente (EDF):** a
   fração de bandas mantidas na rodada `i` é `r_i = a·e^(−k·i)`, com `a` e
   `k` fixados por duas condições: todas as `p` bandas na primeira rodada e
   só 2 na última. Daí `a = (p/2)^(1/(N−1))` e `k = ln(p/2)/(N−1)`. A curva
   tem uma fase de seleção rápida e outra de seleção refinada (Fig. 1).
4. **Seleção competitiva por amostragem adaptativa reponderada (ARS):**
   entre as bandas que sobraram, sorteio com reposição proporcional ao
   peso; as que não são sorteadas saem (Fig. 2).
5. **Escolha:** cada rodada dá um subconjunto; o escolhido é o de menor
   RMSECV entre os N.

**Parâmetros que ficam com o usuário:** o número de rodadas N, a fração de
amostras por rodada, o número máximo de componentes dos PLS internos e a
validação cruzada usada no RMSECV.

**O que o artigo testou:**
- **N** (Seção 4.1, Fig. 5): 50, 100, 200 e 500, com 50 repetições em cada
  conjunto; o desempenho não muda de forma significativa, e o padrão
  adotado é 100.
- **Dados:** um simulado (SIMUIN: 25 amostras, 200 variáveis, as 100
  primeiras informativas) e o milho NIR (80 amostras, 700 pontos de 1.100 a
  2.498 nm), com umidade e proteína.
- **Comparação:** com o PLS do espectro inteiro, o MC-UVE e o MWPLSR, com CV
  de 10 folds (Seção 4.2). No simulado (Tabela 1), RMSECV de 0,0139 ± 0,0023 do CARS
  contra 0,0209 ± 0,0006 do MC-UVE, com 16 ± 4 variáveis; os autores notam
  que o desvio maior indica que **a estabilidade do CARS ainda precisa
  melhorar**.

**Neste trabalho** (ADR 016, proposto): o algoritmo do artigo, em Python,
conferido contra os códigos dos autores (`carspls.m` 1.50 e 1.95), com dois
modos. O `protocolo` escolhe N ∈ {50, 100}, a razão ∈ {0,8, 0,9} e o fator do
teto de componentes ∈ {1, 2, 3} na CV interna; o `fiel` fixa N = 100 (o
artigo), razão 0,9 e fator 3. Reproduz o achado do artigo no milho e o
RMSEP de Zhong et al. (2023) no Gasoline (checklist, item 3). **O artigo não
informa o teto de componentes que usou,** e o teto decide se o CARS acha a
combinação de bandas (ADR 016).

**A instabilidade que o próprio artigo aponta** é o que a H5 mede (Jaccard
entre sementes).

---

## 3. GA-PLS (PLS com algoritmo genético)

**Origem.** Atribuído por Mehmood et al. (2020, Seção 3.2.1) a Hasegawa,
Miyashita e Funatsu (1997). O GA-PLS de Leardi também é referência clássica.
**Nenhum dos dois lido.**

**Ideia** (Mehmood et al., 2020, Seção 3.2.1, conforme o registro do ADR 015):
cada subconjunto de bandas é um cromossomo binário (1 = banda dentro); a
qualidade de cada cromossomo é o desempenho de um PLS com aquelas bandas; os
melhores sobrevivem e geram os próximos por cruzamento e mutação.

**Algoritmo** (mesma fonte), em cinco passos: população inicial binária;
ajuste de um PLS por cromossomo; sobrevivência dos melhores; cruzamento;
mutação. Repete por várias gerações.

**Parâmetros que ficam com o usuário:** tamanho da população, número de
gerações, probabilidades de cruzamento e mutação, densidade da população
inicial, a medida de qualidade (o RMSECV de qual validação) e como escolher o
cromossomo final. No estudo de simulação de Mehmood et al. (2020, Tabela 2),
o parâmetro de mutação ajustado ficou em R0 = 8,39.

**O motor genético** (Scrucca, 2013, e o código do pacote GA 3.2.5): seleção
por ranking linear, cruzamento de um ponto (probabilidade 0,8), mutação de
um bit (0,1) e elitismo de 5% como padrão.

**Neste trabalho** (ADR 015, proposto): `GA::ga` binário, com os operadores
padrão; qualidade = menos o RMSE da CV nas folds do protocolo, com o PLS
avaliado pelo algoritmo kernel de Dayal e MacGregor (1997) por custo;
população inicial com chance 0,1 por banda (com 0,5 o braço terminava com 38
a 49% das bandas); (população, gerações) ∈ {(30, 50), (50, 100)} na CV
interna; o cromossomo final é o melhor da execução.

**A ler:**
- Hasegawa et al. (1997) e o GA-PLS de Leardi: tamanhos de população e
  gerações usados, como evitam o sobreajuste da busca (o GA avalia milhares
  de subconjuntos na mesma CV), e a densidade inicial.

---

## 4. VIP (importância da variável na projeção)

**Origem.** Wold, Johansson e Cocchi (1993), capítulo em *3D QSAR in Drug
Design*; o nome VIP é de Eriksson et al. (2001). **Nenhum dos dois lido;**
atribuição segundo Mehmood et al. (2020, Seção 3.1.3).

**Ideia:** depois de ajustar um PLS, dar a cada banda um escore de quanto ela
pesa nos componentes que explicam y, e ficar com as bandas de escore alto. É
um filtro: um só ajuste de PLS, sem busca.

**Fórmula** (Mehmood et al., 2020, Seção 3.1.3, conforme o ADR 014):
`VIP_j = sqrt( p · Σ_a SS_a (w_ja / ||w_a||)² / Σ_a SS_a )`, com os pesos
`w_a` do PLS e `SS_a = q_a² t_a't_a`, a variância de y explicada pelo
componente `a`. A média dos VIP² é 1 por construção.

**O corte:** a convenção "geralmente aceita" é selecionar as bandas com VIP
acima de 1 (Mehmood et al., 2020, citando Eriksson et al., 2001, Chong e
Jun, 2005, e Gosselin et al., 2010). A documentação da Eigenvector diz o
mesmo ("próximo de 1 ou maior") e alerta contra eliminar em rodadas
sucessivas pelo VIP. No estudo de simulação de Mehmood et al. (2020, Seção
4.3, Tabela 2), o limiar ajustado por validação cruzada ficou em 0,90, e eles
recomendam validação cruzada dupla para ajustar o limiar.

**Parâmetros que ficam com o usuário:** o número de componentes do PLS, o
limiar e qual "VIP" calcular. Medido aqui (ADR 014): o `mdatools` e o
`plsVarSel` chamam de VIP quantidades diferentes (pesos do SIMPLS contra
pesos do NIPALS), e a seleção muda.

**Neste trabalho** (ADR 014, proposto): a fórmula com os pesos do NIPALS,
como em Mehmood et al. (2020) e no `plsVarSel`; o limiar escolhido na CV
interna entre {0,2; 0,4; 0,6; 0,8; 1,0; 1,2; 1,5; 2,0; 2,5; 3,0} (grade
alargada em 17/11, a pedido da orientação), com a regra de um erro-padrão.

**A ler:**
- Wold et al. (1993) e Chong e Jun (2005): a fórmula na forma original e o
  estudo de simulação que sustenta o corte em 1.

---

## Tabela comparativa

| | iPLS | CARS | GA-PLS | VIP |
|---|---|---|---|---|
| **o que seleciona** | intervalos contíguos | bandas soltas | bandas soltas | bandas soltas |
| **tipo de busca** | gulosa, um intervalo por vez | eliminação progressiva com sorteio | evolutiva (população) | nenhuma: um PLS e um corte |
| **critério interno** | RMSECV | \|coeficiente\| do PLS, depois RMSECV | RMSECV | escore VIP |
| **aleatório?** | não | sim (amostras e ARS) | sim | não |
| **parâmetro principal** | número de intervalos | N, fração de amostras, teto de componentes | população, gerações, densidade inicial | limiar (e nº de componentes) |
| **custo** | médio a alto (um PLS por intervalo por passo) | médio (N rodadas × CV) | alto (milhares de PLS) | baixo |
| **original lido?** | não | sim | não | não |
| **implementação aqui** | `mdatools` (R) | Python, conferido contra o código dos autores | `GA` (R) + PLS kernel | Python, conferido contra o `plsVarSel` |
| **ADR** | 012 | 016 | 015 | 014 |

Custo: leitura qualitativa do algoritmo, a conferir com os tempos medidos no
piloto.

---

## O que falta ler, em ordem de impacto

1. **Nørgaard et al. (2000), iPLS.** Pode mudar a grade de `int.num` do ADR
   012, e conversa com a pergunta da borda mandada em 23/11.
2. **Mehmood et al. (2020)**, de novo, com o PDF guardado: é a fonte
   secundária dos três métodos não lidos, e é de acesso aberto.
3. **Chong e Jun (2005)**, VIP: o corte em 1.
4. **Hasegawa et al. (1997)** e **Leardi (GA-PLS)**: população, gerações e
   sobreajuste da busca.
5. **Wold et al. (1993)**, a fórmula original do VIP.
