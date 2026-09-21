# ADR 010 — Divisão de literatura do Gasoline

**Data:** 2026-09-21
**Status:** proposto

## Contexto

O critério de aceitação do Estágio 2 exige reproduzir valores publicados
de RMSEP no Tecator e no Gasoline. O modo "protocolo da literatura" (ADR
005, `src/tcc/validation.py`) só tinha divisão definida para o Tecator
(172/43 sequencial). Para o Gasoline, o paper de referência (pgsg_0,
Seção 4.1) diz apenas "We use a 48/12 train-test split", sem dizer quais
linhas vão para treino e quais para teste.

Investigação em 21/09/2026, em três frentes.

**Documentação do pacote R `pls`**, de onde vem o dado (tarball
`pls_2.9-0.tar.gz` do CRAN, a mesma URL de `_PLS_TARBALL_URLS` em
`src/tcc/data.py`):

- `man/gasoline.Rd` não define divisão nenhuma. Descreve só o formato
  ("A data frame with 60 observations on the following 2 variables"), a
  fonte (Kalivas, 1997) e a medição ("from 900 nm to 1700 nm in 2 nm
  intervals, giving 401 wavelengths").
- A vinheta do pacote (`vignettes/pls-manual.Rmd`, também em
  `inst/doc/pls-manual.R`) usa uma divisão **50/10 sequencial**, não
  48/12:

  ```r
  gasTrain <- gasoline[1:50,]
  gasTest <- gasoline[51:60,]
  ```

  O 50/10 é real, mas aparece como exemplo de uso do pacote, não como
  divisão canônica do conjunto. Nenhum arquivo do tarball menciona 48/12.
  O único outro uso do gasoline no pacote
  (`tests/RUnit/common/create_refmodels.R`) ajusta o modelo no conjunto
  inteiro, sem divisão.

**O próprio paper.** A Seção 4.2 diz que os resultados de teste único
são reportados "on the same data partition (seed 42)". O 48/12 é também
exatamente 80/20 de n = 60, e o 172/43 do Tecator é exatamente 80/20 de
n = 215. Os dois tamanhos batem, portanto, com uma divisão aleatória
80/20 com semente 42.

**Teste empírico.** PLS com o número de componentes do paper (H = 5 no
Gasoline, H = 10 no Tecator), Z-score de espectro e alvo ajustado só no
treino, métricas na escala normalizada, contra os valores publicados
(Tabela 1):

| conjunto | divisão | R² | RMSE |
|---|---|---|---|
| gasoline | **publicado** | **0,975** | **0,145** |
| gasoline | sequencial 48/12 | 0,9231 | 0,2752 |
| gasoline | sequencial 50/10 (vinheta do `pls`) | 0,9139 | 0,2930 |
| gasoline | `train_test_split(test_size=0.2, random_state=42)` | **0,9752** | **0,1453** |
| tecator | **publicado** | **0,919** | **0,296** |
| tecator | sequencial 172/43 (em uso) | 0,9604 | 0,2041 |
| tecator | `train_test_split(test_size=0.2, random_state=42)` | 0,9489 | 0,2365 |

No Gasoline, a divisão aleatória do scikit-learn com semente 42 reproduz
as duas métricas publicadas até a terceira casa decimal. Em 200 divisões
aleatórias 80/20, o R² do PLS H = 5 fica em 0,9737 ± 0,0173, e o valor
publicado cai no percentil 40: é um resultado típico, não uma partição
atípica. A divisão sequencial fica longe (0,923).

## Decisão

Divisão de literatura do Gasoline = `train_test_split(np.arange(60),
test_size=0.2, random_state=42)` do scikit-learn, 48 treino / 12 teste.
Os índices são ordenados antes do uso, o que não altera as métricas.

A proposta de partida era a divisão sequencial (primeiras 48 linhas no
treino, últimas 12 no teste), por precedente do Tecator neste mesmo
módulo. Ela foi descartada pela evidência: com ela, o PLS do paper não
se reproduz (R² 0,923 contra 0,975). A divisão aleatória com semente 42
reproduz os dois números publicados, e é compatível com as duas pistas
do próprio paper (80/20 e "seed 42").

**Decisão assumida, não descoberta.** Nenhuma fonte primária diz que o
paper usou `train_test_split` do scikit-learn. A evidência é a
reprodução numérica de duas métricas até a terceira casa, que é forte,
mas é inferência. A confirmação definitiva está no código do grupo
(pgsg_1), como foi feito para a proveniência do Tecator no ADR 004.

## Consequências

`evaluate_against_literature()` passa a aceitar `tecator` e `gasoline` e
continua rejeitando `mango` e `bioprocess`. A lógica de Z-score, folds
internas e `_fit_and_score` é a mesma nos dois conjuntos; só a escolha
dos índices depende do conjunto (`_literature_split`). O Gasoline não tem
grupos de réplica (ADR 009), então as folds internas não mudam por isso.
Teste: `test_reproduces_published_gasoline_pls` em
`tests/test_validation.py`, contra o valor publicado, com a mesma
tolerância (`abs=1e-3`) do teste do Tecator. O teste falha se a divisão
for trocada sem revisar este ADR.

A divisão depende da implementação de `train_test_split` do
scikit-learn. A versão está fixada em `requirements.txt`; se uma
atualização mudar o embaralhamento, o teste acima detecta.

Divergência registrada: a vinheta do pacote `pls` usa 50/10 sequencial;
o paper usa 48/12. Este trabalho segue o paper, porque é contra os
números dele que o portão compara.

**Achado lateral sobre o Tecator, fora do escopo desta decisão.** A mesma
hipótese (aleatória, semente 42) não reproduz o Tecator: dá R² 0,9489,
contra 0,919 publicado. A divisão sequencial em uso também não reproduz
(0,9604). O número publicado do Tecator continua sem explicação, e a
menção a "seed 42" põe em dúvida se a divisão do paper no Tecator era
sequencial. A divisão 172/43 sequencial foi aprovada em 01/09 (ADR 005)
e não muda aqui; fica registrada como pergunta à orientação, junto com
a do Gasoline.

Proposta pendente de aprovação da orientação. O código já está
implementado.

## Adendo (21/09/2026) — auditoria de robustez da semente 42

Mesmo portão de `validation.py` (PLS com H = 5 fixo, Z-score de espectro
e alvo ajustado só no treino), variando o `random_state` de
`train_test_split(test_size=0.2)` de 0 a 19999. O H é o fixo do portão, não
a regra de um erro-padrão: H = 5 é o que o paper obteve com essa regra.
Script: `scripts/audit_gasoline_split.py --n-seeds 20000` (cerca de 46 s),
que troca `tcc.validation.GASOLINE_SPLIT_SEED` a cada iteração, restaura o
valor no fim e não altera o `validation.py`. Saídas em
`results/gasoline_split_audit.{csv,md,png}`.

A auditoria foi ampliada em três rodadas, e cada uma corrigiu a anterior:

| sementes | batem os dois valores em 1e-3 | batem em 5e-4 (3 casas) |
|---|---|---|
| 200 | 1 (a 42) | 1 (a 42) |
| 2.000 | 6 | 1 (a 42) |
| 20.000 | 34 | 9 |

A aparente unicidade da semente 42 era efeito de amostra pequena, nas
duas tolerâncias. Os números a seguir são todos da rodada de 20.000.

| estatística | R² | RMSE |
|---|---|---|
| média | 0,9751 | 0,1408 |
| desvio-padrão | 0,0170 | 0,0267 |
| mínimo | 0,5588 | 0,0535 |
| máximo | 0,9966 | 0,2690 |
| percentil 5 | 0,9475 | 0,1012 |
| percentil 25 | 0,9700 | 0,1212 |
| percentil 50 | 0,9793 | 0,1381 |
| percentil 75 | 0,9852 | 0,1591 |
| percentil 95 | 0,9902 | 0,1876 |

Semente 42: R² = 0,975184, RMSE = 0,145343. Posição na distribuição
(`scipy.stats.percentileofscore`; strict, weak e rank coincidem):
**percentil 37,2 no R²** e **percentil 60,2 no RMSE**.

**Sensibilidade da tolerância.** Sementes a até a tolerância do valor
publicado, só no R², só no RMSE e nos dois. "Esperado" é a contagem
conjunta sob independência das duas métricas (produto das marginais ÷
20.000), e a razão é observado ÷ esperado.

| tolerância | batem R² | batem RMSE | batem os dois | Wilson 95% (os dois) | esperado | razão obs/esp |
|---|---|---|---|---|---|---|
| 1e-4 | 114 | 45 | 0 | [0,000%; 0,019%] | 0,26 | 0,00 |
| 5e-4 | 553 | 257 | 9 | [0,024%; 0,086%] | 7,11 | 1,27 |
| 1e-3 | 1.098 | 496 | 34 | [0,122%; 0,237%] | 27,23 | 1,25 |
| 5e-3 | 5.530 | 2.603 | 999 | [4,70%; 5,31%] | 719,73 | 1,39 |
| 1e-2 | 11.432 | 5.087 | 3.638 | [17,66%; 18,73%] | 2.907,73 | 1,25 |
| 5e-2 | 19.683 | 18.887 | 18.605 | [92,66%; 93,37%] | 18.587,64 | 1,00 |

Em 5e-4, as nove sementes são 42, 2385, 4460, 7819, 11363, 12106, 14263,
15657 e 18858. Arredondar para 3 casas, como o paper, dá exatamente o
mesmo conjunto. A proporção é 0,045%, com Wilson 95% [0,024%; 0,086%]:
cerca de 1 semente em 2.200.

Conferência da coluna "esperado" na rodada de 2.000, linha 5e-2 (R² 1.961,
RMSE 1.895): 1.961 × 1.895 = 3.716.095, e 3.716.095 ÷ 2.000 = 1.858,0475. O
valor 1.858,05 registrado antes estava certo. O script calcula a razão com
as contagens inteiras reais.

**Correlação entre R² e RMSE** nas 20.000 sementes: Pearson r = −0,503,
Spearman ρ = −0,665. A correlação é moderada, não perfeita. Numa divisão
fixa, R² = 1 − RMSE²/s², em que s² é a variância do alvo normalizado no
teste. Essa variância muda de divisão para divisão, e é isso que as duas
métricas carregam de informação distinta. Com 20.000 sementes, a razão
observado/esperado fica entre 1,25 e 1,39 em todas as tolerâncias não
saturadas; em 5e-2 vai a 1,00 porque quase todas as sementes batem. A
razão de 2,4 em 1e-3 que aparecia com 2.000 sementes (6 contra 2,5) era
ruído de contagem pequena. Tratar as duas métricas como independentes
superestimaria a raridade do acerto conjunto em cerca de 1,3×. As
proporções acima não têm esse problema, porque contam o acerto conjunto
diretamente, sem multiplicar probabilidades marginais.

**De onde vem o valor 42.** O valor não saiu desta auditoria: está no
texto do paper, pgsg_0, Seção 4.2 ("to enable direct comparison on the
same data partition (seed 42)"). O arquivo `docs/fontes/pgsg_0_paper.pdf`
está no repositório desde o commit `ff78fe5` (20/08/2026, "estrutura
inicial do projeto") e não foi alterado depois. A leitura dessa passagem
está registrada na seção Contexto deste ADR ("O próprio paper") e na
pergunta 9 de `docs/estudo_rodrigo/PERGUNTAS.md`, ambas de 21/09/2026. O
teste empírico do Contexto, feito num script avulso fora do repositório,
usou `random_state=42` antes das varreduras de 200, 2.000 e 20.000
sementes, mas isso também não tem comprovação por commit ou DIARIO: em
21/09/2026, nenhum commit do repositório contém `random_state`
(`git log -S`), e o `validation.py`, o `test_validation.py` e
`scripts/audit_gasoline_split.py` só tinham alterações não commitadas.
Ressalva: a leitura e as varreduras
aconteceram no mesmo dia, e nenhum commit ou entrada do DIARIO registra
a ordem entre elas. O que garante que a 42 não foi escolhida a posteriori
é o texto do paper, anterior a tudo isso, e não essa ordem.

A auditoria responde a duas perguntas distintas, que não devem ser
confundidas:

1. **A divisão do paper é atípica?** Não. A semente 42 fica perto da
   mediana nas duas métricas (percentis 37 e 60). O PLS publicado no
   Gasoline é um resultado típico de uma divisão 80/20 qualquer: nem
   favorável nem desfavorável ao PLS. É o contrário do achado de 03/09 no
   Tecator (DIARIO, não o ADR 004), onde o valor publicado caía no
   percentil 5 da nossa distribuição, sinal de partição atipicamente
   desfavorável.
2. **Bater os números identifica a semente 42?** Não por unicidade: na
   precisão do paper, 9 das 20.000 sementes reproduzem os dois valores, e
   a 42 é só uma delas. O argumento de unicidade, que as rodadas de 200 e
   2.000 pareciam sustentar, não se mantém.

   O que sobra é outra forma de argumento, e precisa ser lido como
   interpretação. O paper nomeia a semente 42 (Seção 4.2) antes de
   qualquer busca nossa, então não se escolheu a 42 entre várias depois de
   ver os resultados. A pergunta relevante é: se o paper não tivesse usado
   `train_test_split(test_size=0.2, random_state=42)`, qual seria a chance
   de essa chamada reproduzir por acaso os dois números publicados? A
   frequência medida responde: cerca de 0,045% (Wilson 95%: 0,024%–0,086%),
   já contando a correlação entre as métricas. Por esse critério, a
   hipótese deste ADR fica muito mais provável que a coincidência. As
   outras 8 sementes não competem com a 42, porque o paper não as menciona.
   Continua sendo inferência sobre qual função o paper chamou, não prova, e
   a confirmação definitiva segue sendo o código do pgsg_1.

   Objeção previsível: 42 é a semente-padrão de inúmeros exemplos do
   scikit-learn, então bater esse valor "não provaria nada". O motivo de
   os autores terem escolhido 42 é irrelevante para o que se testa aqui.
   Importa se rodar o pipeline com esse valor reproduz os números
   publicados, o que foi confirmado. A chance de isso ser coincidência
   (~0,045%) é a mesma qualquer que seja a razão da escolha, desde que o
   valor tenha sido fixado antes de se ver o resultado. Aqui ele foi,
   porque vem do texto do paper.

Limitação: só as sementes 0–19999 foram testadas. Os arquivos em
`results/` caem no `.gitignore` (`results/*`, com exceções nominais),
então os valores ficam registrados neste adendo para não depender deles.

### Tolerância do teste de reprodução: de 1e-3 para 5e-4

`test_reproduces_published_gasoline_pls` (`tests/test_validation.py`)
passa a usar tolerância 5e-4 no R² e no RMSE, meia unidade da terceira
casa publicada. Esta mudança substitui a frase da seção Consequências que
dizia "mesma tolerância (`abs=1e-3`) do teste do Tecator". O teste do
Tecator não muda.

Justificativa: 1e-3 é duas vezes mais frouxo que a precisão do número
publicado e aceitava 34 das 20.000 divisões da auditoria; 5e-4 aceita 9. O
teste continua não podendo distinguir a 42 dessas outras 8, porque os
números publicados não têm precisão para isso; fica, porém, mais
específico contra trocas de semente ou de lógica de divisão.

Verificação por mutação (21/09/2026), usando uma semente que a própria
auditoria achou "quase certa". A 239 bate em 1e-3 (R² 0,97456, RMSE
0,14443), mas não em 5e-4:

1. `GASOLINE_SPLIT_SEED = 239` em `validation.py`, tolerância ainda 1e-3:
   o teste **passa**. É um falso positivo: a 239 não reproduz o paper na
   precisão dele, mas o teste aceita.
2. Tolerância apertada para 5e-4 no teste.
3. Mesma semente 239: o teste **falha** no RMSE
   (`assert 0.1444314414795512 == 0.145 ± 5.0e-04`). O R² da 239 fica
   dentro de 5e-4; quem pega a mutação é o RMSE.
4. `validation.py` restaurado para a semente 42, com o hash conferido
   contra a cópia anterior à mutação; a suíte inteira passa
   (75 passed, 1 skipped).
