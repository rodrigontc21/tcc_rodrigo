# ADR 012 — iPLS via mdatools

**Data:** 2026-09-28
**Status:** proposto

## Contexto

Primeiro braço clássico do Estágio 2. O pipeline manda preferir
implementação estabelecida a reescrever e **registrar em ADR cada decisão
que o artigo original deixa em aberto** — cita nominalmente "número de
intervalos". O [ADR 008](008-bracos-classicos-via-pacotes-r.md) (proposto)
escolheu `mdatools` via `rpy2` para o iPLS.

Antes de escrever este documento, um spike inspecionou a API real do
pacote (28/09/2026), porque decidir sobre parâmetros sem saber o que o
pacote expõe seria adivinhação. Proveniência conferida na mesma sessão:
**rpy2 3.6.7, R 4.6.1, mdatools 0.16.0, plsVarSel 0.10.0, pls 2.9.0**,
biblioteca de usuário em `~/R/x86_64-pc-linux-gnu-library/4.6`.

Assinatura de `mdatools::ipls`:

```r
ipls(x, y, glob.ncomp = 10, center = TRUE, scale = FALSE,
     cv = list("ven", 10), exclcols = NULL, exclrows = NULL,
     int.ncomp = glob.ncomp, int.num = NULL, int.width = NULL,
     int.limits = NULL, int.niter = NULL, ncomp.selcrit = "min",
     method = "forward", x.test = NULL, y.test = NULL,
     silent = FALSE, full = FALSE, cv.scope = "local")
```

Três achados do spike, com a evidência ao lado:

**1. As folds do protocolo podem ser injetadas.** O corpo de
`mdatools::crossval` começa com

```r
if (is.numeric(cv) && length(cv) == nobj) return(as.matrix(cv))
```

ou seja, um vetor numérico de comprimento `n` com o índice do segmento de
cada amostra é aceito como está, sem passar pelo gerador interno. Como as
`cv_folds` de `evaluate` formam uma partição — todo registro é validação
em exatamente um fold, garantido por
`test_grouped_folds_keep_replicates_together` —, a conversão para vetor de
rótulos é bem definida. O braço usa as folds do protocolo, e não as
próprias, que era o risco registrado no
[ADR 001](001-folds-da-cv-interna-derivam-de-seed-split.md).

**2. A centragem interna não vaza.** `cv.scope = "local"` é o default:
centragem e escala são calculadas dentro de cada segmento de CV, não uma
vez sobre o conjunto inteiro.

**3. O critério de número de componentes conflita com o protocolo.** O
corpo de `selectCompNum.pls` tem exatamente dois ramos:

```r
switch(selcrit, wold = f(res, fWold), min = f(res, fMin), ncomp)
```

`"min"` (argmin puro, o default) e `"wold"`. **A regra de um erro-padrão
não existe no mdatools.** Ela está no pacote `pls`, em
`selectNcomp(method = c("randomization", "onesigma"))` — que é a família
usada pelo artigo de referência e a que o `PLSArm` deste trabalho
implementa, por correção apontada pela orientação em 14/09/2026.

Sem tratamento, o A1 escolheria complexidade por um-erro-padrão e o A3
por argmin. Isso fere o "ajuste justo" do pipeline não por orçamento
desigual, mas por **critério desigual**, e contraria diretamente a
observação da orientação em 14/09: *"se seu pipeline está pegando o
argmin puro, seu PLS não é o mesmo objeto que o PLS do artigo, e a
comparação com o valor publicado no Estágio 2 fica sem âncora."*

## Decisão

**Implementação.** `mdatools::ipls` via `rpy2`, com namespace explícito em
toda chamada — `mdatools::` escrito, nunca `library()` — por causa do
mascaramento entre `pls` e `mdatools` registrado no ADR 008. O `rpy2`
fica isolado atrás da interface `Arm`: conversão numpy→R na entrada,
R→numpy na saída, e nenhuma outra parte do projeto sabe que existe R.

**Folds.** As `cv_folds` injetadas por `evaluate` são convertidas em vetor
de rótulos de segmento e passadas em `cv`. O braço nunca chama o gerador
interno do mdatools.

**Direção.** `method = "forward"`, que é o default do pacote e o caminho
mais barato. Backward fica como análise de sensibilidade, se houver
motivo, e nunca como escolha feita depois de ver resultado.

Ressalva: o `mdatools` oferece as duas direções, mas **não foi verificado
aqui** o que Nørgaard et al. (2000) de fato apresentam — o artigo ainda
não foi lido (ver "Não verificado neste documento"). A escolha por
forward apoia-se no default do pacote, não no artigo.

**Número de intervalos.** Vai à validação cruzada interna, como o pipeline
exige ("número de intervalos em iPLS ... ajustados por validação cruzada
interna"). Usa-se `int.num` — e não `int.width` nem `int.limits`, que são
as outras duas formas mutuamente exclusivas de definir os intervalos —
com faixa de candidatos declarada a priori:

```
int.num ∈ {10, 15, 20, 25, 30}
```

A mesma faixa nos quatro conjuntos, o que mantém comparável o orçamento
de busca entre eles. A consequência é que a **largura** do intervalo varia
por conjunto, já que `p` varia: no Tecator (p=100) 20 intervalos dão 5
canais cada; no Gasoline (p=401), 20; no Mango (p=306), 15; no bioprocess
(p=1870), 93. Isso é deliberado — o número de intervalos é o parâmetro
ajustável, não a largura.

**Número de componentes.** `ncomp.selcrit` do mdatools não é usado para
decidir complexidade. Em vez disso, `glob.ncomp` é fixado no valor que a
regra de um erro-padrão do `PLSArm` escolhe sobre o mesmo `X_train` e as
mesmas folds. Assim a regra de complexidade é a mesma em
todos os braços, e o mdatools faz o que ele faz bem — a busca de
intervalos.

Ressalva declarada, e é séria: um subconjunto de intervalos tem menos
variáveis que o espectro inteiro, e o número de componentes justificável
muda com isso. Fixar pelo ajuste de espectro completo pode ser generoso
demais para um subconjunto pequeno. A alternativa — aplicar a regra de um
erro-padrão dentro de cada candidato de intervalo — exigiria reimplementar
por fora a busca do mdatools, o que anula a razão de usar o pacote.

**`int.ncomp` é recortado pela largura do intervalo, e isso limita a
afirmação acima.** Um PLS com mais componentes que variáveis é
degenerado, e com `int.num` alto os intervalos ficam estreitos — no
Tecator (p=100), `int.num = 30` dá intervalos de 3 canais. O código usa
`int.ncomp = min(glob.ncomp, largura)`. A consequência, declarada porque
enfraquece a uniformidade prometida: **nos candidatos maiores da faixa, a
complexidade dentro do intervalo fica abaixo do valor da regra de um
erro-padrão**, enquanto o A1 usa o valor cheio. A regra é a mesma; o valor
efetivo nem sempre. A alternativa seria restringir a faixa de `int.num`
para que a largura nunca desça abaixo de `glob.ncomp`, o que amarraria a
faixa ao conjunto e ao alvo — mais arbitrário que o recorte.

(Uma primeira versão deste ADR dizia que `int.ncomp` também era fixado no
valor da regra, o que o código nunca fez. Corrigido em 28/09/2026, numa
vistoria do próprio dia.)

O critério é **parâmetro do braço**, com o valor acima como default
proposto. Trocá-lo é mudança de uma linha.

**Seleção aninhada.** O `mdatools::ipls` escolhe os intervalos pela CV
agregada sobre todas as folds, então uma chamada devolve **uma** seleção,
propriedade do treino inteiro — que é o formato descrito pela armadilha do
Estágio 2 ("selecionar bandas usando todo o conjunto de treino e depois
validar"). O braço portanto roda o `ipls` **uma vez por fold, só sobre
`fold_train`**, e uma vez sobre o treino inteiro para o ajuste final. O
custo é o preço da validade, e aparece no `n_fits` como o pipeline quer.

**O regressor é o do projeto, não o do mdatools.** O `ipls` é usado só
para selecionar; o modelo final é o mesmo `PLSRegression` do `PLSArm`.
Assim A1 e A3 diferem por exatamente uma característica — o subconjunto de
variáveis —, que é o que torna o termo da decomposição interpretável. Se o
mdatools ajustasse o modelo, qualquer diferença de implementação do PLS
entraria no termo junto com o efeito da seleção.

**`glob_ncomp` também é parâmetro, e não só `int_num`** (achado de
28/09/2026, ver Consequências).

## Consequências

`cv_selections` (ADR 011) é preenchido com os canais dos intervalos
selecionados dentro de cada fold, e o braço passa pelo
`assert_selection_is_fold_local`. É o primeiro braço real a atravessar
aquele verificador, que até aqui só foi exercitado por sondas sintéticas.

**O verificador reprovou o braço na primeira execução (28/09/2026), e
estava certo em reprovar.** Com apenas `int_num` fixo, perturbar as linhas
de validação de um fold mudava a seleção daquele fold — mas não por
vazamento: o `glob_ncomp` era buscado pela regra de um erro-padrão sobre
todo o `X_train`, agregando as folds, e entrava em todas as execuções do
iPLS, inclusive nas de cada fold. É precisamente o falso positivo que o
ADR 011 antecipou ao exigir hiperparâmetro fixo durante a verificação.

A correção foi tornar `glob_ncomp` parâmetro do braço: neste braço, "fixo"
quer dizer `int_num` **e** `glob_ncomp`. Com os dois fixos o verificador
passa. O episódio tem valor próprio — foi o primeiro contato do
verificador com um braço real, e o ponto fraco que ele expôs era do
verificador, não do braço.

Registrado também o que o disparo **não** é: universal. Num problema
sintético pequeno a perturbação não chega a mudar a escolha do
`glob_ncomp`, e com só `int_num` fixo o verificador passa. Por isso o
teste de regressão (`test_fixed_glob_ncomp_bypasses_the_search`) verifica
o mecanismo — que o valor fixo corta a busca — e não o sintoma, que
depende dos dados.

`n_fits` conta os ajustes consumidos pela busca de intervalos, para que o
orçamento comparado com CARS, GA-PLS e os braços neurais seja auditável
como o pipeline exige. O valor é **estimado** a partir do que o mdatools
reporta — iterações da busca forward em `int.stat`, intervalos restantes
por iteração, segmentos de CV — e declarado como estimativa, porque o
interior do pacote não é instrumentado. Contar 1 por chamada do `ipls`
dava 6 ajustes contra 101 do `pls_full` num caso em que o iPLS gastava 25×
mais tempo, o que inverteria a tabela de custo do manuscrito.

**Folds internas do braço.** O `ipls` roda uma CV própria para pontuar
intervalos. Como `Arm.fit` não recebe `dataset.groups`, o braço não teria
como respeitar sozinho a regra do ADR 009 — réplicas nunca em folds
diferentes. As folds internas são portanto os **outros blocos de validação
das folds externas**, reindexados para a posição dentro de `fold_train`:
a garantia vem de `_make_cv_folds` e o braço não precisa conhecer os
grupos. A primeira versão fatiava `arange(n)` contiguamente e partia 664
grupos num teste com réplicas densas; no Tecator passava por acaso, por
haver só 7 pares.

O iPLS é determinístico dado o treino, então o mapeamento `seed_algo` →
`set.seed(R)` exigido pelo ADR 008 não é exercitado aqui; ele entra com o
CARS, que é o primeiro braço estocástico em R.

**Pendente de orientação — pergunta nova.** A escolha do critério de
componentes não é decisão de implementação, é metodológica, e cai
exatamente na classe de coisas que a orientação pediu para levar em ADR
("eu aprovo o ADR, não a escolha solta numa mensagem", 14/09/2026). Entra
como pergunta 10 em `PERGUNTAS.md`, junto das que já esperam resposta
desde 21/09. O código não fica bloqueado por ela, por ser parâmetro.

**Não verificado neste documento.** A faixa `int.num ∈ {10,…,30}` é
declarada a priori por este ADR, mas não foi conferida contra Nørgaard et
al. (2000) — o artigo ainda não foi lido, e essa leitura é parte da
revisão dirigida, que continua pendente. Se o artigo original indicar
faixa diferente, este ADR é corrigido **antes** de qualquer execução que
entre em resultado, e nunca depois de ver desempenho. Registrado aqui para
que a lacuna não passe por decisão fundamentada.
