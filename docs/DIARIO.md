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

## 2026-08-27

**Feito**
- Vistoria completa do repositório em sessão nova, sem o histórico de quem
  escreveu o código
- Verificação por mutação do achado crítico refeita de forma independente,
  com o mesmo resultado registrado em 25/08
- Quatro achados novos, nenhum crítico:
  - `docs/ADR/` não existia, embora o README o listasse — resolvido
  - `requirements.txt` gravado em UTF-16 pelo `pip freeze >` do PowerShell;
    o GitHub tratava como binário e não mostrava diff — regravado em UTF-8
  - `assert abs(r2) < 0.2` com limiar arbitrário; funciona hoje por a
    `seed_split=0` ser benigna, mas quebraria sob mudança de `test_size` —
    anotado
  - O histórico git não sustenta a narrativa da auditoria: o commit de
    código já contém o `RandomArm`, então o estado pré-correção nunca
    existiu no repositório e a mutação não é reconstruível a partir do
    histórico
- Três ADRs escritos: 001 folds derivando de `seed_split`, 002 `rmse_cv`
  como propriedade de `FittedArm`, 003 omissão do campo `rmse`
- `docs/` reorganizado: material de estudo movido para `docs/estudo_rodrigo/`
- `CONCEITOS.md` escrito — treino/teste, semente, validação cruzada, como
  material de consulta
- A pedido da orientação, `scripts/run_mean_baseline.py` criado e o
  `MeanArm` rodado no Tecator em 10 `seed_split`

**Resposta da orientação (27/08)** — quatro critérios de avaliação, com
quatro pedidos derivados:

1. Aderência ao protocolo único — verificar se o pré-processamento é
   ajustado só no treino e se `evaluate` não fixa hiperparâmetros que o
   braço deveria escolher. Ambos confirmados no código.
2. Justiça dos braços clássicos — Estágio 2. Mas surge uma decisão de
   arquitetura antecipada: validar CARS e GA-PLS contra valores publicados
   exige reproduzir o protocolo daqueles artigos, que no Tecator costuma
   ser a divisão padrão do conjunto, não partição aleatória repetida.
   Serão necessários dois modos na `evaluate()`: o protocolo único, para a
   decomposição, e um modo "protocolo da literatura", usado exclusivamente
   no portão de validação e nunca na grade.
3. Separação dos eixos — correto, mas falta o teste anti-réplica do
   checklist.
4. Resultados brutos — diagnóstico específico: o R² tem que ser
   ligeiramente negativo, nunca 0,000. Se der zero exato, a média está
   sendo calculada no teste, e isso é vazamento na métrica. O RMSE deve
   ficar próximo do desvio-padrão de `y`.

**Correção conceitual recebida**
A H5 é sobre reprodutibilidade da seleção de bandas, medida por Jaccard,
não sobre variabilidade do erro entre partições. São grandezas diferentes,
e a confusão apareceria no manuscrito.

## 2026-08-28

**Feito** — três das quatro tarefas da orientação:

**Piso de ruído de partição.** Baseline da média rodado no Tecator com 100
`seed_split` (com 10, a estimativa da própria dispersão é instável).
Resultados: RMSEP com média 12,6858 e desvio-padrão 0,9761; R² com média
-0,0291 e desvio-padrão 0,0382; R² negativo em todas as 100 partições,
máximo -0,0000 — o diagnóstico de vazamento na métrica passa. A média do
RMSEP bate com o desvio-padrão da gordura no Tecator (~12,7), como
esperado de um preditor de média. O desvio-padrão do R² (0,0382) é a
âncora empírica da margem δ do TOST, que até aqui não tinha critério
objetivo: nenhum efeito da decomposição menor que esse piso é
interpretável. Pendência: repetir nos outros três conjuntos quando
entrarem — Gasoline é do Estágio 1, e Mango e bioprocesso dependem da
pergunta nº 4.

**Sonda de vazamento com y permutado.** `PermutedYArm` implementado como
decorador de qualquer braço: embaralha `y_train` com `rng_algo`, deixa
`X_train` intacto, delega o resto ao braço interno. Com o alvo permutado
não existe relação X→y, então R² apreciavelmente acima de zero denunciaria
vazamento no caminho de X — o que o baseline da média não detecta, por
nunca tocar em X.

Os resultados saíram idênticos aos do `MeanArm`, o que levantou a suspeita
de a permutação não estar acontecendo. Verificado: era a matemática, não
bug. A média é invariante a permutação, então o `MeanArm` é
estruturalmente cego ao decorador. A prova veio em três partes — um
`SpyArm` capturando o `y_train` entregue (mesma multiset, ordem
diferente); um `FirstYArm` sensível à ordem, cuja saída muda sob
permutação; e verificação por mutação (permutação desativada → os dois
testes novos falham, `2 failed, 7 passed`; revertida → `9 passed`). O
teste antigo continuou verde sob a mutação, corretamente: pela mesma
invariância, ele é cego a esse ponto — os dois novos cobrem o ponto cego.

**Teste anti-réplica.** Item do checklist do pipeline. `_result_key`
deriva um SHA-256 de `test_idx` + `y_pred`. Três testes: chaves distintas
entre 10 `seed_split` para qualquer braço; chaves idênticas ao variar
`seed_algo` em braço determinístico, com o motivo no docstring — exceção
declarada em código, não conhecimento tácito; e chaves distintas ao variar
`seed_algo` no `RandomArm`, para que a exceção não mascare propagação
quebrada em braços estocásticos.

Verificação por mutação: com `evaluate` ignorando `seed_split`,
`2 failed, 10 passed` — o teste novo e o
`test_seed_split_varies_partition_with_fixed_seed_algo`, dupla detecção do
mesmo defeito por mecanismos diferentes. Revertido, `12 passed`.

**Padrão que se repete**: um invariante testado apenas com braço
insensível ao mecanismo é proteção ilusória. Ocorreu no achado crítico de
25/08 e de novo na sonda de permutação.

**Pendente**: a quarta tarefa — dois modos de protocolo na `evaluate()`. É
decisão de arquitetura que muda a assinatura da função e precisa ser
desenhada antes do Estágio 2.

**Próximo**
Estágio 1 em 01/09 — escolher o pré-processamento. A escolha determina se
o contrato muda: SNV é por espectro e não vaza; métodos entre-amostras
vazam para a CV interna com o ajuste na posição atual.

## 2026-09-01

**Reunião de orientação — respostas obtidas**
- Pré-processamento: SNV costuma dar resultados melhores, mas testar os
  dois (SNV e derivada) e escolher empiricamente. Se a combinação SNV
  seguido de derivada for melhor, pode usar. Isso muda o Estágio 1 de
  "escolher um e registrar" para "comparar e decidir com evidência".
- Tarefa D (dois modos de protocolo): desenho aprovado — segunda função em
  arquivo separado, com tipo de retorno distinto, núcleo compartilhado.
- Divisão fixa: usar a mesma divisão do paper (172/43) para todos os
  braços validados contra a literatura.
- Faixa de gordura: sem confirmação, mas suspeita de que o pacote R seja a
  causa. Orientação para investigar.

**Pendente**
A pergunta sobre o pré-processamento do B4 (Z-score do paper versus o
escolhido para os demais braços) não foi feita. Fica para o Estágio 3.

## 2026-09-03

**Investigação da proveniência do Tecator**

`PLSArm` implementado (`src/tcc/arms/pls.py`), cumprindo o contrato `Arm`,
com busca de componentes por CV interna ou `n_components` fixo.

**Tentativa de reproduzir o resultado publicado.** Script
`scripts/validate_against_paper.py` com o protocolo do paper (172/43
sequencial, H=10, Z-score no treino): obtido R² = 0,9604 contra 0,919
publicado, RMSE normalizado 0,2041 contra 0,296. Sensibilidade em 200
partições aleatórias: R² = 0,9491 ± 0,0144, com o valor do paper caindo
no percentil 5. O resultado publicado é alcançável nesta fonte apenas
numa partição atipicamente desfavorável.

**Verificação da coluna de alvo** (`scripts/check_targets.py`): as três
colunas somam 99,03% em média; gordura × água têm correlação -0,9881;
`as_frame=True` nomeia as colunas explicitamente como
`['fat', 'water', 'protein']`. A coluna 0 é gordura de fato.

**Verificação independente no R.** R instalado no WSL (exigiu
`libcurl4-openssl-dev`, `libssl-dev`, `libxml2-dev` para o `RCurl`
compilar). `fda.usc` carregado direto, sem passar pelo Python: Fat
0,90–49,10, Water 39,30–76,60, Protein 11,00–21,80 — idêntico ao que o
`scikit-fda` entrega. A ponte Python→R é fiel.

**Achado sobre a fonte citada no paper.** O manual oficial do pacote R
`pls` lista quatro datasets embutidos — yarn, oliveoil, gasoline e
mayonnaise. Tecator não está entre eles, embora o Data Availability do
paper o cite como fonte.

**Conclusão da investigação.** A divergência não vem de coluna trocada,
nem de transformação na ponte Python→R. O máximo que o paper reporta para
gordura (76) coincide quase exatamente com o máximo da água nesta fonte
(76,6), o que sugere imprecisão na descrição do dataset no paper. Enviado
à orientação com as evidências.

**Próximo**
Estágio 1 — comparar SNV, derivada e a combinação dos dois, usando o
`PLSArm` como avaliador.