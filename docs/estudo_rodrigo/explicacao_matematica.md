# Explicação da matemática do projeto

> Material de referência pessoal, para consulta ao longo do TCC — não é texto
> de monografia. Escrito para relembrar os conceitos com calma sempre que
> precisar, do zero, sem assumir conhecimento prévio de quimiometria.

---

## Parte 0 — De onde vêm os números

### O experimento físico

Pega um pedaço de carne moída. Coloca no aparelho (o Tecator Infratec). O
aparelho dispara luz infravermelha através da amostra e mede quanta luz saiu
do outro lado.

Ele não dispara uma luz só — dispara luz de **100 cores diferentes** (comprimentos
de onda), uma de cada vez, de 850 a 1050 nanômetros (nm — um bilionésimo de
metro). É infravermelho próximo: não se enxerga, mas é luz igual à visível.

### Por que isso diz algo sobre gordura

Moléculas vibram. Uma ligação química entre carbono e hidrogênio (C–H) se
estica e comprime numa frequência específica, como uma mola com massa numa
ponta. Quando a luz que passa tem energia igual à dessa vibração, a molécula
**absorve** aquele fóton.

Cada tipo de ligação absorve numa faixa característica:

| Ligação | Onde absorve | Está em |
|---|---|---|
| C–H | ~930 nm | gordura (cadeias de hidrocarboneto) |
| O–H | ~970 nm | água |

Mais gordura → mais ligações C–H → mais absorção em 930 nm.

Isso é a **Lei de Beer-Lambert**: a absorção é proporcional à concentração da
substância. É a razão pela qual métodos lineares funcionam tão bem nessa área
(ver Parte 5).

### Absorbância

```
absorbância = −log₁₀(transmitância)
```

Essa transformação torna a relação com a concentração **linear**: dobrar a
gordura dobra o número medido.

### De onde vem o vetor

Uma amostra de carne, 100 medições, na ordem:

```
[2,86  2,88  2,89  ...  3,21 (930nm, gordura)  ...  3,78 (970nm, água)  ...  3,35]
```

Isso é o vetor: uma lista ordenada de números. A posição importa — a posição 41
sempre significa "930 nm". Se plotar (posição no eixo horizontal, valor no
vertical), sai a curva do espectro. Curva e vetor são a mesma coisa.

### De onde vem a matriz X

Empilha um vetor por linha, uma linha por amostra:

```
                banda 1   banda 2   ...   banda 100
amostra 1        2,86      2,88     ...     3,35
amostra 2        2,91      2,93     ...     3,41
...
amostra 215      2,79      2,81     ...     3,28
```

`X` tem dimensão `(215, 100)`: 215 linhas (amostras), 100 colunas (bandas).
Convenção universal em ML: linha = amostra, coluna = característica (feature).

### De onde vem y

Cada amostra também passou por análise química de laboratório (destrutiva,
lenta, cara), que deu o teor de gordura real — um número por amostra. Isso é
o vetor `y`, dimensão `(215,)`.

```
X  →  entrada                matriz (215, 100)
y  →  alvo a prever           vetor  (215,)
n  →  número de amostras  = 215
p  →  número de features  = 100
```

O objetivo do campo: substituir a análise química cara por um modelo que lê
o espectro em segundos.

---

## Parte 1 — Regressão linear, coeficientes, β

### A ideia

Uma fórmula que transforma 100 números num só, multiplicando cada entrada por
um peso e somando:

```
gordura_estimada = β₁·banda₁ + β₂·banda₂ + ... + β₁₀₀·banda₁₀₀
```

**β são os coeficientes** — 100 números, um por banda, dizendo quanto cada
banda pesa na conta. β (beta) é só a convenção da estatística para "peso" —
em redes neurais a mesma coisa se chama peso mesmo.

### Exemplo com 3 bandas

```
β₁ = 0,2      (850 nm)
β₂ = 15,0     (930 nm — banda da gordura)
β₃ = −8,0     (970 nm — banda da água)
```

Espectro novo `[2,9  3,4  3,8]`:

```
0,2·2,9 + 15,0·3,4 + (−8,0)·3,8 = 0,58 + 51,0 − 30,4 = 21,18%
```

- β₂ grande e positivo: mais gordura → mais absorção em 930. Faz sentido químico.
- β₃ negativo: mais água → menos gordura (a composição soma 100%).
- β₁ ≈ 0: essa banda quase não informa nada.

Os coeficientes **são** o conhecimento aprendido pelo modelo.

### Como se acham os β — mínimos quadrados

Define o erro de cada amostra de treino: `erro = valor_real − valor_predito`.
Eleva ao quadrado (pra erros positivos e negativos não se cancelarem) e soma:

```
soma_dos_erros² = Σᵢ (yᵢ − ŷᵢ)²
```

(Σ = "some tudo"; ŷ = "y chapéu" = valor predito, para distinguir do y real.)

Objetivo: achar os β que minimizam essa soma. Existe fórmula fechada:

```
β = (Xᵀ X)⁻¹ Xᵀ y
```

- **Xᵀ** ("X transposto"): vira a matriz de lado, linhas viram colunas.
- **XᵀX**: multiplicação de matrizes — uma tabela de "quanto cada banda se
  parece com cada outra banda".
- **⁻¹**: inversa. Análogo do inverso de um número (inverso de 5 é 1/5,
  porque 5×1/5=1). Para matrizes, "desfaz" a multiplicação.

---

## Parte 2 — Por que isso quebra aqui

### Nem toda matriz tem inversa

Análogo do zero para matrizes: quando colunas são **linearmente
dependentes** (uma pode ser escrita a partir das outras), a matriz é
**singular** e não tem inversa.

### Por que acontece com espectros

Bandas vizinhas (930 nm e 932 nm) têm valores quase idênticos em todas as
amostras — a física garante isso, o espectro é uma curva lisa. Fazendo de
conta que fossem exatamente iguais, todas estas soluções dão a mesma
predição:

```
β₉₃₀=15, β₉₃₂=0   |   β₉₃₀=0, β₉₃₂=15   |   β₉₃₀=5000, β₉₃₂=−4985
```

Infinitas soluções — igual resolver `x+y=10` com uma equação só. Isso se
chama **colinearidade** (ou multicolinearidade), e em espectroscopia é a
regra, não a exceção.

### Por que aparece a pior solução

Na prática as bandas são quase iguais, não exatamente. A matriz tem inversa
tecnicamente, mas instável — e o algoritmo tende a escolher soluções tipo
`[5000, −4985]`. Um ruído de 0,001 na banda 930 vira `5000×0,001=5` na
predição. O modelo acerta perfeitamente no treino e desanda no teste —
**overfitting por colinearidade**.

No Gasoline é pior ainda: 48 amostras de treino, 401 bandas — menos equações
que incógnitas.

### O caminho de saída

Não usar as 100 bandas diretamente. Comprimir em ~10 **direções** (misturas
das bandas) e regredir nelas.

---

## Parte 3 — Variância e covariância

**Variância**: quanto os valores se afastam da média (o quão espalhados estão).

**Covariância**: se duas grandezas sobem e descem juntas.

```
Cov > 0  →  sobem juntas       (altura e peso)
Cov ≈ 0  →  sem relação
Cov < 0  →  uma sobe, outra desce   (gordura e água na carne)
```

Cálculo, em uma linha: centra as duas (subtrai a média), multiplica ponto a
ponto, soma. Se ambas acima da média → positivo×positivo=positivo. Se ambas
abaixo → negativo×negativo=positivo também. Direções opostas → negativo. Sem
relação → os sinais se cancelam e a soma tende a zero.

Isso é exatamente o que a operação `X.T @ y` calcula (ver Parte 5).

---

## Parte 4 — Por que PCA acha as direções erradas

**PCA** (Principal Component Analysis) acha as direções de **maior
variância** nos dados — parece razoável, mas:

No gráfico do Tecator, as curvas estavam empilhadas verticalmente, mesmo
formato, umas acima das outras. Essa subida/descida do bloco inteiro é a
maior fonte de variância — e vem de espessura da fatia, granulometria,
espalhamento de luz. **Não é química.**

PCA acharia isso como componente nº 1, explicando boa parte da variância, e
sendo inútil para prever gordura.

O defeito é estrutural: PCA nunca olha para `y`.

```
PCA maximiza:  Var(Xw)     — "onde os dados variam"
```

---

## Parte 5 — PLS (Partial Least Squares)

### A mudança de uma linha

```
PCA:  maximizar  Var(Xw)         onde os dados variam
PLS:  maximizar  Cov(Xw, y)²     onde variam JUNTO com o alvo
```

A direção do espalhamento de luz varia muito, mas descorrelacionada com
gordura — covariância baixa, PLS ignora.

### Como acha a direção

```python
w = X.T @ y
```

Para cada banda: pega a coluna, multiplica ponto a ponto por `y`, soma —
exatamente o cálculo de covariância da Parte 3. Resultado: um número por
banda, "quanto essa banda covaria com a gordura". Banda da gordura → número
grande. Banda irrelevante → perto de zero. Isso já é a primeira direção.

### Deflação — o coração do algoritmo

```python
t = X @ w                    # projeta: cada amostra vira um número
p = (X.T @ t) / (t @ t)      # quanto cada banda contribuiu
X = X - outer(t, p)          # SUBTRAI dos dados o que já foi explicado
```

O `X = X - ...` remove dos dados o que a primeira direção já capturou. Sobra
o **resíduo**. Repetindo `X.T @ y` no resíduo sai a segunda direção — que por
construção não repete nada da primeira (são **ortogonais**, sem informação
redundante). Repete H vezes.

### Por que isso resolve o problema da Parte 2

100 bandas colineares viram ~10 direções ortogonais. A matriz resultante não
é singular, a inversa é estável, e a regressão linear nela é bem-comportada.

> PLS = comprimir bandas colineares em ~10 direções ortogonais escolhidas por
> correlacionarem com o alvo, e fazer regressão linear normal nelas.

### O hiperparâmetro H

Quantas direções extrair. Hiperparâmetro = número escolhido antes de treinar
(diferente dos β, que o algoritmo aprende sozinho).

**Regra de um erro-padrão** (usada no paper): a curva de erro costuma ser
plana perto do mínimo, então pegar o argmin é pegar ruído. A regra escolhe o
**menor H cujo erro esteja dentro de um erro-padrão do mínimo** — o modelo
mais simples entre os equivalentes. Precisa ser replicada nos braços
clássicos do TCC, por justiça de comparação.

### Por que é tão difícil de bater

Pela Lei de Beer-Lambert (Parte 0), a absorção é proporcional à concentração
— o fenômeno é fisicamente linear. Um modelo linear não é aproximação
grosseira aqui, é o modelo correto. Rede neural tem que ganhar de algo já
estruturalmente adequado, com poucas amostras. É difícil.

---

## Parte 6 — A porta espectral (gating)

### O que é

```python
g = softmax(θ / τ)      # 100 pesos que somam 1
x̃ = x * g               # multiplica cada banda pelo peso
```

(x̃ = "x til" = x modificado; θ = theta, τ = tau — parâmetros treináveis,
ajustados por gradiente igual ao resto da rede.)

### Softmax

Transforma qualquer lista de números numa lista que soma exatamente 1,
preservando a ordem relativa. Duas razões para usar:

1. Somar 1 = distribuição de probabilidade → necessário para usar KL depois.
2. É competitivo: aumentar peso de uma banda reduz o das outras — a porta é
   obrigada a escolher.

### Temperatura τ

```
θ = [3,1,1,1]
τ=1  →  [0,71  0,10  0,10  0,10]   quase tudo numa banda (satura)
τ=5  →  [0,32  0,23  0,23  0,23]   distribuído
```

Com τ=1 a porta satura cedo → gradiente ≈ 0 → para de aprender, congelada
numa escolha arbitrária. τ=5 mantém o gradiente vivo. O paper reporta ter
observado esse colapso com τ=1.

### Inicialização pelo prior

`s` = escores de importância por banda (de ANOVA, VIP ou Random Forest),
normalizados para [0,1]. Inicializa:

```python
θ₀ = log(s / (1 - s))     # logit, inversa da sigmoide
```

Construído para que `softmax(θ₀/τ) ≈ s`: a rede nasce já ponderando o
espectro segundo o conhecimento químico, em vez de nascer aleatória.

### Regularização KL

```python
perda = MSE + λ · KL(g ‖ s)
```

- MSE (erro quadrático médio) — mede se as predições estão certas.
- KL (divergência de Kullback-Leibler) — mede o quanto duas distribuições
  diferem; 0 se iguais, cresce ao se afastarem.

Juntos: uma mola puxando a porta de volta pro prior durante o treino. λ é a
rigidez da mola:

| λ | correlação final com o prior | efeito |
|---|---|---|
| ≥ 0,01 | > 0,85 | mola rígida — só copia o prior |
| **0,001** | **0,35–0,51** | refina o prior com os dados |
| ≤ 0,0001 | — | mola frouxa — vira init aleatória |

### O resto da rede

```python
h = ReLU(BatchNorm(W1 @ x̃))    # camada oculta, 16 neurônios
ŷ = W2 @ Dropout(h)             # saída: um número
```

Minúscula de propósito (1.765 parâmetros no Tecator, ~97 amostras por
parâmetro). A CNN pesada testada no paper (109 mil parâmetros, ~2
amostras/parâmetro) deu R² = 0,235 — overfitting catastrófico.

### Por que é "interpretável"

Depois de treinar, `g` mostra direto quais bandas o modelo usa — a
importância é um parâmetro do modelo, não reconstrução posterior. No
Tecator, o maior peso (0,215) caiu em 931 nm — a região C–H da gordura. A
rede "descobriu" química correta.

---

## Parte 7 — Por que os braços existem

A porta tem três ingredientes separáveis, nunca isolados no paper:

```
1. a ponderação existir
2. ela receber gradiente (ser treinável)
3. ela começar do prior em vez de uniforme
```

| Braço | ponderação | treinável | init |
|---|:---:|:---:|---|
| A1 | — | — | (é PLS, nem tem rede) |
| B1 | ❌ | — | — |
| B2 | ✅ | ❌ congelada | prior |
| B3 | ✅ | ✅ | uniforme |
| B4 | ✅ | ✅ | prior *(= modelo publicado)* |

```
B1 − A1  →  quanto ganhei só por trocar linear por rede neural
B2 − B1  →  quanto ganhei por ponderar (porta congelada)
B4 − B2  →  quanto ganhei por deixar a porta aprender
B4 − B3  →  quanto ganhei por começar do prior em vez de uniforme
```

A soma dos três primeiros reconstitui `B4 − A1` — o ganho total reportado na
literatura. O trabalho mostra como esse total se reparte.

**Analogia:** um PR que mudou três coisas de uma vez, a latência caiu 30%, e
todo mundo assumiu que foi a feature nova. O TCC separa em commits atômicos
e mede cada um.

**Teste de sanidade essencial:** B2 com a porta congelada em uniforme tem
que dar estatisticamente idêntico a B1 (multiplicar tudo pela mesma
constante não muda nada). Se não der, há bug na implementação.

**Regra de ferro do Estágio 3 do pipeline:** o MLP deve ser byte a byte
idêntico nos quatro braços neurais — mesma arquitetura, inicialização,
otimizador, orçamento de épocas. Qualquer diferença acidental contamina o Δ
correspondente sem possibilidade de detecção posterior.
