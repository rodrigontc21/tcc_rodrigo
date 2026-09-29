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
