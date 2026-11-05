# ADR 008 — Braços clássicos via pacotes R

**Data:** 2026-09-16
**Status:** proposto

## Contexto

O portão de validação do Estágio 2 exige reproduzir os valores de RMSEP
publicados usando iPLS e CARS especificamente. O pipeline recomenda
preferir implementação estabelecida a reescrever, **sem indicar
linguagem**: em nenhum ponto ele menciona R, `rpy2` ou pacote algum, e
todos os blocos de código dele são Python. A escolha de linguagem é
inferência deste ADR, feita por onde as implementações estabelecidas
estavam — não é exigência do pipeline.

O critério, portanto, é **por método**, e não global:

| Braço | Implementação estabelecida | Linguagem |
|---|---|---|
| `ipls` | `mdatools` | R |
| `ga_pls` | `plsVarSel` | R |
| `vip_threshold` | fórmula fechada, sem pacote | Python |
| `cars` | `libPLS`, dos autores do método (ver abaixo) | R |

**Correção de 28/09/2026.** A primeira versão deste ADR afirmava que o
`plsVarSel` implementava CARS. **Não implementa.** Conferido no ambiente
do projeto: o `plsVarSel` 0.10.0 exporta 31 funções, nenhuma de CARS —
tem `ga_pls`, `VIP`, `mcuve_pls`, `spa_pls`, `bve_pls`, entre outras. O
`mdatools` 0.16.0 também não tem; tem `ipls` e `vipscores`. A afirmação
foi escrita sem verificação e sustentou a pergunta 4 enviada à orientação
em 21/09.

Antes de decidir, um spike foi executado em 16/09 para validar a
viabilidade: ambiente migrado para WSL (Ubuntu 24.04), R atualizado de
4.3.3 para 4.6.1 pelo repositório do CRAN (o do Ubuntu está parado no
4.3.3, e o `rpy2` 3.6 exige R ≥ 4.5), `rpy2` 3.6.7 instalado em modo API,
`mdatools` 0.16.0 e `plsVarSel` 0.10.0 instalados e carregando. A suíte de
56 testes do projeto passa no ambiente novo.

## Decisão

Implementar **iPLS** (`mdatools`) e **GA-PLS** (`plsVarSel`) chamando os
pacotes R via `rpy2`.

Implementar **VIP** em Python: é fórmula fechada sobre pesos e loadings do
PLS, sem risco relevante de divergência, e não justifica atravessar a
ponte.

Implementar **CARS** a partir do **`libPLS`**, e não de uma reimplementação
de terceiros. O libPLS é a biblioteca do grupo de **Hongdong Li**, primeiro
autor de Li et al. (2009), o artigo que define o CARS, e está descrito em
artigo próprio publicado em *Chemometrics and Intelligent Laboratory
Systems*. Site oficial: `libpls.net`; código em
`github.com/lhdcsu/libPLS`, cuja pasta `R/` traz `carspls.r` e
`carsplsorigin.r`. Como "implementação estabelecida", no sentido que o
pipeline usa, não existe candidata mais forte: é a dos próprios autores do
método, publicada e revisada.

A alternativa descartada é o `carsAlgo`, pacote no CRAN que se descreve
como *"inspired from the work of Li et al. (2009)"* — ou seja, uma
releitura de terceiros. Ele leva vantagem em empacotamento, e só nisso.
Tratando-se do portão que valida se o nosso CARS não está aleijado,
reimplementação de terceiros é exatamente o que não serve de referência.

**Proveniência do libPLS, que não é pacote.** São 17 arquivos `.r` soltos,
sem `DESCRIPTION` nem `NAMESPACE`: não há versão a fixar por gerenciador.
A disciplina do projeto se aplica assim mesmo — o código é obtido num
**commit fixo**, com o hash registrado aqui e o conteúdo conferido por
`sha256`, igual ao que já se faz com o tarball do `pls` (ADR 010) e com o
CSV do Mango (ADR 006). O commit entra neste ADR quando o braço for
implementado.

Isolar o `rpy2` atrás da interface `Arm` existente: cada braço R é uma
classe que converte numpy para R na entrada e de volta na saída, e nenhuma
outra parte do projeto sabe que existe R.

Registrar como proveniência as versões: R 4.6.1, `rpy2` 3.6.7,
`mdatools` 0.16.0, `plsVarSel` 0.10.0, `pls` 2.9-0, e o commit do libPLS.

## Consequências

Nova dependência de ambiente (R e pacotes R) a declarar na seção de
reprodutibilidade.

O `seed_algo` precisa ser mapeado explicitamente para o gerador do R
(`set.seed`) no início de cada `fit`, com teste automatizado verificando
que a mesma semente dá a mesma seleção e sementes diferentes dão seleções
diferentes — sem isso, a reprodutibilidade do eixo `seed_algo`, que
sustenta a H5, fica sem garantia.

Carregar `mdatools` e `plsVarSel` juntos causa mascaramento de nomes
(`pls::crossval` mascara `mdatools::crossval`, e `plsVarSel` sobrescreve
um método S3 do `pls`), então as chamadas devem usar namespace explícito.

Se a orientação preferir Python, o custo é reimplementar os algoritmos a
partir dos artigos e validar cada um contra valores publicados — o que
transfere o risco de divergência da comparação para a implementação. Para
o CARS existe o `auswahl` em Python, mas vale a mesma objeção do
`carsAlgo`: é reimplementação de terceiros, não a dos autores.

**Risco em aberto do libPLS.** A biblioteca é primariamente MATLAB; a
pasta `R/` é porte secundário, e não foi verificado se o `carspls.r` roda,
nem se reproduz o comportamento da versão MATLAB. Se não rodar, as opções
voltam a ser o `carsAlgo`, o `auswahl`, ou portar do MATLAB — e aí a
escolha volta à orientação. A verificação acontece antes de o braço ser
implementado, e o resultado entra neste ADR.

**Estado de implementação (28/09/2026).** O `ipls` está implementado e
testado (ADR 012), sob a proposta deste ADR e sem aprovação da orientação
— decisão registrada no DIARIO de 28/09. `cars`, `ga_pls` e
`vip_threshold` não existem ainda. A pergunta 4 enviada em 21/09 continua
sem resposta, e foi reescrita depois da correção sobre o `plsVarSel`.

**Adendo (28/10/2026).** O `vip_threshold` está implementado em Python, como
decidido aqui ([ADR 014](014-vip-com-limiar.md), proposto). Ao conferir a
fórmula contra os dois pacotes R, apareceu uma diferença que este ADR não
previa: o `plsVarSel::VIP` e o `mdatools::vipscores` não calculam o mesmo
VIP. O primeiro usa os pesos `W` do PLS, e o segundo, os pesos do SIMPLS. O
VIP do projeto segue o `plsVarSel`, com o detalhe no ADR 014. "Fórmula
fechada, sem risco relevante de divergência" valeu para a conta, mas não
para a escolha de qual fórmula usar.

**Adendo (29/10/2026).** O GA-PLS **não** usa mais o `plsVarSel::ga_pls`. Lido
o código e conferido rodando (`scripts/verificar_ga_pls_plsvarsel.py`), ele
devolve o cromossomo com mais variáveis em vez do de menor erro, avalia com
folds próprias e com número de componentes fixo, e dá nota fixa a
cromossomos de uma variável. O braço usa o motor do pacote R `GA` 3.2.5
(Scrucca 2013) com avaliação própria ([ADR 015](015-ga-pls-com-pacote-ga.md),
proposto). Proveniência acrescentada: `GA` 3.2.5. A decisão de usar o
`plsVarSel` foi tomada em 16/09 sem ler esse código.

**Adendo (05/11/2026): o CARS não sai do `carspls.r` do GitHub.** Este ADR
tratou o `github.com/lhdcsu/libPLS` como "a implementação dos autores".
Conferido em 05/11 (DIARIO), o quadro é outro:

- **O repositório é do autor, mas é um rascunho.** O perfil `lhdcsu` é do
  Hongdong Li e aponta para `libpls.net`. O repositório tem só a pasta
  `R/`, com 3 commits de 15/11/2015, e o primeiro diz *"very initial
  codes, which are not cleaned up yet"*.
- **O `carspls.r` depende do `Hmisc`, e o GitHub não diz isso.** Ele usa
  `ceil`, que não existe no R base. No R do projeto, só com o `pls`
  carregado, para na primeira iteração. O pacote original de 2009
  (`carspls_1.0.0`) declara `Depends: Hmisc, pls`, e o `Hmisc` tem um
  `ceil` com método padrão, pela documentação do CRAN; não instalei o
  `Hmisc` para conferir o comportamento. *(Corrigido em 05/11: a primeira
  versão deste adendo dizia só "não roda".)* De todo modo, o `carspls.r`
  é a versão simplificada, sem os dois sorteios.
- **O `carsplsorigin.r` tem o algoritmo original, mas difere do MATLAB:**
  - a curva EDF está deslocada um passo;
  - o número de variáveis é arredondado para baixo, e não para o inteiro
    mais próximo;
  - o RMSECV divide pelo total de amostras quando usa só 90% delas.
- **A distribuição oficial é o MATLAB.** O `libPLS_1.95.zip`, em
  `libpls.net`, sai sob GPL v2. Mas o `carspls.m` dessa versão tem como
  padrão `originalVersion = 0`, uma versão sem os dois sorteios (o de
  amostras e o ARS), que não é o CARS publicado.
- **O artigo descreve o CARS com os dois sorteios.** Li et al. (2009) foi
  lido na cópia que os autores publicaram no projeto `carspls` do Google
  Code (arquivado). O algoritmo dele é o do `carspls.m` da versão 1.50 do
  mesmo projeto (21/05/2011), igual ao `originalVersion = 1` do 1.95, com
  duas exceções: no 1.95, o número de componentes segue por padrão a regra
  de um desvio-padrão, e a validação cruzada ordena as amostras por `y`.

O CARS deste trabalho segue o artigo, conferido contra o `carspls.m` 1.50 e
o 1.95 com `originalVersion = 1`, e usa as folds do protocolo. A proposta
está no [ADR 016](016-cars-do-artigo-com-folds-do-protocolo.md). Nenhum
código do libPLS é executado nem versionado. Os arquivos ficam em
`docs/fontes/cars/`, pasta ignorada pelo git, identificados por `sha256`:

| arquivo | origem | sha256 |
|---|---|---|
| `carspls.m` (1.50) | Google Code `carspls`, `CARS_V1.50.rar` | `db89fb0508905960e8d45a81ef62194262ad4c8a3be1fe08633a03491c1fe4ae` |
| `carspls.m` (de 2010) | Google Code `carspls`, `CARS.rar` (21/05/2010) | `02c5ece95da8fab9a7421964a3534d971cc10af4fb644f90d5328fb63711aa24` |
| `carspls.m` (1.95) | `libpls.net`, `libPLS_1.95.zip` | `6741214a625b795248c93d760b28856f4576073ec7a4d24c8da22941b6b14273` |
| `carspls.r` | GitHub `lhdcsu/libPLS`, commit `0f92938` | `d77bf7abe1826ed673444e9df0af1f9eea4f158863df2db9b1a24f01fda3d7f5` |
| `carsplsorigin.r` | GitHub `lhdcsu/libPLS`, commit `0f92938` | `1699dfef414be7523dacc00a9575760241113c4b61fec49e842a0f744d47ae76` |
| pacote R `carspls_1.0.0.tar.gz` (lido: o `carspls.R` e o `carsplsorigin.R` são idênticos aos do GitHub) | Google Code `carspls` | `53366ffa150fe40c7fde260085b65965ba45f1ec467d1180f9a5a3a7f964930b` |
| artigo, cópia pessoal dos autores | Google Code `carspls`, `CARS.pdf` | `e64b37b260739672bb90f44a9f03a942aa02eea68fc03adae6aab68fd01a90ba` |
| `corn_m51.mat` (milho, m5, umidade; dados do artigo) | `libpls.net`, `libPLS_1.95.zip` | `36bf40e3ccd21a6c45cf2ed02192622b63cc22fc350a7014c95e3dcd169770cb` |
| `corn_m51.mat` (mesmos números, outro arquivo) | Google Code `carspls`, `CARS.rar` | `864b88907d7a5600520d4991660e4798979635fccb6ca5faf70ab5f210ddfc5e` |

O artigo é a "Author's personal copy" da Elsevier, para uso pessoal de
pesquisa, e não entra no repositório.
