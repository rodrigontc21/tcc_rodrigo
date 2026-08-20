# Pipeline experimental — guia de implementação

Documento de apoio à proposta de TCC *"O que a porta espectral realmente
contribui?"*. Destina-se a quem vai escrever o código. Cada estágio traz
**contrato de interface**, **critério de aceitação** e **armadilhas conhecidas**.

Este é um estudo de *benchmark*. A credibilidade depende inteiramente de os
competidores clássicos serem implementados com justiça — mais do que de qualquer
sofisticação do braço neural. O pipeline foi organizado em torno disso.

---

## Visão geral

```
[0] Protocolo de avaliação único   ←  a fundação; tudo se conecta aqui
        ↓
[1] Camada de dados          →  (X, y, eixo, unidade)
        ↓
[2] Braços clássicos         →  PLS, iPLS, CARS, GA-PLS, VIP
        ↓          ↘
[3] Braços neurais           →  MLP puro, ponderação fixa, porta uniforme, porta+prior
        ↓          ↙
[4] Camada de seleção        →  conjunto de k bandas, cardinalidade pareada
        ↓
[5] Executor da grade        →  12 braços × 4 conjuntos × 2 eixos de semente
        ↓
[6] Métricas                 →  desempenho, Jaccard, química, custo
        ↓
[7] Decomposição + TOST      →  os cinco termos, com testes de equivalência
        ↓
[8] Figuras e manuscrito
```

Ordem obrigatória: **[0] antes de tudo**. O protocolo de avaliação não é
documentação — é código, e é o que garante que os doze braços sejam comparáveis.

---

## Estágio 0 — Protocolo de avaliação único

**Objetivo.** Que seja estruturalmente impossível avaliar dois braços de formas
diferentes.

**Contrato.**

```python
def evaluate(arm: Arm, dataset: Dataset,
             seed_split: int, seed_algo: int) -> Result
# Result:
#   r2, rmse, rmsep        no teste externo
#   selection: set[int]    bandas selecionadas (ver Estágio 4)
#   n_fits: int            número de ajustes de modelo consumidos
#   wall_time: float
#   hyperparams: dict      escolhidos na CV interna
```

Todo braço implementa a mesma interface `Arm`. Nenhum braço tem acesso ao teste
externo, e nenhum recebe hiperparâmetros escolhidos fora da validação cruzada
interna.

**Os dois eixos de semente.** Esta é a decisão de projeto mais importante do
trabalho e a mais fácil de errar:

| Eixo | O que varia | Para que serve |
|---|---|---|
| `seed_split` | partição treino/teste | variabilidade amostral; generalização |
| `seed_algo` | aleatoriedade interna do método | instabilidade algorítmica |

Eles medem coisas diferentes e **não podem ser confundidos**. Jaccard calculado
variando `seed_algo` com `seed_split` fixo mede instabilidade do algoritmo.
Jaccard variando `seed_split` mede estabilidade sob perturbação dos dados.

**Consequência que altera H5 da proposta.** PLS, iPLS e limiarização de VIP são
determinísticos dado o conjunto de treino: com `seed_split` fixo, o Jaccard deles
é trivialmente 1. Comparar a porta contra eles no eixo `seed_algo` seria uma
derrota garantida e sem significado. **A afirmação de reprodutibilidade deve ser
feita no eixo `seed_split`**, onde todos os métodos variam e a comparação é
legítima. Reporte os dois eixos, mas a conclusão do manuscrito sai do eixo de
partição. Discuta isso com a orientação antes de congelar o protocolo.

**Orçamento auditável.** `n_fits` e `wall_time` existem para que "orçamento
equivalente de ajuste" seja verificável, e não uma alegação. Se o GA-PLS consumir
40× mais ajustes que o MLP, isso precisa aparecer na tabela.

**Critério de aceitação.** Um braço trivial (predizer a média) atravessa
`evaluate` e produz `Result` válido. Dois braços quaisquer, com mesma
`seed_split`, recebem exatamente a mesma partição — verificado por teste.

---

## Estágio 1 — Camada de dados

Idêntico em contrato ao usado no estudo paralelo de parametrizações; se aquele
código já existir, reutilize em vez de reimplementar.

```python
def load(name: str) -> Dataset
#   X (n,p), y (n,), axis (p,), unit: "nm" | "cm-1", name
```

Conjuntos: `gasoline`, `tecator`, `mango`, `bioprocess`.

**Pré-processamento.** Fixado no protocolo e **idêntico para todos os braços**.
Se houver dúvida entre SNV e derivada, escolha um e registre; comparar métodos sob
pré-processamentos distintos invalida o benchmark. Variação de pré-processamento,
se desejada, entra como fator declarado, nunca como escolha por braço.

**Critério de aceitação.** Testes de formato, ausência de `NaN`, coerência entre
`len(axis)` e `X.shape[1]`, e determinismo da partição dada `seed_split`.

---

## Estágio 2 — Braços clássicos

**O portão de credibilidade do trabalho inteiro.**

**Braços.** `pls_full`, `ipls`, `cars`, `ga_pls`, `vip_threshold`.

**Regra de implementação.** Prefira implementações estabelecidas a reescrever.
Onde for necessário implementar, siga o artigo original e registre no ADR cada
decisão que o artigo deixa em aberto (número de intervalos, critério de parada,
tamanho da população).

**Ajuste justo.** Cada método tem seus próprios hiperparâmetros e todos vão à
validação cruzada interna: número de componentes latentes (todos), número de
intervalos (iPLS), número de execuções de Monte Carlo e razão de amostragem
(CARS), tamanho de população e gerações (GA-PLS), limiar (VIP).

**Critério de aceitação — não negociável.** Antes de qualquer comparação com
braços neurais, reproduzir valores publicados de RMSEP para Tecator e Gasoline
com iPLS e CARS, dentro da faixa reportada na literatura. Registre a referência e
o valor obtido lado a lado na monografia.

> Se o CARS implementado for pior que o CARS publicado, o benchmark é inválido e
> será rejeitado em revisão. Este portão vem antes de tudo que interessa.

**Armadilha.** Seleção de variáveis **dentro** da validação cruzada, nunca antes
dela. Selecionar bandas usando todo o conjunto de treino e depois validar é
vazamento, e é o erro mais comum na literatura de seleção em quimiometria.
Escreva um teste que falhe se a seleção enxergar a partição de validação.

---

## Estágio 3 — Braços neurais

**Braços.** `mlp_full` (B1), `mlp_weighted` (B2, ponderação fixa pelo prior, sem
gradiente na porta), `gate_uniform` (B3), `gate_prior` (B4).

**Regra.** O regressor MLP é **byte a byte o mesmo** nos quatro braços: mesma
arquitetura, mesma inicialização dada a semente, mesmo otimizador, mesmo
orçamento de épocas. A única diferença permitida entre B1 e B2 é a presença da
ponderação; entre B2 e B4, o fato de a porta receber gradiente; entre B3 e B4, o
valor de inicialização da porta.

Essa disciplina é o que torna a decomposição interpretável. Uma diferença
acidental de hiperparâmetro entre B1 e B2 contamina $\Delta_{\text{ponderação}}$
e não há como detectar isso depois.

**Verificação contra o modelo de referência.** `gate_prior` deve reproduzir o
modelo publicado do grupo dentro da dispersão entre sementes. Vendorize esse
modelo com SHA-256 e não o edite.

**Critério de aceitação.**
1. B2 com porta congelada em 1,0 produz resultado estatisticamente idêntico a B1
   (teste de sanidade da implementação).
2. B4 reproduz o braço de referência.
3. Teste que compara os hiperparâmetros efetivos dos quatro braços e falha se
   divergirem em qualquer campo além dos permitidos.

---

## Estágio 4 — Camada de seleção

**Objetivo.** Converter a saída de qualquer braço num conjunto de bandas
comparável entre métodos.

```python
def to_selection(arm_output, k: int) -> set[int]
```

- Métodos com seleção explícita (iPLS, CARS, GA-PLS): o conjunto que devolvem.
- VIP e portas contínuas: as `k` bandas de maior escore/peso.
- `pls_full` e `mlp_full`: sem seleção; excluídos das métricas de seleção.

**Cardinalidade pareada.** `k` é fixado no protocolo e igual ao número médio de
bandas retidas pelos métodos clássicos no conjunto em questão. Jaccard entre
conjuntos de tamanhos diferentes é enganoso — conjuntos maiores tendem a
sobreposição maior por acaso.

**Critério de aceitação.** Análise de sensibilidade: as conclusões sobre
reprodutibilidade se mantêm para `k` variando em uma faixa declarada (por
exemplo, ±50% do valor nominal). Se não se mantiverem, isso é resultado e deve
ser reportado.

---

## Estágio 5 — Executor da grade

**Grade.** 12 braços × 4 conjuntos × 10 `seed_split`. Para os braços
estocásticos (CARS, GA-PLS, os quatro neurais), acrescentar 10 `seed_algo` com
`seed_split` fixo, para a análise de instabilidade algorítmica.

**Requisitos.**

- Sementes propagadas explicitamente e separadas por eixo.
- Teste automatizado que rejeita réplicas idênticas — compare o hash do resultado
  entre sementes; coincidência indica propagação quebrada. Exceção esperada e
  declarada: braços determinísticos no eixo `seed_algo`.
- Retomada por `run_id`; reexecução pula o que já concluiu.
- Proveniência por execução: commit, versões, dispositivo.
- `n_fits` e `wall_time` gravados sempre.

**Critério de aceitação.** Reexecutar a grade com as mesmas sementes reproduz os
resultados dentro da tolerância de não determinismo documentada.

---

## Estágio 6 — Métricas

Funções puras sobre `results/`. Nada calculado dentro do laço de treinamento.

**Desempenho.** R², RMSE, RMSEP no teste externo.

**Reprodutibilidade da seleção.** Jaccard médio par a par entre conjuntos de
bandas, calculado separadamente nos dois eixos de semente. Reporte ambos;
conclua pelo eixo `seed_split`.

**Plausibilidade química.** Fração das `k` bandas selecionadas que caem em
janelas de atribuição espectroscópica documentada. Tabele as janelas e suas
fontes — vira tabela do manuscrito.

**Custo.** `n_fits` e `wall_time` por braço, incluindo a busca interna.

**Critério de aceitação.** Cada métrica tem teste com entrada sintética de
resposta conhecida. Métrica sem teste não entra no manuscrito.

---

## Estágio 7 — Decomposição e equivalência

**Regra central da decomposição.** Cada termo é calculado **pareado**, por
`(conjunto, seed_split)`, e só depois agregado:

```
Δ_não-lin[d,s]      = R²(B1,d,s) − R²(A1,d,s)
Δ_ponderação[d,s]   = R²(B2,d,s) − R²(B1,d,s)
Δ_aprendizado[d,s]  = R²(B4,d,s) − R²(B2,d,s)
Δ_prior[d,s]        = R²(B4,d,s) − R²(B3,d,s)
```

Calcular os termos a partir de médias marginais quebra o pareamento, invalida os
testes pareados e faz a soma deixar de reconstituir B4 − A1. Escreva um teste que
verifique a identidade aditiva por `(conjunto, semente)`.

Note que $\Delta_{\text{aprendizado}}$ e $\Delta_{\text{prior}}$ não são
ortogonais — ambos envolvem B4. A decomposição aditiva usa os três primeiros
termos; $\Delta_{\text{prior}}$ é contraste complementar e deve ser apresentado
como tal, não somado aos demais.

**Equivalência (TOST).** Para cada termo declarado nulo em H2–H4: dois testes
unilaterais contra a margem $\pm\delta$ fixada no protocolo. A conclusão só é
"equivalente" se ambos rejeitarem. Reporte sempre o intervalo de confiança ao
lado da margem — é a figura mais informativa do artigo.

**Armadilha fatal.** A margem $\delta$ é escolhida **antes** de ver os
resultados, com justificativa em termos de relevância prática (que diferença de
R² importaria a um analista?). Margem escolhida depois invalida H2–H4 inteiras.

**Comparação global.** Friedman entre braços sobre os conjuntos, com pós-teste
pareado e correção para múltiplas comparações.

---

## Estágio 8 — Figuras

1. **Cascata da decomposição**: barras empilhadas de A1 até B4, mostrando quanto
   cada termo contribui. É a figura principal do artigo.
2. **Intervalos de confiança × margem de equivalência**, um por termo.
3. **Desempenho × reprodutibilidade**, um ponto por braço — a figura que sustenta
   H5. O quadrante desejado é "acurácia equivalente, Jaccard alto".
4. **Jaccard nos dois eixos de semente**, lado a lado, com os braços
   determinísticos marcados.
5. **Bandas selecionadas por método**, sobrepostas ao espectro médio e às janelas
   de atribuição química.
6. **Custo computacional por braço** (escala log).
7. **Decomposição por regime amostral**, testando H7.

---

## Primeira semana: a fatia mínima

**Tecator + A1 (`pls_full`) + B1 (`mlp_full`) + 1 semente**, atravessando os
estágios 0→7 e produzindo o primeiro termo da decomposição,
$\Delta_{\text{não-lin}}$.

Esse único número já é informativo: se for grande, H1 ganha suporte imediato e
todo o enquadramento do trabalho se confirma na primeira semana. Só depois
acrescente braços.

---

## Checklist de reprodutibilidade

- [ ] ADR para cada decisão deixada em aberto pelos artigos originais
- [ ] Protocolo pré-registrado congelado, **com a margem $\delta$ declarada**
- [ ] Braços clássicos validados contra valores publicados
- [ ] Seleção de variáveis dentro da CV, com teste anti-vazamento
- [ ] Dois eixos de semente separados e documentados
- [ ] Teste que rejeita réplicas idênticas (com exceções declaradas)
- [ ] Identidade aditiva da decomposição verificada por teste
- [ ] `n_fits` e `wall_time` gravados por execução
- [ ] Cardinalidade `k` pareada, com análise de sensibilidade
- [ ] Toda métrica com teste de entrada sintética

---

## Ordem de implementação recomendada

| Semana | Foco |
|---|---|
| 1–2 | Estágio 0 — protocolo de avaliação, dois eixos de semente, interface `Arm` |
| 3 | Estágio 1 + testes |
| 4–7 | Estágio 2 — braços clássicos e **validação contra a literatura** |
| 8–9 | Estágio 3 — braços neurais e verificação contra o modelo de referência |
| 10 | Estágio 4 + fatia mínima ponta a ponta |
| 11–12 | Protocolo congelado, margem declarada, piloto em Tecator |
| 13+ | Estágios 5–8 (segundo semestre) |

Quatro semanas para os braços clássicos não é excesso. É a parte do trabalho que
determina se o artigo sobrevive à revisão, e é também onde o Rodrigo aprende
quimiometria de verdade — o que, para um TCC, é um efeito colateral desejável.
