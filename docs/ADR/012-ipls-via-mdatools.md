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

**O valor pedido não é sempre o executado** (medido em 28/09/2026, achado
de vistoria independente). O mdatools converte o número de intervalos em
largura, arredonda essa largura, e recalcula quantos intervalos cabem em
`p`. Nos três conjuntos com `p` conhecido:

| conjunto | pedido → executado |
|---|---|
| Tecator (p=100) | 15 → 14, 30 → 33 |
| Mango (p=306) | 25 → 26, 30 → 31 |
| Gasoline (p=401) | 30 → 31 |

A faixa realmente avaliada, portanto, não é `{10, 15, 20, 25, 30}` em
todos os conjuntos. O objeto devolvido pelo pacote carrega o valor
executado, e é ele que vai ao `hyperparams`, no campo
`int_num_executed`, ao lado do pedido: registrar só o pedido descreveria
um experimento que não aconteceu. Nenhuma correção é aplicada ao valor —
forçar o número exato exigiria passar `int.limits` à mão, o que
substituiria a divisão do pacote pela nossa e sairia do "usar
implementação estabelecida".

**Regra de desempate entre candidatos** (acrescentada em 28/09/2026: o
código a aplicava desde o início e este ADR não a declarava — omissão
apontada por vistoria independente).

O `int_num` é escolhido pela mesma regra de um erro-padrão do `PLSArm`:
entre os candidatos cujo RMSE de CV fica dentro de um erro-padrão do
mínimo, fica o **menor** `int_num`.

**Essa regra tem o sinal invertido, e fica registrada como problema, não
como decisão defendida.** No `PLSArm`, "menor candidato" significa menos
componentes, logo modelo mais simples — a regra faz sentido. Aqui, menos
intervalos significa intervalos **mais largos**, logo **mais** bandas
retidas. Medido no Tecator, `seed_split` 0:

| `int.num` | largura | bandas selecionadas |
|---|---|---|
| 10 | 10 | 30 |
| 15 | 6 | 35 |
| 20 | 5 | 10 |
| 25 | 4 | 8 |
| 30 | 3 | 6 |

O menor `int_num` é o menos parcimonioso em número de variáveis, que é a
grandeza que importa num método de seleção. No mesmo `seed_split`, o menor
erro de CV estava em `int.num = 25`, a regra escolheu 10, e o resultado no
teste externo caiu de R² 0,9710 (com 20 fixo) para 0,9415.

**Nada é alterado agora, deliberadamente.** Trocar o critério depois de
ver esses números seria escolher regra olhando resultado, que é o que o
pré-registro proíbe. A regra em vigor continua declarada como está, com o
defeito exposto, e a escolha vai à orientação (**pergunta 12**). Se ela
mudar, os números do Tecator registrados no DIARIO de 28/09 precisam ser
refeitos, e isso está anotado lá.

**Número de componentes — o que o pacote realmente faz.** Esta seção foi
reescrita em 28/09/2026, depois de uma vistoria independente mostrar que a
versão anterior descrevia o mecanismo errado. O registro do erro fica no
fim da seção, porque ele afeta o que já foi perguntado à orientação.

Dentro de `ipls.forward`, **cada intervalo candidato é ajustado e pontuado
com o `ncomp.selcrit`**, que por padrão é `"min"`; o vencedor de cada
passada sai do RMSE calculado com o `ncomp.selected` daquele intervalo. Ou
seja, a complexidade usada na seleção é escolhida **por intervalo, pelo
critério do mdatools**, e não fixada por fora. O `glob.ncomp` define o
modelo global — que não participa da escolha dos intervalos — e serve de
**teto** via `int.ncomp`.

Evidência (Tecator, `seed_split` 0, teto 8, `int.num` 20):

| `ncomp.selcrit` | nComp escolhido por intervalo | bandas selecionadas |
|---|---|---|
| `"min"` | 5, 5, 4, 6, 4 | 20 |
| `"wold"` | 4, 2, 3, 5, 4, 3, 3 | 30 |

Os dois fatos que isso estabelece: o número de componentes **varia entre
intervalos**, logo não está fixado; e **trocar o critério muda a seleção**,
logo ele não é inerte. Com o teto 3 que a regra de um erro-padrão devolve
na `seed_split` 0 o efeito não aparece, o que explica por que passou
despercebido.

**Decisão.** `glob.ncomp` continua fixado no valor da regra de um
erro-padrão do `PLSArm`, como teto — isso é real e continua valendo. Mas a
afirmação de que "a regra de complexidade é a mesma em todos os braços"
**não se sustenta**: dentro da busca de intervalos, quem decide é o
`ncomp.selcrit`. O parâmetro fica exposto no braço, com `"min"` como
default do pacote, e a escolha vai à orientação (pergunta 10).

Alinhar de verdade exigiria aplicar a regra de um erro-padrão dentro de
cada candidato de intervalo, o que significa reimplementar por fora a
busca do mdatools — e anula a razão de usar o pacote. É a tensão que a
pergunta 10 leva à orientação.

**`int.ncomp` é recortado pela largura do intervalo.** Um PLS com mais
componentes que variáveis é degenerado, e com `int.num` alto os intervalos
ficam estreitos — no Tecator (p=100), `int.num = 30` deixa cerca de 3
canais por intervalo pela conta do braço, e 33 intervalos pela do pacote
(ver "O valor pedido não é sempre o executado", acima). O código usa
`int.ncomp = min(glob.ncomp, largura)`, com a largura calculada pelo braço
como `p // int.num`, então o teto
efetivo cai nos candidatos maiores da faixa. A alternativa seria restringir
a faixa de `int.num` para que a largura nunca desça abaixo de
`glob.ncomp`, o que amarraria a faixa ao conjunto e ao alvo — mais
arbitrário que o recorte.

**Registro do erro.** Até 28/09/2026 este ADR afirmava que o
`ncomp.selcrit` "não é usado para decidir complexidade" e que `glob.ncomp`
e `int.ncomp` eram fixados no valor da regra de um erro-padrão. As três
afirmações eram falsas: o `selcrit` decide, o `int.ncomp` sempre foi
recortado pela largura, e o `glob.ncomp` é teto e não valor efetivo. A
evidência já estava à vista desde o spike — a coluna `nComp` do `int.stat`
mostrava valores diferentes por linha — e não foi lida. A **pergunta 10**
foi escrita sobre essa premissa e teve de ser reescrita antes de ir à
orientação.

**Escalonamento — seletor e regressor otimizam geometrias diferentes.**
O `mdatools` pontua os intervalos com `center = TRUE, scale = FALSE`, que
é o default do pacote. O `PLSRegression` que ajusta o modelo final
autoescala, que é o default do scikit-learn e o que o `PLSArm` (A1) usa.
Ou seja, os intervalos são escolhidos sob uma métrica e o modelo entregue
é ajustado sob outra.

Efeito medido no Tecator, `int.num = 20`, seis `seed_split` da faixa
exploratória, comparando a seleção com `scale = FALSE` e com
`scale = TRUE`:

| `seed_split` | bandas (FALSE) | bandas (TRUE) | Jaccard | R² (FALSE) | R² (TRUE) |
|---|---|---|---|---|---|
| 0 | 10 | 10 | 0,333 | 0,9710 | 0,9669 |
| 1 | 15 | 30 | 0,500 | 0,9549 | 0,9526 |
| 2 | 20 | 15 | 0,750 | 0,9735 | 0,9712 |
| 3 | 10 | 10 | 1,000 | 0,9722 | 0,9722 |
| 4 | 50 | 15 | 0,182 | 0,9685 | 0,9651 |
| 5 | 10 | 10 | 1,000 | 0,9710 | 0,9710 |

**O efeito é desprezível na acurácia e grande na seleção.** As diferenças
de R² ficam na terceira casa e sem vencedor consistente. Já o Jaccard
médio entre as duas configurações é 0,63 — mais de um terço do conjunto de
bandas muda por causa de uma opção de escalonamento que ninguém declarou.

Isso importa desproporcionalmente neste trabalho: a **H5 é sobre
reprodutibilidade do conjunto de bandas, medida por Jaccard**. Uma escolha
de implementação que move o Jaccard nessa magnitude não pode ficar
implícita, sob pena de o efeito atribuído ao método ser, em parte, efeito
de um default de pacote.

**Nada é alterado agora.** `scale` vira parâmetro do braço, com o default
`False` do pacote preservado, e a escolha vai à orientação
(**pergunta 13**). A proposta que eu defenderia é alinhar o seletor ao
regressor (`scale = TRUE`), porque o intervalo deveria ser escolhido sob a
mesma geometria em que o modelo final será julgado; o argumento contrário
é que `FALSE` é o default da implementação de referência, e o pipeline
manda preferir implementação estabelecida. Não é decisão que eu deva tomar
sozinho.

Descartada de saída uma terceira via — desligar o autoescalonamento do
`PLSRegression` no A3 —, porque aí o A3 deixaria de usar o mesmo regressor
do A1 e a decomposição perderia a propriedade de os braços diferirem por
exatamente uma característica.

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

**Nota (10/11/2026): a regra de réplicas do Tecator mudou.** Em 09/11 a
orientação decidiu corrigir a regra de réplicas do Tecator (ADR 009), e os
grupos foram de 208 a 180. Com isso, as partições do Tecator mudaram.
- **As tabelas de diagnóstico do Tecator neste ADR foram medidas com a
  partição anterior:** o `int_num` contra as bandas, o `ncomp.selcrit` e o
  escalonamento. Elas mostram que cada fenômeno existe e sustentam as
  perguntas 10, 12 e 13; não são resultado, e não foram refeitas.
- **O braço foi medido de novo** com `scripts/medir_custo_ipls.py`
  (`seed_split` 0): R² 0,9556, contra 0,9628 do PLS completo; `int_num`
  10, 20 bandas, 9.774 ajustes, 15,3 s.
