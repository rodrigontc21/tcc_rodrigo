# ADR 007 — Alvo do bioprocess: glicose

**Data:** 2026-09-14
**Status:** proposto

## Contexto

O conjunto `bioprocess_substrates` é obtido pelo pacote `raman-data`
(RamanBench, Koddenbrock et al., 2026), que por sua vez o traz de
`huggingface.co/datasets/chlange/SubstrateMixRaman`. São espectros Raman
com eixo em número de onda (cm⁻¹), e o conjunto traz **oito alvos
possíveis** na mesma matriz de rótulos: Glucose, Glycerol, Acetate,
EnPump, Nitrate, Yeast_Extract, total_phosphate e total_sulfate.

O protocolo deste trabalho avalia um alvo contínuo por conjunto, então é
preciso escolher um dos oito. O loader `_load_bioprocess()` em
`src/tcc/data.py` já usa glicose desde a ingestão, selecionada **por
nome** e não por posição (mesma disciplina do ADR 004), mas com um
comentário marcando a escolha como PROVISÓRIA: ela nunca havia sido
formalizada com a orientação.

## Decisão

Confirmar a **glicose** como alvo único do conjunto de bioprocesso.

Justificativa (orientação, 14/09/2026): é o alvo mais reportado na
literatura de monitoramento de bioprocesso e o de melhor razão
sinal-ruído em Raman — escolha defensável para um único alvo.

## Consequências

O comentário "PROVISÓRIO" em `_load_bioprocess()` (`src/tcc/data.py`)
deixa de ser válido: quando este ADR for aprovado, ele vira comentário
definitivo citando este documento como a decisão que fixa o alvo. Nenhum
outro comportamento do loader muda — a seleção por nome, o descarte dos
488 espectros sem rótulo de glicose (restando 6.472) e o `sha256` sobre
todos os oito alvos continuam como estão, e o pino
`EXPECTED["bioprocess"]` em `tests/test_data.py` não é afetado.

Os outros sete alvos permanecem carregados na fonte e entram no `sha256`,
mas não são avaliados. Se em algum momento a orientação quiser um segundo
analito, isso é um conjunto adicional na grade, não uma troca deste — e
exigiria novo ADR, porque mudaria o que a linha "bioprocess" da
decomposição significa.

Fica registrado como limitação: a escolha de um alvo único é uma decisão
de escopo, não uma afirmação de que a glicose seja o analito mais difícil
ou mais informativo dos oito. As conclusões do trabalho para este
conjunto valem para glicose, e não se estendem automaticamente aos demais.

O código **não** foi editado nesta data: este ADR documenta a mudança
pendente da aprovação da orientação sobre a redação exata.
