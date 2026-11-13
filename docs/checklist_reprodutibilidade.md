# Checklist de reprodutibilidade

Os dez itens do checklist do pipeline (`docs/fontes/pipeline_tcc_rodrigo.md`,
"Checklist de reprodutibilidade"), um por um, com onde está a prova.
Situação em 13/11/2026 (commit `cd68ddb`).

| # | item do pipeline | situação | onde está a prova |
|---|---|---|---|
| 1 | ADR para cada decisão deixada em aberto pelos artigos originais | ✅ feito | `docs/ADR/`, 21 ADRs (001 a 021); os dos braços registram o que cada artigo deixa em aberto (012 iPLS, 014 VIP, 015 GA-PLS, 016 CARS, 017 rede) |
| 2 | Protocolo pré-registrado congelado, **com a margem δ declarada** | ❌ falta | `docs/PROTOCOLO.md` está **provisório**. O limite inferior do δ por conjunto está declarado (seção do δ), mas o δ final não; o congelamento espera a receita do Mango e as decisões dos ADRs 017 a 021 |
| 3 | Braços clássicos validados contra valores publicados | ⚠️ em parte | **CARS:** reproduz o achado do artigo nos dados de milho e o RMSEP de Zhong et al. (2023) no Gasoline (ADR 016). **iPLS, VIP e GA-PLS:** sem valor publicado no Tecator ou no Gasoline (pergunta 11, em aberto). **B4 (rede):** reproduz o artigo semente a semente (ADR 017) |
| 4 | Seleção de variáveis dentro da CV, com teste anti-vazamento | ✅ feito | `tests/test_selection_leakage.py` (ADR 011), aplicado ao iPLS, VIP, GA-PLS e CARS, cada um com uma versão vazada que o teste reprova; na rede, o prior que não vê a fold de parada (`tests/test_gate.py`) |
| 5 | Dois eixos de semente separados e documentados | ✅ feito | ADR 001; `evaluate()` deriva partição e folds só de `seed_split`; o executor grava as duas sementes e roda o eixo `seed_algo` só nos braços estocásticos (ADR 021) |
| 6 | Teste que rejeita réplicas idênticas (com exceções declaradas) | ✅ feito | `tests/test_protocol.py` (réplicas entre `seed_split`, e entre `seed_algo` com a exceção dos determinísticos); `identical_replicas` do executor, com teste (ADR 021) |
| 7 | Identidade aditiva da decomposição verificada por teste | ✅ feito | `tests/test_decomposition.py::test_additive_identity_holds_in_every_partition`; e em dados reais do Tecator, com diferença zero (ADR 020) |
| 8 | `n_fits` e `wall_time` gravados por execução | ✅ feito | cada arquivo do executor (ADR 021); com uma thread por processo, para o tempo ser comparável entre braços |
| 9 | Cardinalidade `k` pareada, com análise de sensibilidade | ⚠️ em parte | o código existe (`paired_k`, `k_grid`; ADR 018, com testes), mas **de onde sai o `k`** está em aberto e **a análise de sensibilidade ainda não rodou** (é da grade) |
| 10 | Toda métrica com teste de entrada sintética | ✅ feito | `tests/test_metrics.py` (16 testes; ADR 019), também conferidas contra o scikit-learn e o scipy; o TOST e o Holm, contra o statsmodels e o R base (ADR 020). As janelas químicas estão em `src/tcc/windows.py` (12 testes), com a largura como parâmetro obrigatório: falta decidir a largura (`docs/janelas_quimicas.md`) |

## O que falta, em ordem

1. **A receita de treino do Mango** (ADR 017, item 7), que destrava o
   `c_TOST` do Mango.
2. **As decisões dos ADRs 017 a 021** e das janelas químicas: o `k`, a
   métrica do δ, os blocos do Friedman, a largura das janelas.
3. **O δ final e o congelamento do protocolo** (item 2).
4. **A grade final**, que fecha o item 9 (análise de sensibilidade do `k`).
5. **A pergunta 11**, para o item 3: se a validação do iPLS, do VIP e do
   GA-PLS pode ficar sem valor publicado, já que a busca não achou nenhum
   nesses conjuntos.
