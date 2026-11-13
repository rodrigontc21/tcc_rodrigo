# ADR 021 — O executor da grade (Estágio 5)

**Data:** 2026-11-13
**Status:** proposto

## Contexto

O Estágio 5 do pipeline: a grade de braços × conjuntos × `seed_split`, e,
para os braços estocásticos, `seed_algo` com `seed_split` fixo. Requisitos:
sementes explícitas e separadas por eixo; teste que rejeita réplicas
idênticas, comparando o hash do resultado entre sementes, com a exceção
declarada dos braços determinísticos no eixo `seed_algo`; retomada por
`run_id`; proveniência por execução (commit, versões, dispositivo); `n_fits`
e `wall_time` sempre. **Critério de aceitação:** reexecutar com as mesmas
sementes reproduz os resultados dentro da tolerância de não determinismo
documentada.

## Decisão proposta

`src/tcc/grid.py` e `tests/test_grid.py`.

- **A grade como configuração** (`GridSpec`): conjuntos, braços, as
  `seed_split` da grade principal com um `seed_algo` base, e o eixo
  `seed_algo` numa partição fixa só para os braços estocásticos. A célula
  que já está na grade principal não se repete no eixo do algoritmo. Os
  valores finais (faixa ≥ 100, quantas sementes) entram quando o protocolo
  congelar.
- **Braços por referência importável** (`ArmSpec`: "módulo:fábrica" e
  argumentos por nome), para atravessar processos, com a marca de
  determinístico.
- **`run_id`** = conjunto, braço, `seed_split` e `seed_algo`, legível.
- **Um arquivo JSON por execução**, escrito de forma atômica (arquivo
  temporário e troca de nome), com o resultado inteiro: R², RMSEP,
  RMSECV, `n_fits`, `wall_time`, seleção, escores de banda, predições,
  índices do teste, hiperparâmetros e proveniência. Rodar de novo pula o que
  já tem arquivo. Uma execução que falha grava o erro em
  `<run_id>.erro.txt`, não derruba a grade e é tentada de novo na próxima
  vez.
- **Proveniência:** commit, se havia mudança não commitada, Python, versões
  de numpy, scipy, scikit-learn, torch, pandas e rpy2, processador,
  sistema, variáveis de thread e threads do torch. Calculada uma vez por
  processo, porque o `git status` na pasta do Windows vista pelo WSL leva
  perto de um segundo.
- **Uma thread por processo**, fixada no ambiente antes de os processos
  nascerem, e paralelismo só entre execuções (ADR 017; orientação de
  12/11). Com uma thread, o mesmo código dá o mesmo número (ADR 017,
  reprodução do B4).
- **`identical_replicas`:** acusa pares com predições idênticas entre
  partições, e entre sementes do algoritmo fora dos braços determinísticos.
- **`load_results`:** lê os arquivos de volta como `Result`, prontos para
  as métricas (ADR 019) e a decomposição (ADR 020).

**Testes (12):** a montagem das tarefas, com o eixo do algoritmo só nos
estocásticos; nome de braço repetido; a fábrica com argumentos por nome;
uma grade real pequena (Tecator, média, PLS, VIP e B4-limpo, duas
partições e três sementes do algoritmo no B4) gravada inteira; os
resultados lidos iguais a um `evaluate()` direto, inclusive a seleção do
VIP; a retomada sem reescrever nada; a proveniência (o commit igual ao
`git rev-parse HEAD`, threads em 1); **o critério de aceitação: rodar do
zero em outra pasta dá os mesmos hashes**; uma falha gravada e tentada de
novo; nenhuma réplica idêntica na grade real; e réplicas idênticas
detectadas nos dois eixos, com a exceção dos determinísticos.

Nove mutações, todas pegas. Uma, perder a seleção na leitura, escapou na
primeira rodada, porque a grade de teste não tinha nenhum braço com
seleção explícita; o VIP entrou nela. O teste de argumento nomeado do
projeto (30/10) pegou duas chamadas `Task(...)` posicionais minhas,
corrigidas. Suíte inteira: 257 passaram, 1 pulado.

## Em aberto

1. **A configuração da grade final:** os braços (com o B4-fiel, o B5 no
   `c_TOST` e o B2'), as `seed_split` (≥ 100, quantas) e o eixo do
   algoritmo (quantas sementes, em qual partição). Depende do
   congelamento.
2. **A pergunta 8** (diagonal ou média sobre réplicas de `seed_algo`): o
   executor roda o que a configuração pedir; a decomposição recusa célula
   repetida até isso ser decidido (ADR 020).
3. **A tolerância de não determinismo:** com uma thread, a reexecução deu
   hashes iguais nos testes. Se aparecer diferença em outra máquina, ela
   entra declarada.
4. **O tamanho dos arquivos:** cada execução grava as predições e os
   escores; no bioprocess são uns 1.600 valores de teste e 1.870 bandas por
   arquivo, o que cabe com folga. A pasta da grade fica fora do git, como o
   resto de `results/`.

## Conferência (13/11/2026)

`scripts/conferir_executor.py`, Tecator, `seed_split` 0–29, piloto:
- **contra resultados já medidos por outros scripts:** 180 execuções
  clássicas iguais a `bracos_tecator_30_particoes.csv` e 570 de rede iguais
  a `varredura_c.csv`, campo a campo, sem nenhuma diferença;
- **interrompida de verdade** (SIGKILL com 220 de 660 gravadas): nenhum
  arquivo corrompido; retomada, as 660 ficaram idênticas, pelo hash, às da
  grade sem interrupção;
- **a cadeia inteira** (grade → leitura → métricas → decomposição) dá os
  mesmos números tirados por fora do executor. Detalhes no DIARIO de 13/11.

