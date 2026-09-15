# ADR 004 — Proveniência do Tecator

**Data:** 2026-09-03
**Status:** aceito

## Contexto

O paper de referência (pgsg_0) descreve a faixa de gordura do Tecator como
7%–76%; a fonte carregada via `skfda`/`fda.usc` dá 0,9%–49,1%. A
investigação local (03/09) verificou em duas linguagens — Python e R via
WSL, `fda.usc` carregado direto — com resultado idêntico; confirmou que as
três colunas de alvo somam ~99% e que a correlação gordura×água é −0,988;
e constatou que o pacote R `pls`, citado no Data Availability do paper,
não distribui o Tecator entre seus datasets.

O orientador foi ao código de ingestão do grupo (pgsg_1) e confirmou: os
dados do paper vieram do OpenML (base 505), baixados via
`scripts/download_tecator.py` daquele repositório — nem do `pls`, nem da
UCI 171, as duas fontes que o artigo cita. O CSV do OpenML nomeia as três
últimas colunas como moisture, fat, protein; o loader usa as 215 primeiras
amostras (descarta 25 de extrapolação). O `y` bruto, antes de qualquer
padronização, tem min 0,9, max 49,1, média 18,14 — bate exatamente com os
números do `fda.usc`.

Conclusão: nenhum resultado do paper está comprometido; a faixa "7–76%" é
erro de prosa (no `summary()` do R, 7,30 é o 1º quartil da gordura e 76,60
é o máximo da água — leitura na diagonal de uma tabela-resumo).

## Decisão

Tecator canônico via `skfda` ou `fda.usc`, 215 amostras, 100 canais,
850–1050 nm, alvo fat selecionado por nome, nunca por posição, com hash do
arquivo carregado. A divergência entra como achado documentado, com data e
evidência.

## Consequências

A camada de dados fica fixada nesta fonte, e a pergunta nº 5 de
`estudo_rodrigo/PERGUNTAS.md` sai da fila. O loader (`data.py`) precisa de
correção: hoje seleciona o alvo por posição (`targets[:, 0]`), o que a
decisão proíbe; passa a selecionar por nome e a registrar o hash do que
carregou. O achado da divergência de prosa vira material de manuscrito,
com data e evidência.

Ressalva obrigatória: o loader inspecionado vive em pgsg_1, na pasta
`revision_pgsg_0_r1` (rodada de revisão) — isso confirma o que a revisão
usou; se a submissão original rodou em outra base de código, isso
permanece não verificado.
