# Diário de bordo

## 2026-08-20

**Feito**
- Estrutura do repositório criada (docs/src/tests/notebooks/results)
- Ambiente virtual configurado + bibliotecas básicas instaladas
- Git local + repositório remoto no GitHub conectados, primeiro commit e push
- Notebook exploratório: primeiro contato com o Tecator

**Problema resolvido**
Python 3.14 quebrava o scikit-fda: o módulo `distutils` foi removido a partir
do 3.12 e a dependência `skdatasets` ainda o utiliza. Migrado o venv para
Python 3.12.10. As duas versões convivem no sistema.

**Observações do dado (Tecator via scikit-fda)**
- X: (215, 100) — 215 amostras, 100 bandas
- Eixo espectral: 850 a 1050 nm
- Alvos disponíveis: fat, water, protein
- fat: 0.9 a 49.1% | water: 39.3 a 76.6% | protein: 11.0 a 21.8%
- Espectros têm formato muito parecido entre si, com pico dominante em ~975 nm
  (O–H, água) e um ombro discreto em ~930 nm (C–H, gordura — a região que o
  modelo do grupo prioriza)
- Distribuição do alvo é irregular, concentrada em 5–15% com cauda até 50%.
  Reforça a necessidade de múltiplas partições (10 seed_split do protocolo)

**Pendência aberta**
O paper (pgsg_0) descreve a gordura variando de 7% a 76%, mas a fonte que
carreguei dá 0.9% a 49.1%. Provável variante diferente do dataset (o Tecator
circula em versões com 215 e 240 amostras). Investigar no Estágio 1 —
candidato a ADR sobre proveniência dos dados.

**Próximo**
Estágio 0 — protocolo de avaliação único, interface `Arm`, contrato `Result`,
dois eixos de semente.

## 2026-08-24

**Feito**
- pytest 9.1.1 instalado, `requirements.txt` regravado
- Estágio 0 implementado: `src/tcc/data.py`, `src/tcc/protocol.py`,
  `src/tcc/arms/base.py`, `src/tcc/arms/mean.py`, `tests/test_protocol.py`,
  `pytest.ini`
- Os dois critérios de aceitação do pipeline passando (braço trivial
  atravessa `evaluate` e produz `Result` válido; dois braços com a mesma
  `seed_split` recebem a mesma partição), mais um terceiro teste

**Decisões de projeto**
- As folds da CV interna derivam de `seed_split`, não de `seed_algo`. Assim
  variar `seed_algo` mede instabilidade algorítmica pura, sem misturar com
  mudança de folds — e todos os braços ensaiam sobre exatamente as mesmas
  folds, que é o que torna a comparação entre eles legítima.
- `Arm.fit()` não recebe `X_test` nem `seed_split`. Vazamento do teste
  externo deixa de ser questão de disciplina do programador e vira
  impossibilidade de tipo: o braço não tem como enxergar o que não lhe é
  passado. Mesma lógica para `seed_split` — só `evaluate` conhece essa
  semente, e é ela quem deriva as folds e as injeta.
- Nenhum RNG global. `SeedSequence(seed_split).spawn(2)` gera dois streams
  independentes, um para a partição e outro para as folds, sem que o avanço
  de um mexa no outro. `seed_algo` alimenta um terceiro gerador, separado.
- `rmse_cv` virou propriedade de `FittedArm`, não cálculo de `evaluate`. Só
  o braço sabe o erro da própria CV interna — o protocolo não tem como
  recalculá-lo sem replicar a busca de hiperparâmetro de cada método.
- `IdentityPreprocessor` como placeholder, mas já com `fit`/`transform`
  separados e ajustado só no treino. O ponto de encaixe fica no lugar certo
  desde agora, para que trocar pela transformação real no Estágio 1 não
  exija mexer em `evaluate`.

**Próximo**
Auditoria do que foi escrito, antes de seguir para o Estágio 1.

## 2026-08-25

**Feito**
- Auditoria do Estágio 0 contra os documentos de `docs/`
- Achado crítico corrigido e verificado

**O achado crítico**
`test_deterministic_arm_is_invariant_to_seed_algo` usava o `MeanArm`, que
ignora `rng_algo` por completo. O teste passava por construção: não havia
aleatoriedade nenhuma para o `seed_algo` perturbar, então a invariância era
trivial e o invariante que o nome promete proteger ficava desprotegido. Na
prática, se `evaluate` passasse `cv_rng` no lugar de `algo_rng` para
`arm.fit`, a suíte inteira continuaria verde e os dois eixos de semente
ficariam entrelaçados sem nenhuma detecção.

Correção: braço-sonda estocástico (`RandomArm`) em `tests/`, cobrindo três
invariantes — reprodutibilidade com as mesmas sementes; `seed_algo`
diferente muda `y_pred` mantendo `test_idx`; `seed_split` diferente muda a
partição.

Verificação por mutação: com `algo_rng` trocado por `cv_rng`, o resultado
foi `1 failed, 5 passed` — falhou exatamente o teste novo, e os dois
`y_pred` saíram idênticos apesar de `seed_algo` diferente. Desfeita a
mutação, `6 passed`. Confirmação empírica de que a suíte anterior era cega
ao bug.

**Pendências abertas** (para o protocolo congelado, semana 11)
- `test_size` está em 25%; o paper de referência usou 20%. Com o Gasoline
  (n=60), 25% deixa só 15 amostras de teste e o R² fica instável.
- A partição não é estratificada por quantil de `y`. Sem isso, uma partição
  azarada pode deixar o teste com faixa estreita do alvo.

**Achados não-críticos da auditoria**

| Achado | Volta em |
|---|---|
| Pré-processador ajustado fora das folds internas — vaza se for entre-amostras | Estágio 1 |
| Folds injetadas mas não auditáveis; braço pode usar CV própria sem detecção | Estágio 2 |
| `n_fits` autodeclarado pelo braço — orçamento é sistema de honra | Estágio 2 |
| `predict` vê `X_test`; `load()` pública permite reconstruir `y_test` | limitação conhecida |
| `PROTOCOLO.md` vazio porém citado como norma no código | semana 11 |
| Variante do Tecator congelada sobre pendência aberta | pergunta nº 5 |

**Próximo**
Estágio 1 — camada de dados e pré-processamento real. Começa em 01/09.