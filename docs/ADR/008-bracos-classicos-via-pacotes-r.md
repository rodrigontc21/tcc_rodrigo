# ADR 008 — Braços clássicos via pacotes R

**Data:** 2026-09-16
**Status:** proposto

## Contexto

O portão de validação do Estágio 2 exige reproduzir os valores de RMSEP
publicados usando iPLS e CARS especificamente. As implementações de
referência desses métodos estão em pacotes R: `mdatools` (iPLS) e
`plsVarSel` (CARS, GA-PLS, VIP). Em Python não localizei implementação
canônica dos três — os pacotes de quimiometria em Python que encontrei
são de escopo geral e nenhum se apresenta como implementação de
referência desses métodos. O pipeline do trabalho recomenda preferir
implementação estabelecida a reescrever.

Antes de decidir, um spike foi executado em 16/09 para validar a
viabilidade: ambiente migrado para WSL (Ubuntu 24.04), R atualizado de
4.3.3 para 4.6.1 pelo repositório do CRAN (o do Ubuntu está parado no
4.3.3, e o `rpy2` 3.6 exige R ≥ 4.5), `rpy2` 3.6.7 instalado em modo API,
`mdatools` 0.16.0 e `plsVarSel` 0.10.0 instalados e carregando. A suíte de
56 testes do projeto passa no ambiente novo.

## Decisão

Implementar iPLS, CARS e GA-PLS chamando os pacotes R via `rpy2`.

Implementar VIP em Python: é fórmula fechada sobre pesos e loadings do
PLS, sem risco relevante de divergência, e não justifica atravessar a
ponte.

Isolar o `rpy2` atrás da interface `Arm` existente: cada braço R é uma
classe que converte numpy para R na entrada e de volta na saída, e nenhuma
outra parte do projeto sabe que existe R.

Registrar como proveniência as versões: R 4.6.1, `rpy2` 3.6.7,
`mdatools` 0.16.0, `plsVarSel` 0.10.0, `pls` 2.9-0.

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

Se a orientação preferir Python, o custo é reimplementar três algoritmos a
partir dos artigos e validar cada um contra valores publicados — o que
transfere o risco de divergência da comparação para a implementação.

Nenhum braço foi implementado nesta data: este ADR documenta a proposta,
pendente de aprovação da orientação, que ainda não se manifestou sobre
ela.
