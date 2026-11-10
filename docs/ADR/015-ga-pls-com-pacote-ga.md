# ADR 015 — GA-PLS com o pacote GA e avaliação própria

**Data:** 2026-10-29
**Status:** proposto

## Contexto

Terceiro braço clássico do Estágio 2, depois do iPLS (ADR 012) e do VIP (ADR
014). O ADR 008 (proposto) escolheu o `plsVarSel::ga_pls` para o GA-PLS. O
pipeline manda preferir implementação estabelecida, seguir o artigo original
onde for preciso implementar, registrar em ADR o que ele deixa em aberto
("tamanho da população", entre outros) e levar à validação cruzada interna o
"tamanho de população e gerações (GA-PLS)".

**O `ga_pls` não serve como está.** Lido o código do `plsVarSel` 0.10.0 e
conferido rodando em `scripts/verificar_ga_pls_plsvarsel.py` (DIARIO de
29/10):

1. a seleção devolvida é o cromossomo com mais variáveis, não o de menor
   erro (no Tecator, 14 bandas com PRESS 1018,0, quando havia 9 com 880,7);
2. a avaliação usa folds aleatórias do pacote `pls`, sem as do protocolo e
   sem os grupos do ADR 009;
3. o PRESS é sempre o de 4 componentes, sem a regra de um erro-padrão e sem
   autoescala;
4. cromossomo com menos de 2 variáveis recebe PRESS fixo 100, que não
   depende da escala de y.

Usá-lo seria comparar contra um braço em desvantagem por defeito de
implementação.

**O que foi lido.**

- Scrucca (2013), "GA: A Package for Genetic Algorithms in R", *Journal of
  Statistical Software* 53(4), acesso aberto: a função `ga()`, seus
  argumentos e padrões, e o exemplo de seleção de subconjunto em
  regressão, com cromossomo binário e fitness pelo AIC.
- Mehmood, Sæbø e Liland (2020), *J. Chemometrics* 34, e3226, Seção 3.2.1: o
  GA-PLS em cinco passos (população binária, ajuste de um PLS por
  cromossomo, sobrevivência dos melhores, cruzamento e mutação), atribuído a
  Hasegawa, Miyashita e Funatsu (1997); Tabela 2: o parâmetro de mutação
  ajustado por RMSEP ficou em R0 = 8,39.
- O código do pacote GA 3.2.5 instalado: operadores binários padrão
  (`gabin_lrSelection`, `gabin_spCrossover`, `gabin_raMutation`) e população
  inicial (`gabin_Population`, cada bit com chance 0,5).

**Não lidos:** Hasegawa et al. (1997), o GA-PLS de Leardi, e Dayal e MacGregor
(1997), o kernel PLS usado na avaliação (ver abaixo). A correção do kernel
PLS foi conferida numericamente, não contra o artigo.

## Decisão

**Motor genético:** `GA::ga(type = "binary")`, pacote GA 3.2.5, via `rpy2`,
com os operadores e as taxas padrão do pacote: seleção por ranking linear,
cruzamento de um ponto com probabilidade 0,8, mutação de um bit por
cromossomo com probabilidade 0,1, e elitismo de 5% da população.

**Avaliação de cada cromossomo:** menos o RMSE médio de uma validação cruzada
com o PLS do projeto (autoescala, como o A1), nas folds do protocolo. Dentro
de cada fold externo, as folds internas são os outros blocos do protocolo
(`_inner_folds`, do iPLS), que respeitam os grupos do ADR 009. Cromossomo
vazio recebe −∞.

**Avaliação por kernel PLS.** Com o `PLSRegression`, uma avaliação custava
0,77 s no Mango e 3,18 s no bioprocess, e a busca aninhada passaria de 20
horas por partição no bioprocess (estimativa). A avaliação calcula o PLS de
resposta única pelo algoritmo kernel de Dayal e MacGregor (1997) sobre `X'X`
e `X'y` de cada fold, calculados uma vez com todas as bandas. Avaliar um
subconjunto vira recortar essas matrizes, e o custo deixa de depender do
número de amostras. O resultado é o mesmo do `PLSRegression` a menos de
arredondamento (diferença relativa até 3,8e-13 nos quatro conjuntos, DIARIO
de 29/10), e um teste permanente compara os dois. O modelo entregue continua
sendo o `PLSRegression`, pelo `_fit_pls` do iPLS e do VIP.

**Escolha final:** o melhor cromossomo da execução (`@solution` do GA; em
empate, o primeiro). É o oposto do `ga_pls`, que devolve o de mais
variáveis.

**População inicial:** cada banda começa selecionada com chance **0,1**, e
não 0,5 como no padrão do pacote. Medido em 29/10: com 0,5, o braço terminou
com 38 a 49% das bandas nos quatro conjuntos, porque a mutação troca um bit
por vez e não consegue reduzir uma população que começa com metade. O 0,1
fica entre o padrão do `plsVarSel` (1 selecionada para 10 não selecionadas,
cerca de 9%) e o valor ajustado em Mehmood et al. (2020), R0 = 8,39, cerca de
11%. Que o R0 deles seja esse mesmo parâmetro é leitura minha do artigo, que
não o define com essa precisão. A densidade não vai à CV: é escolha declarada
deste ADR.

**População e gerações vão à CV**, como o pipeline pede, entre dois
candidatos declarados a priori:

```
(população, gerações) ∈ {(30, 50); (50, 100)}
```

(50, 100) é o padrão do pacote GA; (30, 50) é uma busca menor. Escolha pela
regra de um erro-padrão sobre o RMSE da CV, com desempate para o candidato de
**menos bandas em média** nos folds, o mesmo critério de parcimônia do VIP.

**Número de componentes:** regra de um erro-padrão do `PLSArm` sobre todo o
`X_train`, como no iPLS e no VIP, recortado pelo número de bandas do
cromossomo. Vai fixo (`n_components`) no verificador anti-vazamento, junto
com a configuração (`ga_config`).

**Sementes:** de `rng_algo` (`seed_algo`) saem uma semente do R por fold e
uma para o ajuste final, passadas ao `seed` do `ga()`. São as mesmas para os
dois candidatos, para a comparação entre eles não depender da sorte.

**`n_fits`:** conta um ajuste por fold interna em cada avaliação, mais os
ajustes de pontuação e o modelo entregue. Cada ajuste aqui é um kernel PLS
barato, então o `n_fits` do GA-PLS **não é comparável em tempo** com o dos
outros braços: é muito maior em contagem e bem menor em custo por ajuste.

## Consequências

`src/tcc/arms/gapls.py` (`GAPLSArm`, nome `ga_pls`, e `kernel_pls_rmse`) e
`tests/test_gapls.py`, com 13 testes:

- kernel PLS igual ao `_fit_pls` em subconjuntos sorteados, com 1, 3 e 6
  componentes, e com recorte de componentes;
- desempate pelo candidato de menos bandas;
- seleção, seleções por fold e predição;
- mesma `seed_algo`, mesma seleção; outra semente, seleção diferente;
- a seleção final é a de melhor fitness da execução;
- população inicial com cerca de 10% das bandas;
- o verificador anti-vazamento do ADR 011, junto com uma versão vazada (GA
  rodado no treino inteiro) que ele reprova;
- a contagem de ajustes e a busca entre candidatos.

Nove mutações conferidas: devolver o cromossomo de mais bandas, kernel sem
ortogonalizar, sem autoescala, desempate pelo primeiro, orçamento sem as folds
internas, semente fixa, densidade 0,5, sem a população própria e validação
centrada na própria média. Cada uma derruba pelo menos um teste, e o arquivo
foi restaurado com o hash conferido.

Nova dependência: pacote R `GA` 3.2.5, registrada na proveniência do ADR
008 (adendo de 29/10). O `plsVarSel` continua instalado, mas o braço não o
usa.

**Custo medido** com densidade 0,1 (`scripts/medir_custo_gapls.py`,
`seed_split` 0, `seed_algo` 0, busca completa). Os R² são de uma partição
só, para conferir o encanamento, e não são resultado:

| conjunto | PLS: R² | GA-PLS: R² | (pop., ger.) | bandas | ajustes | tempo |
|---|---|---|---|---|---|---|
| Tecator | 0,9660 | 0,9646 | (30, 50) | 16 de 100 | 111.030 | 14,9 s |
| Gasoline | 0,9839 | 0,9755 | (50, 100) | 40 de 401 | 126.415 | 18,4 s |
| Mango | 0,8676 | 0,8794 | (50, 100) | 54 de 281 | 126.694 | 228,6 s |
| bioprocess | 0,8677 | 0,8703 | (30, 50) | 185 de 1870 | 112.899 | 479,7 s |

O bioprocess, que passaria de 20 horas com o `PLSRegression` na avaliação,
rodou em 8 minutos. O tempo varia entre execuções: o mesmo PLS completo do
Mango levou 46,7 s numa rodada e 143,4 s nesta.

**Limitação que fica.** Nos dois conjuntos de mais bandas, o número final
ficou perto da densidade inicial: 10% no Gasoline e 9,9% no bioprocess,
contra 16% no Tecator e 19% no Mango. Com a mutação de um bit por vez, a
densidade inicial funciona como uma preferência forte pelo tamanho do
subconjunto. É isso que a CV dessa densidade, recusada aqui por custo,
mediria. Fica registrado como fragilidade do braço, a discutir com a
orientação.

Decisão minha, não vista pela orientação. Fica como proposta
até ela ver, junto com o ADR 008, cuja escolha do `plsVarSel` para o GA-PLS
este ADR substitui.
