# ADR 007 — Alvo do bioprocess: glicose

**Data:** 2026-09-14
**Status:** aprovado com pendência (17/09/2026) — falta a confirmação da
distribuição dos 488 espectros sem glicose

**Pendência.** Em 17/09/2026 a orientação aprovou a decisão com uma
pendência: ver a distribuição dos 488 espectros sem glicose contra
qualquer metadado disponível antes da aprovação definitiva. A análise está
na seção "Distribuição dos 488 espectros sem glicose", abaixo, e é
reproduzida por `scripts/audit_bioprocess_missing_glucose.py`; foi enviada
à orientação em 21/09/2026 para confirmação.

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

O comentário "PROVISÓRIO" em `_load_bioprocess()` (`src/tcc/data.py`) foi
substituído em 17/09/2026 por um comentário definitivo, citando este
documento como a decisão que fixa o alvo e registrando a limitação
descrita abaixo. Nenhum outro comportamento do loader muda — a seleção por
nome, o descarte dos 488 espectros sem rótulo de glicose (restando 6.472)
e o `sha256` sobre todos os oito alvos continuam como estão, e o pino
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

**Distribuição dos 488 espectros sem glicose** (investigação exigida pela
orientação antes da aceitação). A orientação pediu a distribuição dos 488
espectros sem rótulo de glicose contra qualquer metadado disponível — para
distinguir ausência aleatória de ausência estruturada (que introduziria
viés de seleção, ao contrário do corte por safra do Mango).

O schema do `bioprocess_substrates` não expõe coluna de corrida ou
condição experimental — só as colunas espectrais, os 8 alvos e a partição
treino/validação/teste do cache.

**Unidade de análise: amostra física, não espectro.** O catálogo do
`raman-data` marca este conjunto como agrupado (`is_grouped`), embora não
exponha a qual amostra cada espectro pertence. A estrutura aparece nos
dados: linhas vizinhas com os 8 alvos idênticos ocorrem muito acima do
acaso (em pares aleatórios de linhas, 0,01%), o que indica duas medições
da mesma amostra. Agrupando essas réplicas, os 6.960 espectros
correspondem a 5.089 amostras, e os 488 espectros sem glicose, a 355
amostras. Como as réplicas não são independentes, a análise abaixo conta
amostras. A identificação é aproximada — réplicas não vizinhas, ou que
caíram em splits diferentes, não são detectadas —, então 5.089 é um teto
para o número de amostras independentes. A mesma estrutura de réplicas
exige que a avaliação nunca separe medições da mesma amostra entre treino
e teste — tratado no [ADR 009](009-particao-agrupada-por-amostra-fisica.md),
que agrupa por composição dos 8 alvos.

- **Sem concentração por split**: 6,88% (treino, 217/3.155), 7,64%
  (validação, 97/1.269), 6,17% (teste, 41/665) — qui-quadrado χ²=1,59,
  p=0,45, sem diferença significativa.
- **Sem bloco**: a sequência mais longa de amostras consecutivas sem
  glicose tem 3 amostras, dentro do esperado se a ausência estivesse
  espalhada ao acaso (teste de permutação), e as ausências cobrem toda a
  extensão de cada split — não há indício de uma corrida inteira sem
  glicose. Ressalva: a fonte não documenta se a ordem das linhas
  corresponde à ordem de aquisição, então este critério só detecta blocos
  se corresponder.
- **Não é falha de linha inteira**: nas amostras sem glicose, a ausência
  simultânea de outro alvo fica próxima da taxa basal desse alvo, exceto
  o glicerol, um pouco acima (6,2% contra 3,8%); `total_phosphate` e
  `total_sulfate` nunca têm ausência em nenhuma amostra.
- **Mas há associação real com condição experimental**: nas amostras sem
  glicose, EnPump e fosfato total são significativamente mais altos
  (Mann-Whitney, p<0,01 com correção de Bonferroni para as 7
  comparações) — EnPump quase dobra (média 1,39 contra 0,76), fosfato
  total sobe de 3,91 para 4,60. Os outros cinco alvos não mostram
  diferença.

Contar espectros em vez de amostras distorce esta análise: tratadas como
independentes, as réplicas dobram artificialmente o tamanho da amostra, e
o extrato de levedura aparece como significativo (p=0,0017), o que deixa
de ser verdade contando amostras (p=0,13).

**Conclusão**: a ausência não é aleatória pura, mas também não é um
bloco/corrida/split inteiro. É uma limitação declarada, não uma correção
no loader: o descarte introduz viés de seleção na faixa de condições com
EnPump e fosfato mais altos, que fica sub-representada no conjunto
avaliado. As conclusões do trabalho para glicose no bioprocess valem para
essa distribuição de condições, com a faixa de EnPump e fosfato altos
sub-representada.
