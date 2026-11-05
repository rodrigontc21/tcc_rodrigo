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

## 2026-09-15

**Nota de abertura**
~11 dias sem registrar desde a última entrada (03/09), por causa de um
hiato de commits. O que segue é um resumo consolidado desse período, sem
granularidade diária.

**Feito**

**Camada de dados.** Os 4 loaders implementados em `src/tcc/data.py`
(tecator, gasoline, mango, bioprocess), com o alvo selecionado por nome e
hash de proveniência.

**Piso de ruído.** Rodada do `MeanArm` nos 3 conjuntos novos (gasoline,
mango, bioprocess) — o Tecator já havia rodado em 28/08, registrado na
entrada daquele dia. Resultados dos 4 conjuntos em
`results/mean_baseline_*`.

**Teste permanente do diagnóstico de R².**
`test_mean_arm_r2_offset_matches_theory` passa a verificar R² ≈ −1/n_test
para o `MeanArm`, com verificação por mutação.

**Dois modos de protocolo.** Módulo `src/tcc/validation.py` e ADR 005:
separação formal entre `evaluate()`, que serve à grade principal, e
`evaluate_against_literature()`/`scripts/validate_against_paper.py` (split
fixo 172/43 do Tecator, `n_components=10` fixo, sem passar pela busca de
hiperparâmetros). Testes em `tests/test_validation.py`.

**Troca com o orientador via WhatsApp (14/09).** Respondeu aos 6 pontos
sobre o piso de ruído, confirmou `test_size = 0.25` uniforme, apontou que a
seleção de componentes do PLS usava argmin puro em vez da regra de um
erro-padrão, e definiu Glicose como alvo do bioprocess.

**PROTOCOLO.md.** Seção Partição atualizada, registrando a confirmação do
orientador sobre `test_size = 0.25` uniforme.

**Regra de um erro-padrão no PLS.** Implementada em `PLSArm._search`, com
testes e verificação por mutação em `tests/test_pls.py`.

**Pré-processamento revisitado.** Nova rodada de
`scripts/compare_preprocessing_tecator.py` com a regra corrigida: a
conclusão anterior (SNV→derivada vence) se reverteu — agora SNV sozinho
empata ou vence (Δ R² = −0,0009, p = 0,27). Ainda não comunicado ao
orientador; a seção Pré-processamento do `PROTOCOLO.md` segue pendente de
atualização, de propósito, aguardando a resposta dele.

**ADRs de curadoria.** ADR 006 (curadoria do Mango, corte da safra 5) e
ADR 007 (alvo do bioprocess = Glicose), ambos com status proposto. Nenhum
implementado em código, aguardando aprovação do orientador.

**Commit consolidado.** Hoje (15/09), descoberto o hiato de ~2 semanas sem
commit; feito commit consolidado de todo o trabalho acima e push para o
GitHub.

## 2026-09-16

**Verificação independente do ADR 007.** Os números do bioprocess foram
reconferidos direto do cache Arrow do HuggingFace, sem passar pelo loader
do projeto: 6.960 espectros no conjunto bruto (train 4.849 + validation
1.409 + test 702), 488 sem rótulo de glicose, 6.472 restantes, 1.870
canais espectrais e exatamente 8 alvos com os nomes esperados; glicose de
0,0 a 19,99. Todos batem com o ADR e com o pino de `tests/test_data.py`.

**ADRs 006 e 007 enviados à orientação** (15/09, WhatsApp), com o
documento em anexo e não só o resumo, como o orientador havia exigido.
Resposta dele: daria uma olhada no dia seguinte. Continuam com status
proposto.

**Pergunta 6 identificada como o bloqueio real do Estágio 2.** A tabela de
decisões em aberto do `PROTOCOLO.md` aponta a pergunta 6 (linguagem dos
braços clássicos) como bloqueio do Estágio 2, e a `PERGUNTAS.md` não tem
registro de envio dela — está aberta desde 20/08 sem nunca ter sido
perguntada.

**Migração do ambiente para o WSL.** O projeto passou a rodar em Ubuntu
24.04 sob WSL, com venv em `~/venv-tcc`, fora do repositório. Os arquivos
do projeto continuam no sistema de arquivos do Windows, alcançados por um
link simbólico (`~/tcc`), decisão deliberada para não quebrar o acesso
externo aos arquivos. Critério de aceite cumprido: os 56 testes passam no
ambiente novo. Efeitos colaterais resolvidos no caminho: identidade e
credenciais do git reconfiguradas do lado Linux, e o BOM que vinha do
PowerShell deixou de aparecer.

**Ponte com o R validada (spike da pergunta 6).** R atualizado de 4.3.3
para 4.6.1 pelo repositório do CRAN — o do Ubuntu está parado no 4.3.3 e o
`rpy2` 3.6 exige R ≥ 4.5, o que causava erro de símbolo ausente ao
carregar a biblioteca. Instalados `rpy2` 3.6.7 em modo API, `mdatools`
0.16.0 (iPLS) e `plsVarSel` 0.10.0 (CARS, GA-PLS, VIP), com `pls` 2.9-0
como dependência.

**Achado a registrar sobre os pacotes R.** Carregar `mdatools` e
`plsVarSel` juntos causa mascaramento de nomes: `pls::crossval` mascara
`mdatools::crossval` e o `plsVarSel` sobrescreve um método S3 do `pls`.
As chamadas precisam usar namespace explícito, sob pena de a função
executada depender da ordem dos `library()`.

**requirements.txt regenerado** no ambiente Linux: entram `rpy2`,
`rpy2-rinterface` e `rpy2-robjects`; saem `pywinpty` e `win32_setctime`,
que só existem no Windows.

**ADR 008 escrito** propondo os braços clássicos via pacotes R, com VIP em
Python, o `rpy2` isolado atrás da interface `Arm` e as versões registradas
como proveniência. Status proposto, nenhum braço implementado.

**Próximo**
Aguardar a orientação sobre dois pontos já enviados: a reversão do
pré-processamento (SNV vs. SNV→derivada) e a aprovação dos ADRs 006 e
007. Enviar o ADR 008 e, depois, aguardar a aprovação dele. Pendência
interna detectada hoje: a seção "Protocolo da literatura" do
`PROTOCOLO.md` ainda diz "implementação pendente", mas
`src/tcc/validation.py` já implementa `evaluate_against_literature()` —
corrigir quando o protocolo for atualizado.

## 2026-09-17

**ADRs 006 e 007 aceitos pela orientação**, cada um com uma exigência
cumprida antes da aceitação.

**ADR 006 — Mango, safras 1–4.** Exigência: a coluna `Set`
(Cal/Tuning/Val Ext) não pode ser descartada junto com o filtro. Os papers
originais não usam partição aleatória, usam essa divisão, e ela é
necessária no modo "protocolo da literatura" do Estágio 2 (ADR 005).
Resolvido com um campo novo em `Dataset`, `metadata: dict | None` (`None`
nos outros três conjuntos), que `_load_mango()` popula com
`{"Set": ...}`. Implementado: filtro `Season != 5` em `_load_mango()` e
pino `EXPECTED["mango"]` de 12.011 para 11.691 amostras em
`tests/test_data.py`. Novo `sha256` do `Dataset` (cobre X, eixo e DM; a
coluna `Set` não entra no hash), conferido como determinístico em duas
cargas:
`5b829645f407864de6b2a2c90ca2eee7ac0a963baef4aa76d8fca0bbaf8dbb36`.

**ADR 007 — glicose no bioprocess.** Exigência: a distribuição dos 488
espectros sem rótulo de glicose contra qualquer metadado disponível, para
distinguir ausência aleatória de ausência estruturada — esta introduziria
viés de seleção, ao contrário do corte por safra do Mango. O schema do
`bioprocess_substrates` não expõe corrida nem condição experimental, só
as colunas espectrais, os 8 alvos e a partição treino/validação/teste do
cache. A ausência foi cruzada com essa partição (qui-quadrado), com a
ordem das linhas (sequências de ausência, teste de permutação) e com os
outros 7 alvos (Mann-Whitney, correção de Bonferroni).

Conclusão: a ausência não é aleatória pura — EnPump e fosfato total são
significativamente mais altos onde falta a glicose —, mas também não é
um bloco, uma corrida ou um split inteiro. Fica como limitação declarada,
não correção no loader: a faixa de EnPump e fosfato altos fica
sub-representada no conjunto avaliado, e as conclusões para glicose valem
para essa distribuição de condições. Em `_load_bioprocess()`, o
comentário "PROVISÓRIO" deu lugar a um comentário definitivo, citando o
ADR 007 e registrando a limitação.

**Pergunta 4 respondida.** Mango e bioprocess vêm de fontes públicas, com
a curadoria aprovada (ADRs 006 e 007). Sai da fila da `PERGUNTAS.md`.

**Causa raiz da reversão do pré-processamento.** A vantagem do
SNV→derivada na primeira rodada (R² 0,9699 contra 0,9658, p≈0,01) não era
efeito do pré-processamento: era a instabilidade do argmin puro na
seleção do número de componentes do PLS. O teste pareado estava
aritmeticamente correto, mas comparava dois pré-processamentos com o
número de componentes escolhido de forma ruidosa por cima. Corrigido o
seletor (regra de um erro-padrão), o efeito desaparece.

Registrado no `PROTOCOLO.md`: escolha revertida para SNV puro. Com o
seletor corrigido, SNV 0,9689 contra 0,9680 do SNV→derivada (ΔR² =
−0,0009, p=0,27; ΔRMSEP p=0,26) — sem diferença a defender, e a
parcimônia decide: um passo a menos no pré-processamento. A derivada
sozinha fica nitidamente pior (0,9445). O desvio-padrão do R² do SNV
entre partições caiu de 0,0125 para 0,0068 com a regra nova, e o RMSEP
médio também melhorou (2,2159 → 2,1285). A evidência vem só das
`seed_split` 0–29, disjuntas da grade final. A troca do default de
`evaluate()` continua adiada para o início do Estágio 2.

## 2026-09-18

**Eixo do Tecator (adendo ao ADR 004).** A orientação apontou que o
loader do pgsg_1 reconstrói o eixo com `np.linspace(850, 1050, 100)`
(passo de 2,0202 nm), quando o instrumento tem passo de 2 nm exatos de
850 a 1048 nm. Verificação local: o nosso loader não usa `linspace`, mas
herda o mesmo eixo — o `skfda` repassa o `argvals` do `fda.usc`, que já
vem assim. Nem a fonte primária (StatLib) nem o paper definem a posição
dos canais; a faixa 850–1048 nm é indicação da orientação, sem fonte
escrita localizada.

Decisão: o eixo passa a 850–1048 nm em passo de 2 nm. O `sha256`
continua calculado sobre o eixo da fonte, e o loader confere que a fonte
ainda entrega o `linspace` antes de substituí-lo — falha se ela mudar.
Nenhuma métrica muda, porque nenhum braço usa o eixo; muda o comprimento
de onda atribuído a cada canal, em até 2 nm no fim da faixa. A "banda de
931 nm" do paper é o canal 40 (930,81 nm no eixo `linspace`, 930 nm no
novo), então comparações com bandas publicadas se ancoram no índice do
canal, não no valor em nm. Teste:
`test_tecator_axis_is_850_to_1048_in_2nm_steps`.

**Achado: réplicas vazando entre treino e teste (ADR 009).** Revisando a
análise dos 488 espectros sem glicose do ADR 007, apareceu uma estrutura
que o protocolo não tratava: no bioprocess, linhas vizinhas com os 8
alvos idênticos ocorrem muito acima do acaso — várias medições da mesma
amostra física. `evaluate()` sorteava treino, teste e folds espectro a
espectro, então uma réplica podia cair no treino e outra da mesma amostra
no teste: o R² de qualquer braço ficava inflado e o piso de ruído,
subestimado.

Diagnóstico estendido aos 4 conjuntos, comparando alvos idênticos em
linhas vizinhas com pares de linhas sorteados:
- Tecator: 7 pares vizinhos com (fat, water, protein) idênticos, 3,3%
  dos vizinhos contra 0,17% ao acaso; 2 deles com espectro também
  idêntico. Repetições distantes são compatíveis com coincidência (alvos
  com uma casa decimal).
- Gasoline: 1,7% contra 1,2% — sem evidência de réplicas.
- Mango: 48% dos vizinhos repetem o DM, contra 0,02%; repetições
  distantes trazem os mesmos metadados em 738 de 749 casos. Em geral 2
  leituras por fruto, até 6.
- Bioprocess: 5.089 blocos de linhas vizinhas idênticas, mas só 3.433
  composições distintas — a mesma composição reaparece em linhas
  distantes.

**Decisão proposta.** Réplicas da mesma amostra física nunca ficam em
lados diferentes, nem entre treino e teste, nem entre folds da CV
interna. `Dataset` ganha o campo `groups`, preenchido por conjunto na
camada de dados: Tecator por linhas vizinhas com os três alvos idênticos;
Gasoline sem grupos; Mango por DM idêntico com os mesmos metadados;
bioprocess pela composição dos 8 alvos. Algoritmo: cada grupo é
representado por uma linha fixa, a ordem dos grupos vem da posição desse
representante na permutação de `seed_split`, e teste e folds são
preenchidos com grupos inteiros até o tamanho-alvo. Com grupos unitários,
a partição é idêntica à anterior.

**Implementado** em `src/tcc/protocol.py` (partição e folds),
`src/tcc/data.py` (`groups` em cada loader) e `src/tcc/validation.py`
(folds internas do modo literatura; a divisão 172/43 continua fixa, e
nenhum par de réplicas do Tecator atravessa essa fronteira). Testes:
nenhum grupo atravessa treino/teste nos três conjuntos com réplicas,
nenhum grupo atravessa folds, grupos unitários reproduzem a partição
antiga, e ausência de viés por tamanho de grupo. O teste pode passar do
alvo em até o tamanho de um grupo menos um: Tecator 54 a 55, Mango 2.923
a 2.928, bioprocess exato em 1.618.

**Viés de tamanho de grupo, detectado e corrigido.** A primeira versão
ordenava os grupos pela primeira aparição de qualquer membro, o que
favorecia grupos grandes: no Mango, frutos com 6 leituras ocupavam 54% do
teste, contra 32% do conjunto. O teste de teoria do R² detectou o desvio;
a versão final ordena pelo representante fixo.

**Diagnóstico de R² muda de forma.** Para o `MeanArm`, a média do R²
passa a ser ≈ −1/n_ef, com n_ef o tamanho efetivo de Kish do teste, e não
−1/n_test. Com o split antigo, a teoria "por linhas" parecia bater porque
o vazamento correlacionava as médias de treino e teste.

**ADR 007 passa a contar amostras, não espectros.** Como as réplicas não
são independentes, a análise dos 488 foi refeita por amostra: agrupando
réplicas vizinhas, os 6.960 espectros correspondem a 5.089 amostras (um
teto, já que a identificação é aproximada), e os 488 sem glicose, a 355.
Por split: 6,88% (treino), 7,64% (validação), 6,17% (teste), χ²=1,59,
p=0,45. A sequência mais longa sem glicose tem 3 amostras. EnPump quase
dobra nas amostras sem glicose (1,39 contra 0,76) e o fosfato total sobe
de 3,91 para 4,60. Contando espectros, o extrato de levedura aparecia
como significativo (p=0,0017); contando amostras, deixa de ser (p=0,13).

**Números desatualizados.** Os valores do `PROTOCOLO.md` foram calculados
com a partição anterior. Recalculados com a agrupada:
- Piso de ruído (dispersão relativa do RMSEP do `MeanArm`, 100
  `seed_split`): Mango de 0,95% para 1,60%, bioprocess de 0,96% para
  1,25%; Tecator praticamente igual (7,7%); Gasoline não muda. A
  diferença entre conjuntos na seção da margem δ cai de "mais de 10×"
  para cerca de 7×.
- Pré-processamento no Tecator (`seed_split` 0–29): SNV 0,9686,
  SNV→derivada 0,9688, ΔR² = +0,0003, p = 0,76. O empate continua, e o
  SNV puro por parcimônia se mantém.

**Limitação.** A identificação das amostras é aproximada, porque Mango e
bioprocess não expõem identificador. Réplicas não detectadas continuariam
vazando; coincidências agrupadas por engano só tornam a partição mais
conservadora.

**Pendente**
- ADR 009 com status proposto, aguardando aprovação da orientação. O
  código já está implementado.
- Atualizar os números do `PROTOCOLO.md` e regenerar
  `results/mean_baseline_{tecator,mango,bioprocess}.*`,
  `results/permuted_y_tecator.*` e
  `results/preprocessing_comparison_tecator.*`.

## 2026-09-21

**Documentação em dia.** ADR 005 passou de "implementação pendente" para
"implementado (2026-09-14)", com a frase sobre `validate_against_paper.py`
corrigida (segue como checagem pontual, não como implementação temporária).
README com o Estágio 1 marcado. Entradas de 17 e 18/09 deste diário
reconstituídas a partir dos ADRs.

**Sonda de vazamento com um braço que usa X.** `PermutedYArm(PLSArm())` no
Tecator, `seed_split` 0–29, `seed_algo=0`: R² médio −0,0474, dp 0,0849,
máximo +0,1005 (`scripts/run_permuted_y.py --inner pls`). Teste novo,
`test_permuted_y_wrapping_pls_has_no_skill_on_average`, com limiar R² médio
≤ 0, cerca de 3 erros-padrão acima do observado; sem limiar por partição,
porque R² isolados chegam a +0,10 sem vazamento.

Verificação por mutação: um pré-processador ajustado em treino+teste NÃO
fez o teste falhar, nem o antigo com MeanArm. Autoscaling vazado deu
resultado idêntico (o `PLSRegression` já autoescala) e PCA vazada deu R²
médio −0,074. Com y permutado, vazamento só de X não dá habilidade ao
modelo; a sonda só pega y verdadeiro chegando ao braço sem passar pela
permutação. Isso ela pega: com a permutação quebrada, R² médio +0,954 com
PLS (falha) e −0,035 com MeanArm (cego). Limitação registrada no docstring
do teste. Detectar vazamento só de X exige outra sonda, a pensar junto do
teste anti-vazamento da seleção de variáveis no Estágio 2.

**Divisão de literatura do Gasoline (ADR 010, proposto).** O paper só diz
"48/12 train-test split". Investigação: `man/gasoline.Rd` do pacote `pls`
não define divisão; a vinheta usa 50/10 sequencial (`gasoline[1:50,]`); a
Seção 4.2 do paper cita "same data partition (seed 42)". Com o PLS H=5 do
paper e Z-score no treino: sequencial 48/12 dá R² 0,9231; 50/10 dá 0,9139;
`train_test_split(test_size=0.2, random_state=42)` dá R² 0,9752 e RMSE
0,1453, batendo com os 0,975 e 0,145 publicados. Implementado em
`validation.py` (`_literature_split`), com teste de reprodução contra o
valor publicado. Achado lateral: a mesma semente não reproduz o Tecator
(0,9489 contra 0,919), e a sequencial em uso também não (0,9604). Pergunta
9 aberta à orientação.

**Auditoria da semente 42.** `scripts/audit_gasoline_split.py`, com o
próprio portão de `validation.py`. Sementes que reproduzem os dois valores
publicados:

| sementes | em 1e-3 | em 5e-4 (3 casas) |
|---|---|---|
| 200 | 1 (a 42) | 1 (a 42) |
| 2.000 | 6 | 1 (a 42) |
| 20.000 | 34 | 9 |

A unicidade aparente era efeito de amostra pequena. A 42 é típica
(percentis 37 no R² e 60 no RMSE). Taxa de acerto por acaso em 5e-4:
0,045% (Wilson 95%: 0,024%–0,086%). R² e RMSE são parcialmente redundantes
(Pearson −0,50; observado/esperado sob independência ≈ 1,3×). Leitura
registrada no adendo do ADR 010: a 42 não é identificada por unicidade, mas
o paper a nomeia antes de qualquer busca, e a chance de coincidência fica
em torno de 0,045%. A âncora cronológica é o texto do paper
(`docs/fontes/pgsg_0_paper.pdf`, no repositório desde `ff78fe5`, 20/08); a
ordem entre a leitura do "seed 42" e as varreduras, dentro do dia, não tem
registro por commit.

Tolerância do teste de reprodução do Gasoline apertada de 1e-3 para 5e-4,
com verificação por mutação: semente 239 com 1e-3 passa (falso positivo);
com 5e-4 falha no RMSE (0,14443 contra 0,145); restaurada a 42, a suíte
passa.

**Auditoria de fechamento dos Estágios 0 e 1**, rodando a suíte e
verificações pontuais (partição e folds idênticas entre braços,
pré-processador ajustado só em `X_train`, coluna `Set`, alvo `fat` por
nome, sha256). Os critérios do pipeline passam; as lacunas eram de
aprovação e registro: nada commitado, ADR 009 proposto e nunca enviado,
resultados da partição antiga, análise dos 488 sem script, H5 sem resposta,
δ sem valor numérico. O relatório escrito foi descartado depois de usado.

**Piso de ruído com a partição agrupada.** Mango e bioprocess regenerados:
dispersão relativa do RMSEP de 1,60% e 1,25%, batendo com o ADR 009.
`PROTOCOLO.md` atualizado (tabela do piso de ruído, razão entre conjuntos
de cerca de 9,5×).

**Correção de dois números da entrada de 18/09.** A entrada de 18/09,
copiada do ADR 009, registrou dois valores imprecisos. Ela fica como
estava, como registro do que se sabia naquele dia; a correção vai aqui.

- **n_test do bioprocess.** Registrado como "exato em 1.618". Nas 100
  `seed_split` de `results/mean_baseline_bioprocess.csv`, regenerado hoje
  com a partição agrupada, o n_test é 1.618 em 98 partições e 1.620 em 2:
  faixa de 1.618 a 1.620, com alvo 1.618.
- **Razão entre os pisos de ruído.** Registrado que a diferença entre
  conjuntos "cai de 'mais de 10×' para cerca de 7×". A razão real entre o
  maior e o menor piso (dispersão relativa do RMSEP do `MeanArm`) é
  gasoline 11,84% ÷ bioprocess 1,25% = 9,45×. Antes do ADR 009 era cerca
  de 12,5× (11,8% contra 0,95%), então o "mais de 10×" estava certo. O
  "cerca de 7×" corresponde só a gasoline ÷ mango (7,4×). O erro já
  estava nos números do próprio ADR 009 em 18/09, não surgiu com a
  regeneração.

A correção já foi replicada no ADR 009 (faixa 1.618 a 1.620; razão de
cerca de 12,5× para cerca de 9,5×) e no `PROTOCOLO.md`, cuja seção da
margem δ já dizia "cerca de 9,5×" e cuja tabela do piso de ruído já traz
n_test 1.618–1.620 para o bioprocess. No mesmo passe, o `PROTOCOLO.md`
passou a descrever o teste do R² do MeanArm como ≈ −1/n_ef (tamanho
efetivo de Kish), não −1/n_test.

**Correção da entrada de 17/09: o ADR 007 não foi aceito.** A entrada de
17/09 registra "ADRs 006 e 007 aceitos pela orientação". Para o ADR 007
isso está errado: em 17/09 a orientação condicionou a aprovação definitiva
a ver a distribuição dos 488 espectros sem glicose contra qualquer
metadado disponível, e essa resposta nunca foi enviada. A análise existe no
ADR 007, mas foi feita depois, sem que a orientação a tenha visto. A
entrada de 17/09 fica como estava. Pelo mesmo motivo, a frase dela sobre a
pergunta 4 ("curadoria aprovada (ADRs 006 e 007)") vale só para o ADR 006.

Corrigido hoje: o status do ADR 007 passou de "aceito (17/09/2026)" para
"proposto", com o código implementado e a aprovação final pendente. A
análise dos 488 ganhou um script reprodutível,
`scripts/audit_bioprocess_missing_glucose.py`, que reproduz os números do
ADR 007 contando por amostra física (linhas vizinhas com os 8 alvos
idênticos, 5.089 amostras): χ² = 1,59, p = 0,45 por split; sequência mais
longa de 3 amostras sem glicose (permutação, p = 0,80); EnPump e fosfato
total significativos após Bonferroni; extrato de levedura não significativo
por amostra (p = 0,126), significativo por espectro (p = 0,0017). Com os
grupos por composição do ADR 009, a conclusão do Mann-Whitney se mantém,
mas o qui-quadrado por split não se aplica: 1.599 das 3.433 composições
aparecem em mais de um split da fonte. As linhas do `raman_data` vêm na
ordem treino, teste, validação.

**Status do ADR 007 ajustado às palavras da orientação.** Relendo a
mensagem de 17/09, a orientação escreveu "ADR 007 — aprovado, com uma
pendência". O status passou de "proposto" para "aprovado com pendência
(17/09/2026)", com a pendência sendo a confirmação da distribuição dos
488, enviada hoje. A mesma redação foi aplicada ao comentário do
`_load_bioprocess()`, à pergunta 4 e à tabela de decisões do
`PROTOCOLO.md`, que também ganhou a pergunta 9 (Gasoline).

**Resultados do Tecator regenerados com a partição agrupada.**
`results/mean_baseline_tecator.*` (dispersão relativa do RMSEP 7,72%,
n_test 54–55), `results/permuted_y_tecator.*` e
`results/preprocessing_comparison_tecator.*` (SNV 0,9686, SNV→derivada
0,9688, derivada 0,9463; ΔR² = +0,0003, p = 0,76). O empate continua e a
escolha de SNV puro se mantém. O `PROTOCOLO.md` guarda a tabela original
do pré-processamento, que foi a base da decisão, e acrescenta a refeita.
Com isso, todos os arquivos que o ADR 009 listava como desatualizados
estão regenerados.

**Versionamento.** `.gitignore` com exceção para
`results/bioprocess_missing_glucose_audit.*` e `results/testes_estagio1.txt`.
Um `.git/index.lock` órfão de 18/09 travava o `git add` e foi removido.
Commit `2121687` com todo o trabalho desde 17/09, enviado ao GitHub. Suíte:
75 passed, 1 skipped.

**Resposta à orientação (WhatsApp, 21/09).** Enviada a mensagem pendente
desde 17/09: SNV puro como decisão de protocolo (padrão do `evaluate()` a
partir do Estágio 2), ADR 006 aplicado, eixo do Tecator, distribuição dos
488, ADR 009, estudo paralelo, ADR 008 e ADR 010. Anexos: ADRs 006 a 010 e
`PROTOCOLO.md`; resultados por links fixados no commit `2121687`.
Perguntas em aberto:
1. ADR 007: enquadramento dos 488 como limitação e aprovação definitiva.
2. ADR 009: aprovação da partição agrupada.
3. Estudo paralelo de parametrizações: o código existe, e os loaders devem
   se alinhar a ele?
4. Braços clássicos: pacotes R via `rpy2` ou Python.
5. Gasoline: o pgsg_1 confirma `random_state=42`? E a divisão do Tecator
   no paper também era aleatória?

**Limpeza.** Para a Lixeira: a `venv/` antiga do Windows (sem uso desde a
migração para o WSL), os caches (`__pycache__`, `.pytest_cache`,
`.ipynb_checkpoints`), `results/gasoline_split_audit.*`,
`results/permuted_y_pls_tecator.*` e `scripts/check_targets.py`
(diagnóstico temporário da pergunta 5). Cache do pip do Windows apagado
(559 MB). Suíte depois da limpeza: 75 passed, 1 skipped.

**Pendente**
- Commit da remoção do `check_targets.py`.
- Resposta da orientação às 5 perguntas.

**Próximo**
Com a resposta, atualizar os status dos ADRs 007, 009 e 010. O Estágio 1
fecha quando os ADRs 007 e 009 forem aprovados. Depois, Estágio 2: SNV como
padrão do `evaluate()` e braços clássicos, conforme a decisão sobre o ADR
008.

## 2026-09-28

**Registro bruto das conversas com a orientação.** Export do WhatsApp em
`docs/orientacao/` (122 mensagens, 28/07 a 28/09, com os anexos em
`files/` e as imagens em `images/`). Não versionado: entrou no
`.gitignore` no commit `c00dc6e`, porque o repositório é público e a pasta
tem mensagens privadas e anexos de terceiros — entre eles o TCC de outro
aluno, que a orientação enviou em 18/08.

**Lembrete enviado** (WhatsApp, 13:59), sobre a mensagem de 21/09. Sem
resposta até o fim do dia; a última mensagem da orientação continua sendo
a de 17/09, com os pareceres dos ADRs 006 e 007.

**Dois achados que a leitura do export trouxe, e que não estavam
registrados em lugar nenhum do projeto.**

1. *Corrigendum ao paper de referência (mensagem de 03/09).* A razão
   amostras-por-parâmetro da Seção 3.5 do pgsg_0 está errada por um fator
   de mil, de forma consistente: 172/1765 = 0,098, não 97; 48/6882 =
   0,007, não 7; 172/109221 = 0,0016, não 2. A orientação registrou que o
   argumento empírico continua de pé — o CNN pesado falha e a arquitetura
   leve funciona —, mas a justificativa numérica não, e que avalia um
   corrigendum cobrindo isso, a faixa da gordura e a proveniência.
   Orientação explícita para este trabalho: se discutir capacidade do
   modelo, usar parâmetros por amostra, com a conta explícita. Como o B4 é
   o braço do paper, isso é material do manuscrito. Na mesma mensagem, o
   eixo: "vou corrigir no pgsg_1 — não herde".
2. *A pergunta 1 provavelmente nunca foi enviada.* A `PERGUNTAS.md`
   registra "Enviada em: 2026-08-28 (sem resposta direta até o momento)",
   mas o export não tem nenhuma mensagem em 28/08 — a conversa vai de
   27/08 17:50 direto para 03/09 15:45. O que houve em 27/08 foi o tema
   ser levantado e a orientação responder com a correção conceitual da H5
   (Jaccard, não variabilidade do erro); a pergunta específica — reescrever
   a H5 em termos de `seed_split` antes de congelar o protocolo — não
   aparece. Mesma situação para as perguntas 3, 7 e 8, que também não
   estão no export. A 1 é a que trava o congelamento, marcado para a
   semana 11 (~27/10); a 3 trava o Estágio 3 e pode ter tempo de espera
   longo, por depender de terceiros. Se tiverem ido por outro canal, não
   há registro. A `PERGUNTAS.md` não foi alterada: a data de envio fica
   como está até haver confirmação de qual foi o canal.

**Início do Estágio 2 — SNV como padrão do `evaluate()`.** Trocado o
default de `IdentityPreprocessor` para `SNVPreprocessor()` em
`src/tcc/protocol.py`. É a única peça do Estágio 2 já aprovada por escrito
pela orientação (17/09: "Use SNV puro"), e o `PROTOCOLO.md` previa a troca
para o início deste estágio. O `IdentityPreprocessor` fica no código como
o nível "sem pré-processamento".

Efeito medido, e não presumido: **nenhum resultado versionado muda**. O
piso de ruído e a sonda de vazamento versionada rodam com o `MeanArm`, que
ignora X, então SNV não altera métrica alguma neles — `permuted_y_tecator`
foi regenerado e conferido coluna a coluna contra o `HEAD`: idêntico fora
do `wall_time`, e por isso a regeneração foi revertida em vez de
commitada. A comparação de pré-processamento injeta o candidato
explicitamente e também não depende do default.

A sonda com PLS, que usa X, muda: R² médio de −0,0474 para −0,0265 nas
`seed_split` 0–29, dp de 0,0849 para 0,1254, máximo de +0,1005 para
+0,2467. O invariante do teste (R² médio ≤ 0) continua valendo, mas a
margem caiu de ~3 erros-padrão para ~1,2. O teste não fica instável,
porque as sementes são fixas, e sim mais sensível; o docstring de
`test_permuted_y_wrapping_pls_has_no_skill_on_average` passou a registrar
os dois conjuntos de números e a instrução de investigar vazamento antes
de mexer no limiar, que é teórico e não calibrado nos dados.

Suíte depois da troca: 75 passed, 1 skipped.

**Consequência registrada no `PROTOCOLO.md`.** O modo "protocolo da
literatura" não aplica SNV — reproduz o desenho do artigo, que usa só
Z-score. Os dois modos passaram a diferir também no pré-processamento, e
não só na partição; no portão do Estágio 2, uma diferença de RMSEP contra
a literatura não pode ser atribuída ao pré-processamento sem essa
ressalva.

**Braços clássicos: implementação começa sob proposta, não sob
aprovação.** O ADR 008 (iPLS, CARS e GA-PLS via `rpy2`) continua com
status **proposto** — a orientação não se manifestou, e a regra que ela
mesma fixou em 14/09 é "eu aprovo o ADR, não a escolha solta numa
mensagem". A decisão de começar a implementar assim mesmo é minha, e fica
registrada aqui como tal para não virar um "aceito" que ninguém disse. Se
a resposta for Python, os braços em R não se perdem: viram o oráculo
contra o qual a reimplementação é conferida, o que é mais forte do que
validar só contra valor publicado.

**Teste anti-vazamento da seleção — e o contrato que faltava (ADR 011).**
O pipeline manda escrever um teste que falhe se a seleção enxergar a
partição de validação. Com o contrato atual isso era impossível: o braço
honesto e o trapaceiro produzem `Result` idênticos, porque os dois
recebem `X_train` inteiro (o que é correto — as folds servem à CV interna
deles, e o modelo final é legitimamente ajustado em todo o treino) e a
diferença mora em quais linhas cada um usa para escolher bandas *dentro
de cada fold*, que não aparecia em lugar nenhum. Qualquer perturbação
aplicada de fora atinge os dois igualmente, porque as linhas de validação
de um fold são linhas de treino dos outros.

É o mesmo buraco que o ADR 001 registrou e adiou explicitamente para o
Estágio 2. `FittedArm` ganhou `cv_selections` — as bandas escolhidas
dentro de cada fold, na ordem de `cv_folds`, `None` para braços sem
seleção. Mesma convenção do `rmse_cv` (ADR 002) e do `band_scores`: é
propriedade do braço, porque só ele sabe o que fez internamente. Não
entra no `Result` e `evaluate` não o lê — o Estágio 6 exige métricas como
funções puras sobre `results/`, e auditoria de fold é verificação de
contrato, que vive nos testes.

Motivação independente, que apareceu relendo o paper: a Seção 5.2 do
pgsg_0 reporta que "8 das 10 bandas do top-10 apareceram consistentemente
no top-10 das seleções das 5 folds". O B4 tem que reproduzir o modelo
publicado no Estágio 3, e essa afirmação só é reproduzível com a seleção
por fold observável. Ou seja, o campo seria necessário de qualquer forma;
o teste anti-vazamento apenas antecipou.

`tests/test_selection_leakage.py`: o verificador
`assert_selection_is_fold_local` perturba as linhas de validação de cada
fold, injetando correlação espúria numa banda de ruído, e exige que a
seleção daquele fold saia idêntica. As seleções dos outros folds mudam, e
devem mudar. O hiperparâmetro fica fixo durante a verificação — com busca
ativa o candidato escolhido depende de todas as folds, e a perturbação
poderia trocá-lo, mudando a seleção por agregação da CV e não por
vazamento.

Duas sondas provam que o verificador tem dentes: `_HonestSelectorArm`,
que seleciona só com `fold_train`, e `_LeakySelectorArm`, idêntica exceto
por olhar o treino inteiro — o erro que o pipeline chama de mais comum da
literatura. Um teste afirma que o verificador aprova a primeira, outro
que reprova a segunda. Sem o segundo seria mais um invariante testado com
braço insensível ao mecanismo, o padrão de falha de 25/08 e 28/08.

Verificação por mutação: fazendo a sonda honesta selecionar sobre o
treino inteiro, `test_honest_selector_passes_the_check` falha
(`1 failed, 3 passed`); restaurado o arquivo, com hash conferido contra a
cópia anterior, `4 passed`.

**Duas voltas até o teste ficar honesto, e as duas valem registro.** A
primeira versão do fixture usava 2 bandas informativas com k=3: a
terceira vaga era ruído e variava de fold para fold, então o controle
falhava por instabilidade da seleção, não por vazamento. A segunda versão
acrescentou uma terceira banda informativa, e ela saiu com |r| = 0,03
apesar do coeficiente 1,2 — colinearidade amostral entre colunas
"independentes" com n=100, que empurrou uma banda de ruído para o top-3.
As duas falhas eram do desenho do teste, não do verificador, mas as duas
teriam produzido um teste que passa por motivo errado. A versão final
ortogonaliza as colunas por QR, o que torna |r_j| = |coef_j|/||y||
previsível e independente da sorte da semente (~0,80, ~0,52 e ~0,31,
contra ~0,45 que a perturbação alcança e ~0,03 do ruído), e o fixture
agora afirma a própria premissa: se o top-k sobre dados limpos deixar de
ser o conjunto das bandas informativas, ele falha alto, e não de forma
obscura dentro de um teste.

Suíte: 79 passed, 1 skipped.

**Spike da API do mdatools, antes do ADR do iPLS.** Escrever o ADR sem
saber o que o pacote expõe seria adivinhação, então a ordem foi spike
primeiro — mesmo padrão de 16/09, em que a ponte foi validada antes do
ADR 008. Trava declarada antes de rodar: o spike serve para aprender a
API, nunca para escolher configuração olhando desempenho; o número de
intervalos vai à CV interna e a faixa de candidatos é declarada a priori.

Ponte conferida hoje: rpy2 3.6.7, R 4.6.1, mdatools 0.16.0, plsVarSel
0.10.0, pls 2.9.0, biblioteca de usuário em
`~/R/x86_64-pc-linux-gnu-library/4.6`.

Três achados, e o terceiro é o que justifica a ordem:

1. **As folds do protocolo podem ser injetadas.** `mdatools::crossval`
   começa com `if (is.numeric(cv) && length(cv) == nobj) return(...)` —
   um vetor de rótulos de segmento é aceito como está. Como as `cv_folds`
   de `evaluate` formam partição, a conversão é bem definida, e o braço
   usa as folds do protocolo em vez das próprias. Fecha, para o iPLS, o
   risco do ADR 001.
2. **A centragem interna não vaza**: `cv.scope = "local"` é o default,
   com centragem calculada dentro de cada segmento.
3. **O critério de componentes conflita com o protocolo.** O corpo de
   `selectCompNum.pls` tem exatamente dois ramos —
   `switch(selcrit, wold = ..., min = ..., ncomp)`. A regra de um
   erro-padrão não existe no mdatools; ela está no pacote `pls`, em
   `selectNcomp(method = c("randomization", "onesigma"))`. Sem
   tratamento, o A1 escolheria complexidade por um-erro-padrão e o A3 por
   argmin — critério desigual entre braços, e exatamente o que a
   orientação mandou remover em 14/09 ("seu PLS não é o mesmo objeto que
   o PLS do artigo").

**ADR 012 escrito** com esses achados. Decisões: `method = "forward"`;
`int.num ∈ {10, 15, 20, 25, 30}` à CV interna, mesma faixa nos quatro
conjuntos (a largura do intervalo varia com `p`, e isso é deliberado);
folds injetadas; e `glob.ncomp` fixado no valor que a regra de um
erro-padrão do `PLSArm` escolhe sobre o mesmo treino, em vez de usar o
`ncomp.selcrit`. O critério é parâmetro do braço, então o código não fica
bloqueado.

Duas lacunas registradas no próprio ADR, para não passarem por decisão
fundamentada: a faixa de `int.num` **não** foi conferida contra Nørgaard
et al. (2000) — o artigo ainda não foi lido, é parte da revisão dirigida
pendente —, e a ressalva de que fixar `glob.ncomp` pelo ajuste de espectro
completo pode ser generoso demais para um subconjunto pequeno de
intervalos.

**Pergunta 10 aberta à orientação**, em `PERGUNTAS.md` e na tabela de
decisões do `PROTOCOLO.md`: qual critério de componentes o iPLS deve usar.
É metodológica, não de implementação, e cai na classe que a orientação
pediu para levar em ADR.

**Achado que pode atingir o critério de aceitação do Estágio 2.** O
pipeline exige, como item não negociável, "reproduzir valores publicados
de RMSEP para Tecator e Gasoline com iPLS e CARS, dentro da faixa
reportada na literatura". Começando a revisão dirigida pela pergunta que
decide se isso é executável, uma busca preliminar sugere que esses valores
podem não existir:

- **iPLS** (Nørgaard et al., 2000) usa um conjunto NIR de 60 amostras de
  **cerveja**, alvo extrato original, RMSEP 0,17% plato. Não usa Tecator
  nem Gasoline.
- **CARS** (Li et al., 2009) aplica o método a NIR de produtos agrícolas,
  **milho** entre eles. Sem menção a Tecator nem Gasoline.
- Busca por trabalhos de terceiros que apliquem os dois métodos a esses
  conjuntos não retornou nada. Há RMSEP publicado para o Tecator por
  outros métodos, não por esses.

**Natureza da evidência, para não valer mais do que vale:** três buscas na
web, só em resumos, sem acesso aos textos completos. Ausência aí não é
prova de ausência, e a revisão dirigida de verdade — com os artigos em
mãos — pode desmentir. Registrado como suspeita a confirmar, não como
conclusão.

Se confirmado, três saídas: validar a implementação nos conjuntos dos
artigos originais (o de cerveja parece disponível em pacote R, objeto
`beer.ob` do `OHPL`); procurar trabalho de terceiros nesses conjuntos; ou
redefinir o portão. A escolha é da orientação, e virou **pergunta 11** em
`PERGUNTAS.md` e na tabela do `PROTOCOLO.md`.

O motivo de perguntar agora, e não depois: o pipeline dá quatro semanas
aos braços clássicos, e descobrir isso com os três prontos seria o
"descobrir em outubro e refatorar" que a orientação alertou em 27/08.

**`IPLSArm` implementado** (`src/tcc/arms/ipls.py`). O `rpy2` fica inteiro
dentro do módulo, importado sob demanda — quem não usa o braço não precisa
de R. Folds injetadas convertidas em vetor de segmentos, com conferência
de que particionam as linhas em vez de assumir. Seleção **aninhada**: o
`ipls` roda uma vez por fold, só sobre `fold_train`, mais uma vez sobre o
treino inteiro para o ajuste final.

Decisão de desenho que não estava no ADR e passou a estar: o `ipls` é
usado só para **selecionar**; o modelo final é o mesmo `PLSRegression` do
`PLSArm`. Assim A1 e A3 diferem por exatamente uma característica — o
subconjunto de variáveis. Se o mdatools ajustasse o modelo, diferença de
implementação do PLS entraria no termo da decomposição junto com o efeito
da seleção.

Detalhe de `rpy2` que custou uma volta: chamar o `ipls` **dentro** do
contexto do conversor `numpy2ri` faz o retorno vir como `NamedList`, sem
`rx2` nem acesso por nome — o objeto do R chega desmontado. Convertendo só
os argumentos e chamando fora do contexto, volta um `ListVector` e os
campos saem por nome. Está comentado no código para não ser redescoberto.

**O verificador anti-vazamento reprovou o braço na primeira execução — e
estava certo.** Com só o `int_num` fixo, perturbar as linhas de validação
de um fold mudava a seleção daquele fold. A causa não era vazamento: o
`glob_ncomp` era buscado pela regra de um erro-padrão sobre todo o
`X_train`, agregando as folds, e entrava em todas as execuções do iPLS,
inclusive nas de cada fold. É exatamente o falso positivo que o ADR 011
antecipou ao exigir hiperparâmetro fixo. Corrigido tornando `glob_ncomp`
parâmetro do braço; com os dois fixos, passa.

Vale o registro de que o ponto fraco exposto era do **verificador**, não
do braço — e que ele só apareceu no primeiro contato com um braço real,
que era justamente a limitação que eu havia declarado ao escrever o ADR
011.

**Um erro meu no teste, corrigido.** Escrevi primeiro um teste afirmando
que fixar só o `int_num` faz o verificador reprovar. Ele falhou: num
problema sintético pequeno a perturbação não chega a mudar a escolha do
`glob_ncomp`, e o verificador passa. Ou seja, eu tinha transformado um
comportamento dependente dos dados em afirmação universal. O teste passou
a verificar o **mecanismo** — que o valor fixo corta a busca, conferido
pelo orçamento — e não o sintoma.

**Custo medido no Tecator** (`seed_split=0`), que era a dúvida aberta
sobre a seleção aninhada. Tabela **remedida ao fim do dia**, depois das
correções do `n_fits` e do `int.num` executado — os valores da primeira
versão desta entrada estavam com a contagem antiga, e três números
inconsistentes dela foram apontados por vistoria independente:

| braço | R² | RMSEP | n_fits | tempo | × fits | × tempo |
|---|---|---|---|---|---|---|
| A1 `pls_full` | 0,9660 | 2,2605 | 101 | 0,2 s | 1,0 | 1,0 |
| A3 `ipls(int_num=20, glob_ncomp=3)` | 0,9710 | 2,0893 | 2.189 | 4,0 s | 21,7 | 22,3 |
| A3 `ipls(int_num=20)` | 0,9710 | 2,0893 | 2.289 | 3,3 s | 22,7 | 18,1 |
| A3 `ipls` (busca) | 0,9415 | 2,9656 | 9.056 | 14,3 s | 89,7 | 79,1 |

As razões em ajustes e em tempo ficam da mesma ordem em cada linha, que é
o que o `n_fits` existe para permitir aferir. A busca custa cerca de 90×
o PLS de espectro completo — é o preço da seleção aninhada, e é
exatamente o tipo de número que o pipeline quer na tabela de custo.

**Correção das inconsistências apontadas.** A versão anterior desta
entrada dizia "1.757 contra 101" e "6 contra 101" para o mesmo braço,
misturando execuções com `glob_ncomp` fixo e buscado, e citava a razão de
tempo como 25×, 24,6× e 30× em lugares diferentes. Os números acima
substituem todos eles, medidos numa única execução com o código atual.

**Não** extrapolar daqui: o bioprocess tem n=6.472 e p=1.870, e o custo
precisa ser medido lá antes de qualquer promessa sobre a grade. E os R²
são de **uma** partição — não são resultado, são prova de que o
encanamento funciona.

Suíte: 84 passed, 1 skipped (5 testes novos, pulados onde não há R).

**Auditoria adversarial do `IPLSArm`, feita logo depois de ele passar.**
A suíte verde não é evidência de correção — foi o padrão de falha
registrado em 25/08 e 28/08. Procurando erro em vez de confirmação, dois
bugs reais:

**Bug 1 — as folds internas do braço violavam o ADR 009.** O iPLS roda uma
CV própria para pontuar intervalos, e eu a construía fatiando `arange(n)`
em pedaços contíguos, ignorando os grupos de réplica. No Tecator não
apareceu: há só 7 pares de réplicas e nenhum caía na fronteira de fatia.
Num teste com réplicas densas — o padrão do Mango (em geral 2 leituras por
fruto) e do bioprocess (toda amostra com 2+ espectros) — **664 grupos
ficavam partidos**, com a mesma amostra física dos dois lados da CV
interna. Vazamento invisível de fora do braço, e que só não explodiu
porque o primeiro conjunto testado foi o de réplicas mais escassas.

A raiz é do contrato: `Arm.fit` não recebe `dataset.groups`, então o braço
não tem como respeitar a regra por conta própria. A correção evita mexer
no contrato — as folds internas passam a ser os **outros blocos de
validação das folds externas**, reindexados. A garantia é herdada de
`_make_cv_folds`, sem o braço precisar conhecer os grupos. Confirmado: 664
→ 0.

**Bug 2 — o `n_fits` do iPLS era incomparável com o do PLS.** Cada chamada
do `ipls` contava 1 ajuste, quando ela ajusta centenas de modelos por
dentro: 6 ajustes contados para o A3 contra 101 do A1, com o A3 gastando
mais de 20× o tempo. A tabela de custo do manuscrito diria o oposto da
verdade, e o pipeline é explícito quanto ao propósito do campo ("se o
GA-PLS consumir 40× mais ajustes que o MLP, isso precisa aparecer na
tabela"). Passou a ser estimado a partir do que o mdatools reporta —
passadas da busca forward em `int.stat`, intervalos restantes por passada,
segmentos de CV. Declarado como **estimativa**, não contagem exata: o
interior do pacote não é instrumentado.

(A estimativa foi refinada mais tarde no mesmo dia, depois de uma vistoria
independente medir que ela ainda subestimava; os números finais estão na
tabela de custo remedida, adiante nesta entrada.)

Nenhum dos dois mudou o resultado no Tecator (R² 0,9710, RMSEP 2,0893
antes e depois), o que era esperado — o bug 1 não se manifesta nesse
conjunto e o bug 2 só afeta contabilidade.

Dois achados menores, um corrigido e um registrado: o `test_ipls.py`
pulava com `importorskip("rpy2.robjects")`, que não cobre "rpy2 instalado,
`mdatools` ausente" — agora confere o pacote R também. E o braço expõe
`selection` do ajuste final, mas `evaluate()` ainda grava `None` no
`Result`, porque a camada de seleção é o Estágio 4; fica como lacuna
conhecida, não bug.

Os dois bugs ganharam teste de regressão
(`test_inner_folds_never_split_a_replicate_group` e
`test_budget_reflects_the_real_cost_of_the_search`). Suíte: 86 passed,
1 skipped.

**Segunda vistoria do dia, por mutação sistemática.** Seis mutações no
código novo, cada uma devendo fazer algum teste falhar. Três falharam como
esperado (folds internas contíguas, `n_fits` voltando a contar 1, remoção
da checagem de partição). **Três passaram verdes**, e a primeira é grave.

**Achado grave — o teste anti-vazamento do iPLS passava por construção.**
Com o `IPLSArm` selecionando deliberadamente sobre todo o `X_train` — o
vazamento que o Estágio 2 proíbe —, a suíte inteira continuava verde.
Mecanismo: o verificador injetava correlação espúria numa **única banda**,
e o iPLS seleciona **intervalos inteiros**. No fixture (p=40, `int_num=5`,
largura 8) a seleção era sempre o intervalo 1, que contém as bandas
informativas; a banda perturbada caía no intervalo 2 e nunca vencia. A
seleção era invariante à perturbação, vazando ou não. É o mesmo padrão de
25/08 e 28/08 — invariante testado com um braço insensível ao mecanismo —
agora ocorrido no próprio teste escrito para evitá-lo.

Alargar a perturbação para um intervalo inteiro **não** resolveu: uma
perturbação que alcança um terço das linhas não faz um intervalo ruim
superar um bom. A correção mudou a natureza da perturbação — em vez de
promover um perdedor, **destruir o vencedor**. O verificador já calcula a
seleção-base, então agora arruína, só nas linhas de validação daquele
fold, exatamente as bandas que ele havia escolhido. Quem enxerga aquelas
linhas vê como ruidosas as bandas de que mais gostava e troca; quem não as
enxerga não nota. Funciona em qualquer granularidade, e dispensa afinar a
largura por método. Confirmado: a mutação do vazamento agora **falha**.

Acrescentado `_LeakyIPLSArm` e `test_check_catches_ipls_that_sees_the_validation_fold`,
para que o teste do braço real tenha a mesma prova de dentes que as sondas
sintéticas já tinham.

**Achado médio — a decisão de pré-processamento não tinha teste.** Reverter
o default do `evaluate()` de SNV para `Identity` não quebrava nada. Uma
decisão de protocolo aprovada pela orientação podia ser desfeita em
silêncio. Corrigido com `test_evaluate_applies_snv_by_default`, que confere
a assinatura do SNV no que chega ao braço (cada espectro com média 0 e
desvio 1).

**Achado baixo — o contrato do ADR 011 não estava testado.** `cv_selections`
devolvendo `[]` em vez de `None` nos braços sem seleção não quebrava nada,
e a distinção importa para o Estágio 4: `None` é "não se aplica", lista
vazia seria "selecionou nada". Corrigido com
`test_arms_without_selection_report_none`.

**Duas imprecisões de documentação, também corrigidas.**

1. O ADR 012 afirmava que `glob.ncomp` **e** `int.ncomp` eram fixados no
   valor da regra de um erro-padrão. O código nunca fez isso com o
   `int.ncomp`: ele recorta pela largura do intervalo, porque um PLS com
   mais componentes que variáveis é degenerado. A consequência estava sem
   declaração e enfraquece a uniformidade prometida — nos candidatos
   maiores da faixa `int.num`, a complexidade dentro do intervalo fica
   abaixo do valor da regra, enquanto o A1 usa o valor cheio. Agora está
   escrito.
2. O comentário do `n_fits` dizia que cada iteração da busca forward
   ocupa uma linha de `int.stat`. Conferido: a primeira linha é o modelo
   global de espectro completo (`n = 0`, `selected = FALSE`), e
   `nrow = 1 + intervalos selecionados`. A aritmética sobrevive por
   coincidência — a busca que aceita `s` intervalos faz `s + 1` passadas,
   e `nrow` também vale `s + 1` —, mas a justificativa estava errada.
   Registrada a coincidência, porque uma mudança no formato da tabela
   quebraria a estimativa em silêncio.

As três correções de teste foram reconfirmadas por mutação: as três
mutações que passavam verdes agora falham, e os arquivos foram restaurados
com hash conferido. Suíte: 89 passed, 1 skipped.

**Limitação desta vistoria.** Foi feita por quem escreveu o código, no
mesmo dia. O achado grave era o tipo de coisa que um revisor independente
encontraria mais rápido, e não há como saber o que continua invisível pelo
mesmo motivo. Uma vistoria em sessão nova, como a de 27/08, continua
valendo.

**Vistoria independente, em sessão nova sem o histórico de quem escreveu o
código** — o mesmo procedimento de 27/08. Ela achou dez itens, e os dois
mais graves eu reproduzi antes de aceitar. Os dois são erros meus que a
auto-vistoria da tarde não pegou, o que é o argumento a favor de repetir
esse procedimento.

**Erro 1 — o ADR 012 descrevia errado como o mdatools escolhe
complexidade.** Eu havia escrito que o `ncomp.selcrit` "não é usado para
decidir complexidade" e que fixar `glob.ncomp` deixava a regra igual em
todos os braços. Falso. Dentro do `ipls.forward`, cada intervalo candidato
é pontuado com o `ncomp.selcrit`, e o vencedor sai do RMSE calculado com o
número de componentes que aquele critério escolheu **para aquele
intervalo**. O `glob.ncomp` é só teto. Reproduzido no Tecator
(`seed_split` 0, teto 8, 20 intervalos): com `"min"`, componentes 5, 5, 4,
6, 4 e 20 bandas; com `"wold"`, 4, 2, 3, 5, 4, 3, 3 e 30 bandas. O número
varia entre intervalos, e trocar o critério muda a seleção.

A evidência estava à vista desde o spike — a coluna `nComp` do `int.stat`
já mostrava valores diferentes por linha — e eu não li. Com o teto 3 que a
regra de um erro-padrão devolve na `seed_split` 0, o efeito não aparece, o
que explica por que passou.

Consequência séria: a **pergunta 10**, escrita para ir à orientação, estava
sobre premissa falsa. Reescrita.

**Erro 2 — a regra que escolhe `int_num` inverte a parcimônia, e nem estava
declarada.** O código aplica a regra de um erro-padrão e fica com o menor
`int_num`, chamando isso de mais parcimonioso. No PLS a analogia vale —
menos componentes, modelo mais simples. No iPLS não: menos intervalos são
intervalos mais largos, logo **mais** bandas. Medido no Tecator,
`seed_split` 0: `int.num` 10 → 30 bandas, 20 → 10 bandas, 30 → 6 bandas.
No mesmo split o menor erro de CV estava em 25, a regra escolheu 10, e o R²
no teste externo caiu de 0,9710 para 0,9415 — é o "A3 (busca)" da tabela
acima.

**Nada foi alterado no código.** Trocar o critério depois de ver esses
números seria escolher regra olhando resultado, que é o que o pré-registro
proíbe. A regra em vigor ficou declarada no ADR 012 com o defeito exposto,
e a escolha virou **pergunta 12**. Se ela mudar, os números do iPLS no
Tecator registrados acima precisam ser refeitos.

Corrigidos hoje: a seção "Número de componentes" do ADR 012, a regra de
desempate de `int_num` (que passou a estar declarada), as perguntas 10 e
12, e a tabela de decisões do `PROTOCOLO.md`, que estava fora de ordem e
ainda dizia "das nove".

**Os outros oito achados da vistoria, ainda abertos:** a faixa de `int.num`
declarada não é a executada (o mdatools arredonda a largura e recalcula o
número de intervalos); sete mutações passam verdes, entre elas remover a
injeção de `cv` — que reabre o risco do ADR 001 que este ADR diz ter
fechado — e o teste de regressão das folds internas, que chama o helper em
vez do braço; seleção e regressão usam escalonamentos diferentes
(`center=TRUE, scale=FALSE` no mdatools contra o autoescalonamento do
`PLSRegression`); o `n_fits` subestima o custo real em 20 a 26%; números
inconsistentes entre o DIARIO e o ADR (17,4× contra 18,4×, "6 contra 101"
onde a tabela mostra 106, razão de tempo citada como 25×, 24,6× e 30×);
docstrings do verificador que ficaram obsoletos quando a perturbação passou
a ser dirigida; e o fato de o Estágio 2 ter começado sem o critério que o
próprio DIARIO de 21/09 fixou (aprovação dos ADRs 007 e 009).

**As sete lacunas de teste, fechadas.** Cada mutação que a vistoria
reportou como sobrevivente agora faz a suíte falhar, conferido reaplicando
as sete e restaurando com hash. Suíte: 96 passed, 1 skipped;
`tests/test_ipls.py` foi de 8 para 15 testes.

O mecanismo que fecha três delas de uma vez é uma sonda, `_IplsSpy`, que
registra o que de fato atravessa a ponte para o R. A lição: aqueles
invariantes não são observáveis na saída do braço — as bandas selecionadas
continuam plausíveis mesmo com o mdatools usando as próprias folds —, então
testá-los exigia olhar a chamada, não o resultado.

| Mutação que sobrevivia | Teste que a pega agora |
|---|---|
| Remover a injeção de `cv` (reabre o risco do ADR 001) | `test_folds_of_the_protocol_are_injected_into_mdatools` |
| Folds internas contíguas escritas dentro do braço | `test_inner_folds_reaching_r_never_split_a_group` |
| `int.ncomp` sem o recorte pela largura | `test_int_ncomp_is_capped_by_the_interval_width` |
| `n_fits` sem o fator `n_segments` | `test_budget_counts_the_cv_segments` |
| argmin no lugar da regra de um erro-padrão | `test_int_num_uses_the_one_standard_error_rule_not_argmin` |
| Modelo final com a seleção do fold 0 | `test_final_model_uses_the_selection_of_the_whole_training_set` |
| Resultado da busca do `glob_ncomp` ignorado | `test_searched_glob_ncomp_is_the_one_se_value` |

**Duas passaram na primeira tentativa, por defeito do meu teste.** Vale
registrar porque é o mesmo padrão de sempre:

- o teste do orçamento comparava 3 contra 5 folds externas, mas aí muda
  também o **número de chamadas** ao iPLS, e a contagem cresce mesmo sem o
  fator `n_segments`. Refeito direto em `_select_intervals`, com os mesmos
  dados e o mesmo `int_num`, variando só os segmentos;
- o teste do modelo final rodava num fixture em que a seleção do fold 0 era
  **idêntica** à do treino inteiro, então trocar uma pela outra não mudava
  nada. Refeito com um cenário de dois blocos informativos de força
  parecida (coeficientes 1,00 e 0,95), em que as duas divergem, e o teste
  afirma explicitamente que o cenário discrimina antes de verificar o
  invariante.

Os dois testes novos que dependem de cenário discriminante — este e o da
regra de `int_num` — seguem o padrão do `tests/test_pls.py`: afirmam
primeiro que o cenário de fato distingue as alternativas, e só então qual
delas o código aplica. Sem essa primeira asserção, um fixture que deriva
para o caso degenerado transforma o teste em decoração sem ninguém notar.

O teste da regra de `int_num` verifica **qual regra está implementada**,
não que ela seja a certa: a parcimônia invertida continua sendo a
pergunta 12, e se a orientação mudar a regra o teste muda junto.

**Achado 3 — a faixa de `int.num` declarada não é a executada.** O
mdatools converte o número de intervalos em largura, arredonda, e
recalcula quantos cabem em `p`. Medido: Tecator (p=100) 15 → 14 e
30 → 33; Mango (p=306) 25 → 26 e 30 → 31; Gasoline (p=401) 30 → 31. O
`hyperparams` registrava o pedido, descrevendo um experimento que não
aconteceu. Passou a registrar os dois, com `int_num_executed` vindo do
objeto que o pacote devolve. Nada é corrigido à força: fixar o número
exato exigiria passar `int.limits` à mão e substituir a divisão do pacote
pela nossa, o que sai do "usar implementação estabelecida".

Efeito colateral: a estimativa de `n_fits` passou a usar o número
executado — antes contava intervalos que não existiam. E o ADR ganhou uma
correção de passagem: eu afirmava que `int.num = 30` no Tecator dá
intervalos de 3 canais; o pacote reporta 33 intervalos, e os 3 canais são
a conta do braço (`p // int.num`), que é a que alimenta o recorte do
`int.ncomp`. As duas contas agora estão distinguidas.

**Achado 6 — o `n_fits` subestimava o custo real.** A vistoria mediu os
ajustes de verdade com um trace no R e achou 20 a 26% a menos do que a
estimativa. Faltavam o ajuste de calibração de cada avaliação de intervalo
e o modelo global; o ajuste do modelo final também não era contado.
Corrigidos os três. Remedido com trace sobre `mdatools:::pls.cal`:

| cenário | ajustes reais | estimados | razão |
|---|---|---|---|
| p=30, `int_num`=5, 3 segmentos | 56 | 49 | 0,88 |
| p=48, `int_num`=8, 3 segmentos | 92 | 85 | 0,92 |
| p=60, `int_num`=10, 4 segmentos | 145 | 136 | 0,94 |

Continua subestimando de 6 a 12%, e a diferença que sobra não foi
localizada — fechá-la exigiria instrumentar o interior do pacote. O valor
segue declarado como estimativa, e para o uso a que se destina, comparar
ordens de grandeza de orçamento entre braços, 6 a 12% não muda conclusão
nenhuma. Está escrito no código, com os números.

**Achado 5 — seletor e regressor otimizam geometrias diferentes.** O
mdatools pontua os intervalos com `center = TRUE, scale = FALSE`, default
do pacote; o `PLSRegression` do modelo final autoescala, default do
scikit-learn e o que o A1 usa. A vistoria apontou lendo o código e não
mediu o efeito. Medido agora, no Tecator, `int.num = 20`, seis
`seed_split` da faixa exploratória:

| `seed_split` | Jaccard entre as duas seleções | R² (FALSE) | R² (TRUE) |
|---|---|---|---|
| 0 | 0,333 | 0,9710 | 0,9669 |
| 1 | 0,500 | 0,9549 | 0,9526 |
| 2 | 0,750 | 0,9735 | 0,9712 |
| 3 | 1,000 | 0,9722 | 0,9722 |
| 4 | 0,182 | 0,9685 | 0,9651 |
| 5 | 1,000 | 0,9710 | 0,9710 |

**O efeito é desprezível na acurácia e grande na seleção.** As diferenças
de R² ficam na terceira casa, sem vencedor consistente. O Jaccard médio
entre as duas configurações é 0,63 — mais de um terço do conjunto de
bandas muda por causa de uma opção de escalonamento que ninguém declarou.

Isso pesa muito mais aqui do que pesaria em outro trabalho: a **H5 é sobre
reprodutibilidade do conjunto de bandas, medida por Jaccard**. Se um
default de pacote move o Jaccard nessa magnitude, parte do que seria
atribuído ao método é efeito de implementação. Se eu tivesse fechado o
achado como "documentação imprecisa", como ele estava classificado, isso
teria passado.

`scale` virou parâmetro, com o default `FALSE` do pacote preservado, e
nada foi alterado no comportamento. A escolha virou **pergunta 13**.
Descartada de saída a terceira via — desligar o autoescalonamento do PLS
no A3 —, porque aí o A3 deixaria de usar o mesmo regressor do A1 e a
decomposição perderia a propriedade de os braços diferirem por exatamente
uma característica.

**Achados 7, 8 e 9 — o passe de documentação, e os dez estão fechados.**

- **7, números inconsistentes**: a tabela de custo do Tecator foi remedida
  numa única execução com o código atual, e substitui os valores soltos
  que apareciam em pontos diferentes desta entrada ("1.757 contra 101",
  "6 contra 101", razão de tempo como 25×, 24,6× e 30×). Eles vinham de
  execuções distintas — uma com `glob_ncomp` fixo, outra com busca —
  apresentadas como se fossem a mesma medição.
- **8, docstrings obsoletos**: quando a perturbação do verificador passou
  a ser dirigida, os textos que mandavam dimensionar `n_spurious_bands`
  conforme a granularidade do método ficaram falsos — a largura deixou de
  importar. Reescritos, com o histórico das três tentativas preservado,
  porque a sequência (uma banda → intervalo inteiro → destruir o vencedor)
  é o que explica por que o desenho atual é o que é.
- **9, processo**: o `PROTOCOLO.md` tratava o ADR 011 como resolvido
  dentro de uma seção marcada "(decidido)", quando o ADR está `proposto` e
  sem aprovação da orientação. A ressalva de status entrou no lugar.

**Sobre o critério de fechamento do Estágio 1.** A vistoria observou, com
razão, que o DIARIO de 21/09 fixou "o Estágio 1 fecha quando os ADRs 007 e
009 forem aprovados; depois, Estágio 2", e que o trabalho de hoje começou
o Estágio 2 sem isso. Fica registrado como está: os dois ADRs continuam
sem aprovação, a orientação não respondeu desde 17/09, e a decisão de
seguir assim mesmo foi minha. O mesmo vale para o ADR 008, já anotado
acima. Nenhum status de ADR foi alterado por causa disso.

**Erro no ADR 008: o `plsVarSel` não tem CARS.** Preparando a reunião de
amanhã, fui conferir os pacotes no próprio ambiente. O `plsVarSel` 0.10.0
exporta 31 funções e **nenhuma é CARS** — tem `ga_pls`, `VIP`,
`mcuve_pls`, `spa_pls`, `bve_pls`, entre outras. O `mdatools` 0.16.0
também não tem; tem `ipls` e `vipscores`. O ADR 008 afirmava, desde
16/09, que o `plsVarSel` implementava CARS, GA-PLS e VIP. Escrevi sem
verificar, e a pergunta 4 enviada à orientação em 21/09 foi construída
sobre essa premissa.

**Onde o CARS existe de verdade.** Três candidatos: o `carsAlgo`, pacote
no CRAN que se descreve como *"inspired from the work of Li et al.
(2009)"*; o `auswahl`, em Python; e o **`libPLS`**, a biblioteca do grupo
de **Hongdong Li**, primeiro autor do artigo que define o CARS. O libPLS
tem artigo próprio publicado no *Chemometrics and Intelligent Laboratory
Systems*, site oficial em `libpls.net`, e a pasta `R/` do repositório traz
`carspls.r` e `carsplsorigin.r`.

**Decisão tomada, não perguntada: libPLS.** Como "implementação
estabelecida", no sentido em que o pipeline usa a expressão, não há
candidata mais forte que a dos próprios autores do método, publicada e
revisada. As outras duas são reimplementações de terceiros — e o portão
existe justamente para validar a implementação, então referência de
terceiros é o que menos serve ali. A escolha vai ao ADR 008 com a
justificativa escrita, que é como a orientação pediu em 14/09 ("eu aprovo
o ADR, não a escolha solta numa mensagem"), e não como pergunta de
reunião.

**Duas ressalvas registradas no ADR.** O libPLS não é pacote R: são 17
arquivos `.r` soltos, sem `DESCRIPTION` nem `NAMESPACE`, então não há
versão a fixar por gerenciador — a proveniência fica por **commit fixo com
`sha256`**, a mesma disciplina do tarball do `pls` e do CSV do Mango. E a
biblioteca é primariamente MATLAB: o porte em R é secundário, e **não foi
verificado se roda**. Se não rodar, a escolha volta à orientação.

**Correção conceitual de passagem.** O pipeline **nunca menciona R** — nem
`rpy2`, nem pacote nenhum. Ele diz apenas "prefira implementações
estabelecidas a reescrever", e todos os blocos de código dele são Python.
A escolha de linguagem sempre foi inferência do ADR 008, não exigência do
pipeline, e isso não estava escrito. Passou a estar, junto com a
consequência: o critério é **por método**, e nada obriga a uma linguagem
única — o VIP já era Python por esse mesmo raciocínio.

A pergunta 4 (nº 6 da `PERGUNTAS.md`) foi reescrita sobre o mecanismo
correto, e o que ela pergunta encolheu: só o aval para o caminho em R no
iPLS e no GA-PLS, mais a chance de ele objetar ao libPLS.

**Próximo**
Medir o custo do `IPLSArm` nos outros três conjuntos, sobretudo no
bioprocess (n=6.472, p=1.870), antes de seguir para o CARS. Se a seleção
aninhada não couber lá, isso é resultado e vira decisão de protocolo.

## 2026-09-29

**A orientação cedeu o código do paper.** O repositório
`prior-guided-spectral-gating-main` foi disponibilizado em 29/09, e está em
`docs/fontes/prior-guided-spectral-gating-main/` — **fora do
versionamento**, no `.gitignore`, porque é material de terceiros e traz
manuscritos de revisão ainda não publicados (`revision_r2`,
`revision_talanta`), além dos CSVs de espectros. O repositório deste
trabalho é público.

### A divisão treino/teste, respondida na fonte

`src/data/preprocessing.py`, `preprocessing_fixed.py` e
`preprocessing_multi.py` — os três fazem:

```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
```

Aleatória com semente 42, **nos dois conjuntos**. Isso:

- **confirma o ADR 010**, cuja divisão do Gasoline era inferência pelos
  números e agora tem fonte no código;
- **derruba a divisão do Tecator em uso**. O modo "protocolo da
  literatura" usa 172/43 sequencial, aprovado em 01/09 (ADR 005). O paper
  não usou sequencial.

Protocolo completo reproduzido, com os dados e o código deles — Z-score de
X e y ajustado no treino, `PLSRegression` do sklearn, H = 10 e H = 5:

| conjunto | obtido | publicado |
|---|---|---|
| Tecator | R² 0,9191 / RMSE 0,2957 | 0,919 / 0,296 |
| Gasoline | R² 0,9752 / RMSE 0,1453 | 0,975 / 0,145 |

Quatro métricas, terceira casa decimal.

### Achado grave: o alvo do Tecator no paper é água, não gordura

Em `data/raw/tecator/targets.csv` daquele repositório, o cabeçalho não
corresponde ao conteúdo:

| coluna rotulada | faixa real | o que é de fato |
|---|---|---|
| **Fat** | 39,30 – 76,60 | **água** |
| **Water** | 0,90 – 49,10, média 18,14 | **gordura** |
| Protein | 11,00 – 21,80 | proteína |

As faixas canônicas estão fixadas no ADR 004, conferidas em Python e em R,
e confirmadas pela orientação em 03/09. A coluna "Water" daquele arquivo é
idêntica, linha a linha, ao `y` que o nosso loader carrega do `skfda` — e
o `X` dos dois é idêntico também.

Todos os scripts do repositório selecionam `y_train[:, 0]`, a coluna
rotulada "Fat" — `baseline_pls.py` (com o comentário `# Fat normalizado`),
os de treino do modelo, e o `one_se_analysis.py` da rodada de revisão.

Rodando o protocolo deles nas três colunas:

| coluna | conteúdo real | R² | RMSE |
|---|---|---|---|
| 0 "Fat" | água | **0,9191** | **0,2957** |
| 1 "Water" | gordura | 0,9489 | 0,2365 |
| 2 "Protein" | proteína | 0,9182 | 0,3088 |

Só a coluna 0 bate nas duas métricas. (A proteína bate no R² por
coincidência; o RMSE separa.) E o 0,9489 da gordura é exatamente o número
que já tínhamos medido em 21/09 ao testar a semente 42 no Tecator —
achávamos que era desacordo com o paper, e era o valor correto da gordura.

**O que fecha a identificação:** `revision_r1/one_se_output.txt`, saída da
rodada de revisão (manuscrito CHEMOLAB-D-26-00658R1, Revisor #2), registra
`H_min = 14`, `RMSECV = 0,2093`, `SE = 0,0269`, `H* = 10` e
`H = 10 (paper): R2 = 0.9191  RMSE = 0.2957`. A Seção 4.2 do artigo
publicado traz exatamente esses números. O script que gerou esse arquivo
declara na linha 9: *"baseline_pls.py-compatível (y_train[:, 0],
PLSRegression default)"*.

Três evidências independentes, portanto: a aritmética das faixas, o código
que seleciona a coluna, e o arquivo de saída da revisão que reproduz o
texto publicado.

**O que permanece sem explicação.** Em 03/09 a orientação inspecionou o
loader em `revision_pgsg_0_r1` e reportou que o CSV do OpenML nomeia as
colunas moisture, fat, protein, e que o `y` bruto tinha min 0,9, max 49,1,
média 18,14 — a faixa da gordura. Isso é verdade sobre o arquivo que ela
olhou. Em algum ponto entre aquele download e este `targets.csv`, as
colunas foram gravadas numa ordem e o cabeçalho escrito noutra. Quem
resolve essa parte é a orientação; o achado não depende dela.

**Por que passou despercebido.** Gordura e água têm correlação −0,988 no
Tecator, então prever uma ou outra dá desempenho parecido. Nada quebra,
nada dá erro, e o resultado parece bom. É exatamente o mecanismo que a
orientação descreveu em 03/09 ao levantar a hipótese de coluna trocada —
hipótese que ela descartou conferindo o cabeçalho de um CSV diferente. Neste
arquivo, conferir o cabeçalho era justamente a checagem que não funcionava.

**Relação com o corrigendum.** Em 03/09 a orientação disse avaliar um
corrigendum cobrindo a razão amostras-por-parâmetro, **a faixa da gordura**
e a proveniência, com a conclusão de que "nenhum resultado do artigo está
comprometido". Se o achado se confirmar, a premissa se inverte: a faixa
"7% a 76%" não é erro de prosa — 76,6 é o máximo da coluna que foi de fato
usada. Corrigir apenas a prosa tornaria o texto internamente consistente e
apagaria a única pista visível da troca.

**Verificação reproduzível:** `scripts/verificar_alvo.py` imprime as quatro
checagens. Escrito em 29/09 para levar à orientação. Depende do repositório
da orientação em `docs/fontes/`, que não é versionado.

### Consequências para este trabalho, a decidir com a orientação

- **ADR 005 e 010**: a divisão de literatura do Tecator deixa de ser
  172/43 sequencial e passa a ser a aleatória com semente 42. O ADR 010
  ganha fonte no código para o Gasoline.
- **ADR 004**: a conclusão "nenhum resultado do paper está comprometido"
  precisa ser revisitada.
- **Portão do Estágio 2**: reproduzir o número publicado do Tecator passa a
  significar prever água.
- **Estágio 3**: o braço B4 deve reproduzir o modelo publicado — que foi
  treinado em água.

Nada foi alterado no código ou nos ADRs por causa disso. O achado vai à
orientação primeiro.

### A orientação aceitou o achado, no mesmo dia

Achado levado por mensagem em 29/09, com a saída da verificação. Resposta
no mesmo dia, ainda em 29/09. O registro bruto está em `docs/orientacao/`,
fora do versionamento.

**Ela conferiu outro artefato em 03/09.** Nas palavras dela: abriu o loader
do `pgsg_1`, que lê o CSV do OpenML com cabeçalho `moisture, fat, protein`
e seleção em `-2`; ali o alvo é gordura de fato, e o 0,9 / 49,1 / 18,14 que
reportou estava correto **para aquele arquivo**. Mas aquele não é o código
que gerou o artigo — o `targets.csv` do `prior-guided-spectral-gating-main`
é o código-fonte declarado na publicação. São artefatos diferentes, e ela
conferiu o errado. Isso fecha o que a entrada acima deixou como "permanece
sem explicação".

**O mecanismo, identificado por ela.** O `targets.csv` tem conteúdo na ordem
do StatLib/OpenML (umidade, gordura, proteína) com cabeçalho escrito na
ordem do `skfda` (Fat, Water, Protein). A troca aconteceu **na exportação
do CSV, não no carregamento** — por isso nenhum teste de carregamento
pegaria.

**Ela aceita a conclusão.** Quatro números na precisão reportada não
coincidem por acaso; a leitura mais direta é que os resultados do Tecator
no artigo publicado foram calculados sobre umidade, não gordura.

**O escopo mudou, na avaliação dela.** Deixa de ser corrigendum de prosa:
Tabela 1, Seção 4.2, Fig. 2 e Fig. 3 na parte do Tecator passam a reportar
um alvo diferente do declarado. E atinge a Seção 5.2, o argumento central
de interpretabilidade — a banda de 931 nm é atribuída ao estiramento C–H da
gordura, mas com ρ = −0,988 ela apareceria de qualquer forma. O argumento
que ela usou em setembro a favor ("o resultado não distingue os alvos")
corta ao contrário: a banda não valida a escolha do alvo, e a frase que
atribui a seleção à gordura foi escrita sobre um modelo que previa água.
Palavra dela: precisa ser **reformulado**, não corrigido. O Gasoline não é
afetado; o método também não, e o PLS com gordura real dá 0,9489, o que
alarga a distância para o PGSG.

**Três verificações pedidas**, nessa ordem e com prioridade sobre o resto:

1. Confirmar que o `targets.csv` é mesmo o insumo das rodadas publicadas —
   data de modificação, histórico do git daquele repositório, e qual script
   o gerou a partir de qual fonte. Se houver script de exportação, ele
   mostra a troca literalmente.
2. Conferir a identidade da coluna 0 contra a água do `fda.usc` elemento a
   elemento, não só por mínimo e máximo, e confirmar o alinhamento das 215
   linhas entre `targets.csv` e a matriz X.
3. Rodar o pipeline completo com a coluna correta — PGSG inclusive, não só
   o PLS — para medir a extensão do que muda.

### Decisão da orientação: o portão do Estágio 2 muda de âncora

Palavra dela: o portão de validação do Estágio 2 previa comparação contra
os valores publicados do Tecator, e **esses valores estão suspensos até a
verificação fechar**. A âncora passa a ser a própria reexecução do protocolo
do artigo com o alvo correto, e isso deve ser registrado em ADR.

E a ordem de prioridade: **os ADRs 006 e 007 podem esperar; as verificações
vêm primeiro.**

Nada foi alterado ainda. O ADR da nova âncora sai depois das verificações,
que é quando se sabe o que ele deve fixar.

### Verificação 1, fechada: o `targets.csv` é o insumo das rodadas publicadas

Rodada em 29/09. O script é `scripts/verificar_origem_targets.py`.

**O zip não respondia.** Todos os arquivos com data 29/09 09:44, que é a
extração; a pasta enviada não tem `.git`. Os dois primeiros itens do pedido
eram impossíveis com aquele material.

**O repositório público resolveu.** O manuscrito declara o código em
`github.com/clarimar/prior-guided-spectral-gating`, e o link está acessível.
Clonado em `~/pgsg-github`, fora deste repositório, com
`--filter=blob:none --no-checkout`. São 18 commits, de 23/05/2026 a
09/09/2026.

- `data/raw/tecator/targets.csv` e `spectra.csv` entraram no **commit
  inicial** (`42c0b30`, 23/05/2026 10:01) e **nunca foram alterados**.
  Atravessaram intactos as três rodadas de revisão — R1 em julho, R2 em
  agosto, Talanta em setembro.
- Os dois arquivos do GitHub são **byte a byte idênticos** aos do zip,
  conferido por `sha256` do blob contra o arquivo
  (`targets.csv`: `3115d049…`, `spectra.csv`: `cc8b2b09…`).
- **Nenhum script de exportação foi apagado** em toda a história do
  repositório; as únicas exclusões são intermediários de LaTeX, em agosto.

Com a reprodução dos quatro números, isso fecha a pergunta: o arquivo é o
insumo das rodadas publicadas, e não um artefato gerado depois.

**A fonte declarada não existe.** Os dois scripts de download
(`src/data/download.py`, `src/data/download_old.py`) e o
`scripts/download_tecator.R` chamam `data(meatspec, package="pls")`. O
pacote `pls` não tem esse conjunto — só `gasoline`, `mayonnaise`,
`oliveoil` e `yarn`, conferido no R desta máquina —, e nenhum pacote
instalado aqui o tem. Esses scripts caem no `except` e não poderiam ter
gerado os arquivos. O `spectra.csv` confirma por outro lado: tem cabeçalho
`850nm, 852nm, ...`, enquanto aquele código grava `pd.DataFrame(X)`, que
daria `0, 1, 2, ...`.

**A fonte de fato é o `skfda` ou o `fda.usc`, indistinguíveis pelos dados.**
O `spectra.csv` é idêntico linha a linha ao X de `fetch_tecator()` — e
também ao `tecator$absorp` do `fda.usc`, porque **o X das duas bibliotecas é
idêntico entre si** (conferido em 29/09). Logo o X bater com o skfda não
identifica qual das duas foi usada; identifica apenas que não foi o
`meatspec`. O `targets.csv` é o mesmo `y`, com as colunas 0 e 1 **trocadas**
em relação à ordem das duas bibliotecas:

| no `targets.csv` | conteúdo | posição na biblioteca |
|---|---|---|
| 0, rotulada `Fat` | água | 1, `water` |
| 1, rotulada `Water` | gordura | 0, `fat` |
| 2, rotulada `Protein` | proteína | 2, `protein` |

**O que identifica o modo de geração:** o cabeçalho do `spectra.csv` é
`850nm, 852nm, ..., 1047nm, 1050nm`. Os `argvals` das duas bibliotecas são
`850,0 / 852,0202 / 854,0404 / ... / 1047,9798 / 1050,0` — o
`linspace(850, 1050, 100)` registrado no adendo do ADR 004. O cabeçalho é
esse eixo **truncado para inteiro**: 1047,9798 virou `1047nm`, não 1048. Um
CSV do StatLib ou do OpenML não traria esses valores quebrados para truncar.
O arquivo foi, portanto, gerado por código a partir de uma dessas duas
bibliotecas.

É o mecanismo que a orientação descreveu. O que muda é a origem: uma das
duas bibliotecas, não o CSV do OpenML.

**O script que fez a troca não está no repositório e nunca esteve.** Não há
menção a `skfda` ou `scikit-fda` em lugar nenhum, nem no `requirements.txt`,
que lista `rpy2` com o comentário "R integration (for Tecator download)".

**Achado lateral:** a declaração de disponibilidade de dados do manuscrito
(`revision_r1/manuscript_R2.tex`, linha 538) afirma que os dois conjuntos
vêm do pacote R `pls`. O Tecator não vem.

### Verificação 2, fechada: a coluna é a água, e as linhas estão alinhadas

Rodada em 29/09. O script é `scripts/verificar_alinhamento_tecator.py`. O
`fda.usc` não estava instalado nesta máquina — o ADR 004 registra o uso dele
em 03/09, mas a instalação não persistiu —, e foi instalado agora.

**Identidade elemento a elemento, nas 215 linhas, contra o `tecator$y` do
`fda.usc`:**

| coluna do `targets.csv` | casa com | linhas iguais | maior diferença |
|---|---|---|---|
| 0, `Fat` | `Water` | 215/215 | 0,00e+00 |
| 1, `Water` | `Fat` | 215/215 | 0,00e+00 |
| 2, `Protein` | `Protein` | 215/215 | 0,00e+00 |

Diferença exatamente zero. Não é semelhança de faixa: são os mesmos valores.

**As linhas não foram embaralhadas.** O `spectra.csv` é idêntico ao
`tecator$absorp` linha a linha, e o `targets.csv` bate com o `tecator$y` sem
reordenar linhas. A linha *i* do espectro corresponde à linha *i* do alvo. O
erro está só na ordem das **colunas** de `y`, o que limita o estrago e torna
a correção mecânica.

**Duas fontes independentes concordam.** O `y` do `fda.usc` (R) e o do
`scikit-fda` (Python) têm o mesmo conteúdo. A identificação das colunas não
depende da biblioteca.

**Sobre qual lado foi alterado.** As colunas do `tecator$y` no `fda.usc` se
chamam `Fat, Water, Protein`, na mesma ordem em que o cabeçalho do
`targets.csv` foi gravado — e é também a ordem do `skfda`. O conteúdo, por
outro lado, está em água, gordura, proteína. Qual dos dois lados foi
mexido não se decide pelos arquivos: sem o script, "cabeçalho correto sobre
conteúdo permutado" e "conteúdo numa ordem de origem com cabeçalho escrito
de outra" explicam igualmente o resultado. A evidência do eixo truncado
(verificação 1) favorece a primeira leitura, já que o gerador leu de uma
biblioteca cuja ordem é gordura, água, proteína — mas isso é inferência, não
prova. O efeito é o mesmo, e é o que a orientação descreveu.

**Em aberto, para olhar depois — réplicas no Tecator.** A checagem de
unicidade feita de passagem mostrou **22 espectros repetidos linha a linha**
no Tecator, e a mesma contagem aparece na fonte (`fda.usc`), então não é
artefato do CSV. Conferido um par: as linhas 185 e 214 têm X idêntico e y
idêntico — são réplicas da mesma amostra física. O ADR 009 deste trabalho é
justamente sobre partição agrupada por amostra física; se essas réplicas
existem e o Tecator é particionado aleatoriamente, há vazamento entre treino
e teste. Nada foi alterado; fica registrado para avaliação.

**Próximo**
Verificação 3: rodar o pipeline completo com a coluna correta, PGSG
inclusive, para medir a extensão do que muda. Depois o ADR da nova âncora do
portão do Estágio 2, e a medição do custo do `IPLSArm` nos outros três
conjuntos.

## 2026-09-30

Dia da verificação 3, de duas auditorias independentes sobre as três
verificações, e das correções que elas produziram. O material para a
orientação ficou em `results/`, e a decisão que ela pediu virou o ADR 013.

### Verificação 3, fechada: a extensão do que muda com o alvo correto

Script: `scripts/verificar_pipeline_tecator.py`. Reimplementa o pipeline do
artigo — não roda os scripts deles — importando os modelos e refazendo o
protocolo de `preprocessing_fixed.py`, `train_light.py`, `train_with_vip.py`,
`train_with_rf.py`, `train_random.py`, `cross_validate.py` e
`train_proper.py`. Conferido linha a linha contra os originais; as contagens
de parâmetros batem com o manuscrito nos três modelos (1.765, 6.882,
109.221), o que fixa o mapeamento. O `torch` foi instalado no `~/venv-tcc`
para isto (2.14.1+cpu).

**Tabela 1 do Tecator**, mediana e faixa entre 10 réplicas — o pipeline
original não fixa semente em lugar nenhum:

| linha | publicado | col 0 = água | col 1 = gordura |
|---|---|---|---|
| PLS | 0,919 | 0,919 | **0,946** |
| PLS, 5-fold | 0,921 | 0,922 | 0,955 |
| Ours (ANOVA), teste único | 0,941 | 0,922 [0,80;0,96] | 0,922 [0,84;0,94] |
| Ours (ANOVA), 5-fold | 0,862 | 0,869 [0,82;0,89] | 0,868 [0,68;0,89] |
| Ours (VIP) | 0,903 | 0,909 | 0,930 |
| Ours (RF) | 0,938 | 0,933 | 0,937 |
| Random init | 0,871 | 0,888 | 0,912 |
| Plain CNN | 0,235 | −0,019 [−2,59;0,21] | 0,005 [−0,53;0,17] |

A coluna 0 reproduz o publicado — PLS 0,919/0,296 no teste único e 0,922 em
5-fold contra os 0,921 do manuscrito. É o protocolo do artigo, não uma
aproximação.

**O H do PLS teve de ser refeito.** `manuscript_R2.tex:386` determina
"Reported PLS results use H* throughout", com H* pela regra de um erro-padrão
sobre LOO. O H=10 é o H* **da água**. Para a gordura a regra dá **H\*=12** e
R² **0,946** — e não 0,9489, que é o valor com H=10 e foi o número citado pela
orientação na mensagem de 29/09. A implementação se valida contra
`revision_r1/one_se_output.txt`: reproduz H_min=14, RMSECV 0,2093, SE 0,0269,
H\*=10 na coluna 0.

**A distância entre PGSG e PLS**, comparando 5-fold com 5-fold, que é o
número justo e está no próprio manuscrito (linha 388):

| | PLS 5-fold | PGSG 5-fold | lacuna |
|---|---|---|---|
| água | 0,922 | 0,869 | 5,7% |
| gordura | 0,955 | 0,868 | 9,1% |

Cresce cerca de 60%, **não dobra**. O mecanismo: o PGSG vai de 0,869 para
0,868 (Wilcoxon pareado p=0,846; Mann-Whitney p=0,910) — trocar o alvo não o
move. Quem muda é o PLS, determinístico, de 0,919 para 0,946. O aumento da
lacuna vem inteiramente do PLS.

**O prior ANOVA contra a inicialização aleatória**, por Mann-Whitney:

| coluna | ANOVA | aleatório | diferença | p |
|---|---|---|---|---|
| 0, água | 0,922 | 0,888 | +0,033 | **0,021** |
| 1, gordura | 0,922 | 0,912 | +0,010 | 0,307 |

Na coluna publicada a vantagem existe; na gordura, some no ruído. Com a
ressalva de que os dois braços usam critérios de parada diferentes.

**Nenhum número desta tabela é medida limpa de desempenho.** Os braços de
teste único param observando o próprio conjunto de teste e ficam com o modelo
da última época; o 5-fold tem o mesmo problema contra a fold de validação, e
além disso usa um prior calculado sobre os 172 do treino, que contêm as folds
de validação. O protocolo foi reproduzido como está, de propósito.

### Entregas em `results/`

Três relatórios em Markdown, gerados por
`scripts/gerar_relatorio_verificacao.py`, cada um com o enunciado do pedido,
a resposta em prosa e a saída bruta como anexo. A orientação lê documento,
não terminal.

- `verificacao_1_procedencia_do_targets.md`
- `verificacao_2_alinhamento_do_tecator.md`
- `verificacao_3_pipeline_com_o_alvo_correto.md`

### ADR 013 — a âncora do portão do Estágio 2

Escrito, status **proposto**. Fixa o protocolo da âncora (partição semente
42, Z-score de X e y, H\* por LOO+1SE refeito por coluna, alvo por nome) e os
valores de referência com a gordura. Mantém a coluna da água como controle.
Registra a ressalva das réplicas.

### Duas auditorias independentes, e o que elas derrubaram

Duas sessões separadas auditaram as três verificações. Tudo que segue foi
**conferido rodando** antes de entrar aqui.

**Erros meus, corrigidos:**

- O H do PLS estava fixo em 10 para as duas colunas (acima).
- A lacuna usava média e desvio entre réplicas. Duas réplicas colapsam na
  gordura — sementes 5 e 7, uma fold cai para ~0 em cada. Passou a mediana e
  faixa, e o script agora lista as réplicas anômalas.
- A lacuna comparava PGSG em 5-fold contra PLS em teste único. O número justo
  está no manuscrito e passou a ser usado.
- O teste ANOVA × aleatório era Wilcoxon pareado por semente. Não vale:
  semente igual não emparelha nada entre os dois braços, porque as camadas
  seguintes partem de pesos diferentes. Passou a Mann-Whitney.
- O script gravava `__pycache__` dentro da árvore da orientação, contra a
  promessa do próprio cabeçalho. Removido, e `sys.dont_write_bytecode = True`
  antes do primeiro import.
- O cabeçalho dizia que só as linhas de teste único eram otimistas; o 5-fold
  também é.

**Afirmações minhas que caíram:**

- "as 20 maiores do Gasoline vão de 150 a 261, não contíguas" — **19 das 20
  são exatamente as bandas 150–168**. O texto publicado erra por uma banda; eu
  exagerei a discrepância.
- "9 das 10 maiores aparecem em todas as folds, não 8" — veio de uma semente.
  Nas dez: 9, 8, 7, 8, 9, 10, 9, 10, 10, 8. O 8 publicado aparece em três.
- "a ablação de bandas não reproduz" — cai pela metade. Com a leitura
  "retreinar sem as bandas" dá 0,28–0,72 e 0,83–0,87, perto dos 0,431 e 0,794
  publicados. Eu havia testado só a leitura "zerar a entrada no teste".
  Os números definitivos são os do relatório da Seção 5.2, medidos no
  script em dez sementes e nas duas variantes do retreino (ver "Revisão do
  relatório da Seção 5.2", adiante).

### Correções à entrada de 29/09

Não reescrevo a entrada anterior; as correções ficam aqui.

- **"Duas fontes independentes concordam" está errado.** O
  `skfda.datasets.fetch_tecator` chama `_fetch_fda_usc("tecator")`: lê do
  próprio `fda.usc`. Conferir os dois mostra que o resultado não depende do
  caminho de leitura, e nada além. Fonte de fato independente seria o OpenML
  505. O resultado da verificação 2 não muda.
- **"A fonte declarada não existe" é forte demais.** O `meatspec` existe no
  pacote R `faraway`, onde traz só a gordura e não as três colunas. O certo é
  "não existe no pacote declarado".
- **A data original existe.** O `overleaf_submission.zip` preserva a data de
  cada entrada: as figuras da submissão são de **21/05/2026 17:45**, dois dias
  antes do commit inicial do GitHub (23/05). Logo o git **não cobre** o
  período em que os resultados foram gerados. "É o insumo das rodadas
  publicadas" continua valendo, mas pela reprodução numérica exata, não pelo
  histórico.
- **Onde o script de exportação pode estar:** `src/data/download.py:73`,
  `README_1.md` e `setup_project.py` apontam para
  `~/Dropbox/chemometric-band-selection/`, o projeto anterior. "Nunca esteve"
  vale só para o repositório do GitHub.

### A Seção 5.2 reporta a inicialização

**Correção de escopo, feita ainda em 30/09.** Eu havia classificado isto como
"achado não pedido" e deixado fora dos relatórios. Errado: a mensagem da
orientação enumera o que o achado atinge — "a Tabela 1, a Seção 4.2, a Fig. 2
e a Fig. 3... **E atinge a Seção 5.2**, que é o argumento central de
interpretabilidade... precisa ser reformulado, não só corrigido" — e em
seguida pede o pipeline completo "para saber a extensão do que muda". A
Seção 5.2 está dentro do pedido, e é a parte que ela mais destacou.

Medido em `scripts/verificar_secao52_pgsg.py`.

As gates de um modelo **sem um único passo de treino** reproduzem os valores
publicados, nos dois conjuntos:

| | sem treinar | treinado | publicado |
|---|---|---|---|
| Tecator, banda topo | 931 nm | 931 nm | 931 nm |
| Tecator, peso | 0,215 | 0,219 | 0,215 |
| Tecator, corr. com o prior | **0,348** | 0,335 | **0,348** |
| Tecator, região C–H | 7,389% | 7,213% | 7,4% |
| Tecator, região O–H | 3,536% | 3,535% | 3,5% |
| Gasoline, banda topo | 154 | 154 | 154 |
| Gasoline, peso | **0,130** | 0,107 | **0,130** |
| Gasoline, corr. com o prior | **0,507** | 0,495 | **0,507** |

O `analyze_gates.py` cria um modelo novo e lê as gates; não há `torch.load`
ali, e nenhum script do pipeline do Tecator chama `torch.save`. A Fig. 1
publicada, extraída do `overleaf_submission.zip`, coincide com a
inicialização ponto a ponto, inclusive no vale de 862 nm.

Isso falsifica a frase da legenda (linha 473): "The moderate correlation with
the ANOVA prior (r=0.35) **confirms genuine data-driven refinement rather
than mere reproduction of initialization**".

**E há um mecanismo, que explica o pico.** O prior é normalizado min-max,
então o máximo vale **exatamente 1**, e o `clip(1 − 1e-7)` o manda para logit
16,12. A banda vizinha, com prior 0,9905 — 1% menos —, fica em 4,65:

| banda | prior | logit | gate |
|---|---|---|---|
| 40 | 1,000000 | 16,12 | 0,2148 |
| 39 | 0,990542 | 4,65 | 0,0217 |
| 41 | 0,975696 | 3,69 | 0,0179 |

Gate dez vezes maior por 1% de diferença no prior. O "dramatic sharpening of
the peak at 931 nm" (linha 481), apresentado como aprendizado, é consequência
mecânica de `(p−min)/(max−min)` → `clip` → `logit`. O mesmo mecanismo produz
o vale em 862 nm, onde o prior mínimo vira −16,12.

Consequência: a banda campeã começa **11,5 logits** à frente da segunda,
enquanto o deslocamento **medido** de cada logit em 200 épocas fica entre
1,47 e 1,93. (O passo do Adam é da ordem do *learning rate*, o que dá ~2,0
em 200 passos, mas isso é uma referência, não um teto rígido — o que
sustenta a conclusão é a medida.) **O topo não tem como mudar.** As posições
de baixo, onde os logits estão próximos, reordenam — o que explica a
estabilidade entre folds sem que ela seja evidência de aprendizado.

**Duas afirmações do manuscrito que não fecham com o próprio material:**

- linha 388 publica PLS 5-fold `0,921 ± 0,018`; o `one_se_output.txt` do autor
  registra `0,9218 ± 0,0439` nas mesmas folds. A média bate, o desvio não.
- linha 390 afirma semente fixa 42 e variação "<0,02 in R²". Nenhum script do
  pipeline do Tecator chama `torch.manual_seed`, e o ANOVA em teste único
  varia de 0,80 a 0,96 nas dez réplicas.

**Onde mais a afirmação aparece:** `submission_package/highlights.txt`,
`cover_letter.txt`, `paper_complete.txt` e `revision_r2/pgsg_1_R2.tex:358`.

Nada disto foi enviado. Está em `docs/PENDENCIAS.md`, bloco C, para a
orientação decidir quando e como.

### Achado sobre ESTE trabalho: as réplicas do Tecator e o ADR 009

O mais sério do dia, e não é sobre o artigo.

```
pares de espectros IDENTICOS no Tecator : 22
pares que o ADR 009 põe no MESMO grupo  :  2
pares que ele SEPARA                    : 20
```

O ADR 009 agrupa réplicas do Tecator por vizinhança de linha. Vinte dos 22
pares idênticos estão em linhas distantes, caem em grupos diferentes, e podem
cair em lados opostos da partição no `evaluate()`. **Isso atinge todo número
do Tecator deste projeto** — piso de ruído, comparação de pré-processamento,
iPLS.

A premissa escrita no ADR 009, de que repetições distantes "são compatíveis
com coincidência", é falsa: são espectros de 100 canais idênticos bit a bit.

No artigo, 7 desses pares atravessam a partição publicada. O efeito medido
sobre o PLS é pequeno — a gordura vai de 0,946 para 0,943 — e não foi medido
sobre os demais braços.

**Nada foi alterado.** O status do ADR 009 segue a palavra da orientação, e o
achado vai a ela primeiro.

### `docs/PENDENCIAS.md`

Arquivo de trabalho, temporário, separado em: o que é deste trabalho (A),
correções nos scripts (B) e material sobre o artigo (C). No fim do dia, B1 a
B4 estão aplicados, o bloco C entrou no relatório da Seção 5.2, e só o A1
segue aberto. O que for resolvido sai de lá e entra na entrada do DIARIO do
dia.

### Revisão do relatório da Seção 5.2

Uma terceira leitura, depois de o relatório `verificacao_3b_secao_5_2.md`
ficar pronto, achou nele duas afirmações que não se sustentavam, e uma
lacuna no relatório 3:

- **"A mediana entre sementes é 8, o valor publicado é o típico."** Com cinco
  sementes (`9, 8, 7, 8, 9`) a mediana é 8; com dez, da mesma sequência
  (`9, 8, 7, 8, 9, 10, 9, 10, 10, 8`), é 9. O número dependia de quantas se
  rodavam. O script passou a dez sementes, e o relatório agora diz o que a
  medida sustenta: o valor vai de 7 a 10, e o 8 publicado aparece em 3 das
  10 — possível, não típico.
- **O retreino da ablação mantinha o prior sem dizer.** Com o prior mantido,
  a porta continua pondo ~21% do peso na banda 931, zerada, e o treino não
  redistribui. É uma escolha que move o resultado, e ela não estava
  declarada. Agora as duas variantes são medidas, com os mesmos sorteios:
  mesmo prior 0,35 [0,18; 0,53], prior zerado 0,63 [0,28; 0,72], contra
  0,431 publicado. O publicado cai dentro da faixa de ambas.
- **A coluna "depois de treinar" era de uma semente.** Refeita em dez: o
  treinado nunca chega aos valores publicados (Tecator, correlação 0,332 a
  0,340 contra 0,348; Gasoline, peso 0,102 a 0,110 contra 0,130, correlação
  0,487 a 0,500 contra 0,507).
- **O relatório 3 não apontava para o 3b.** Quem lesse só o primeiro
  concluiria que "o PGSG praticamente não muda" sem saber que as portas
  publicadas são a inicialização. Ganhou uma remissão na resposta curta.

Os dois relatórios foram regenerados pelo `gerar_relatorio_verificacao.py`.

### Quarta auditoria, refazendo cada afirmação por outro caminho

Sessão nova, com a instrução de não confiar nos scripts que geraram os
relatórios: cada afirmação refeita por caminho diferente — R puro para a
verificação 2, PLS e portas reimplementados do zero em numpy/sklearn, o
código do artigo lido de novo, e o texto conferido contra o **PDF
publicado**, não só contra o `manuscript_R2.tex`.

**Confirmado:** histórico e `sha256` do repositório público (e ele não
mudou desde o clone); identidade das colunas em R (`identical()`); PLS
inteiro (H\* 10 e 12, 0,9191/0,2957, 0,9462/0,2428, 5-fold 0,922 e 0,955);
as portas da inicialização nos dois conjuntos; a fidelidade da
reimplementação do PGSG, receita por receita; o A1 contra os grupos do
loader. Os quatro scripts rodados de novo deram saída idêntica aos anexos.
Tudo o que os relatórios citam do manuscrito está também no PDF publicado.
Fato novo: os 22 pares de espectros idênticos do Tecator têm também o `y`
idêntico — são réplicas, não coincidência.

**Corrigido nos relatórios:**

- Relatório 3 dizia que a Plain CNN publicada caía "na cauda" da dispersão.
  Está **fora** da faixa das 10 réplicas, em R² (0,235 contra [−2,59; 0,21])
  e em RMSE (0,909 contra [0,93; 1,97]).
- Relatório 3b dizia que a Fig. 1 "coincide com a inicialização ponto a
  ponto". Nunca foi medido; a olho são iguais, mas a curva treinada também
  seria. Deixou de ser usada como evidência.
- Relatório 3b citava o deslocamento dos logits "entre 1,47 e 1,93": eram a
  semente 0 de cada coluna, apresentadas como faixa. Em 10 sementes: 1,45 a
  1,92 no Tecator, 1,22 a 1,79 no Gasoline. A conclusão se mantém.
- Relatório 1 afirmava, sem conferir, que o `meatspec` do `faraway` só tem a
  gordura. Conferido no `faraway` 1.0.9 do CRAN, lendo o arquivo de dados
  sem instalar o pacote (a instalação exige CMake para uma dependência):
  215 × 101, colunas `V1`–`V100` e `fat`.
- Relatório 3 citava só o Wilcoxon pareado. Passou a citar os dois testes,
  com a justificativa do pareamento — que aqui é legítimo, ao contrário do
  que o item B3 do `PENDENCIAS.md` sugeria.

### Varredura de treino: o que reproduz as portas publicadas

A formulação que eu vinha usando dizia que treino muito curto, ou com lr
cem vezes menor, reproduz o publicado. Isso nunca tinha sido medido em
script. Medido agora em `scripts/verificar_varredura_treino.py`, com
desenho e critério fixados no cabeçalho antes de rodar: 10 sementes,
"reproduz" = peso da maior porta **e** correlação com o prior iguais ao
publicado na terceira casa.

- Sem treino: 10 de 10 nos dois conjuntos.
- 1 a 5 épocas: 1 a 3 de 10 no Tecator, 0 a 1 de 10 no Gasoline.
- lr 1e-4 no protocolo do artigo: 4 de 10 no Tecator, **0 de 10** no
  Gasoline (peso 0,129 contra 0,130).
- Protocolo declarado, e qualquer KL de 0 a 10: 0 de 10 nos dois.

**A formulação caiu pela metade.** Treino curto ou com lr baixo deixa as
portas a 0,001–0,002 do publicado — praticamente iguais à inicialização —,
mas não as reproduz de forma consistente; só a inicialização reproduz em
todas as sementes. O KL não aproxima em nenhum valor. O relatório 3b passou
a dizer "correspondem à inicialização", com a tabela da varredura e a
saída dela como segundo anexo.

### Adendos datados, sem reescrever

O achado de 29/09 desmentia três registros que seguiam como estavam: o ADR
004 (aceito) dizia "dados do OpenML" e "nenhum resultado do paper está
comprometido"; a pergunta 5 do `PERGUNTAS.md` e a linha 5 da tabela do
`PROTOCOLO.md` diziam "erro de prosa". Os três ganharam adendo de 30/09. A
decisão do ADR 004 para este trabalho não muda, e o status também não. A
redação pode mudar quando a orientação responder.

O ADR 013 passou a dizer como os 7 pares foram tirados no cálculo do
0,946 → 0,943: dos dois jeitos dá o mesmo (0,9426 tirando do teste, 0,9428
tirando do treino).

### A fonte independente: OpenML 505

A verificação 2 só tinha o `fda.usc` (o skfda lê dele). Refeita contra o
OpenML 505 em `scripts/verificar_openml_tecator.py`, que entrou no
relatório 2 como segundo anexo. O OpenML tem 240 amostras; as 215 do
`spectra.csv` são as 215 primeiras, na mesma ordem, com espectro idêntico. A
coluna rotulada `Fat` é a `moisture` do OpenML, 215/215 com diferença zero;
`Water` é `fat`; `Protein` é `protein`. Duas rotulagens independentes, a
mesma resposta — com a ressalva de que as duas distribuições descendem do
mesmo arquivo do StatLib.

O script errou na primeira execução, e a trava que eu tinha posto o parou:
o teste de ordem buscava, para cada linha, "a linha mais parecida" do
OpenML, e os 22 espectros repetidos fazem essa busca devolver a primeira
ocorrência. Era defeito do teste, não dos dados — a diferença posição a
posição já dava zero. Passou a comparar posição com posição.

### Releitura do pedido: o que faltava no "pipeline completo"

Relendo a mensagem de 29/09 frase por frase, e o artigo inteiro atrás de
todo resultado do Tecator, apareceram dois lugares que os relatórios não
cobriam:

- **O resumo e a conclusão** repetem o argumento da Seção 5.2 ("*the moderate
  correlation ... (0.35–0.51) confirms ... rather than merely reproducing
  initialization*"). O relatório 3b só listava highlights, carta e textos
  de fora do artigo.
- **A Seção 3.4** (`manuscript_R2.tex:267`) afirma uma busca em grade do
  peso do KL no Tecator: λ ≥ 0,01 "colapsa para o prior" (r > 0,85) e
  λ ≤ 1e-4 fica "indistinguível da inicialização aleatória". Não há script
  dela no repositório. Refeita em `scripts/verificar_kl_secao34.py`, com a
  grade e o protocolo do texto, 50 treinos por λ: a correlação fica entre
  0,331 e 0,351 em todos os λ, nenhum treino passa de 0,85, e com λ = 1e-4
  as portas seguem agrupadas em 0,337, enquanto as da inicialização
  aleatória vão de 0,17 a 0,50. Nenhuma das três afirmações se reproduz.

Leitura de código, registrada como tal: o texto trata o prior como
distribuição de probabilidade, mas o `band_select_net_light.py` usa os
escores min-max sem normalizar a soma — o termo minimizado não é a KL da
equação.

Os dois entraram no relatório 3b, com o script como terceiro anexo.

**Decisão minha, hoje:** a mensagem à orientação responde só ao que ela
pediu em 29/09. O A1 — as réplicas do Tecator neste trabalho — fica para
depois, numa mensagem própria.

**Próximo**
Enviar à orientação os quatro relatórios de `results/` e o ADR 013. Levar
junto o item A1 — as réplicas do Tecator —, que é o que trava o Estágio 2
deste trabalho. Depois, medir o custo do `IPLSArm` nos outros três
conjuntos.

## 2026-10-21

Entrada de retomada, depois de 20 dias sem registro. Cobre o que aconteceu
em 30/09 à noite e em 01/10, reconstituído do export do WhatsApp atualizado
hoje (`docs/orientacao/`, agora com a pasta `files/`), e o que ficou parado
desde então.

### O envio de 30/09

Enviados à orientação às 22:26 de 30/09: os quatro relatórios de `results/`
e o ADR 013, com uma mensagem que resumia cada verificação e levava duas
perguntas — se o H\* deve ser refeito por coluna, e se o script que gerou o
`targets.csv` está no Dropbox do projeto anterior. O A1 ficou de fora, como
decidido em 30/09. Conferido por `sha256`: os arquivos que estão no disco são
idênticos aos que foram enviados.

Correção à entrada de 30/09: o "Próximo" de lá dizia para levar o A1 junto.
Isso foi revisto no mesmo dia, na seção "Releitura do pedido", e o A1 não
foi.

### O parecer da orientação (01/10, 10:39)

Documento `.docx`, guardado em `docs/fontes/` e fora do versionamento
(`.gitignore`), porque é avaliação privada do artigo dela. Em resumo, nas
palavras do documento:

- "O conjunto das quatro verificações é melhor do que o que foi pedido."
  Trata os achados como estabelecidos, e não como hipótese.
- O alvo trocado: a Tabela 1, a Seção 4.2 e as Figs. 2 e 3 passam a
  reportar água; a lacuna para o PLS vai de 5,7% para 9,1%, e o H\* da
  gordura é 12.
- A Seção 5.2 "é de outra ordem": os oito valores da Tabela 2 são
  reproduzidos pela inicialização, e a Seção 3.4 também não se reproduz.
- "O mecanismo é o achado científico real": a cadeia min-max → clip →
  logit torna a porta campeã imóvel por construção. Propõe correções:
  escalar os logits, não recortar no extremo, ou usar a temperatura.
- **Nova direção do TCC:** a hipótese passa a ser que o termo
  Δ_aprendizado é nulo por construção. Três mudanças de desenho: desdobrar
  o braço B4 em "inicialização pura, sem nenhum passo de treino" e "PGSG
  treinado com o protocolo declarado"; acrescentar um braço com a
  inicialização corrigida; e reinterpretar a H5 (Jaccard) no protocolo
  pré-registrado antes de rodar a grade.
- **ADR 013:** "A âncora do PLS está correta e aprovada." Falta um
  parágrafo sobre o braço B4, com o desdobramento acima. "Com essa adição,
  o ADR pode passar a aceito." O status segue **proposto** até a adição.

**Não respondido até hoje.** Há uma dúvida a levar junto da resposta: o
pipeline já tem um braço com porta fixa, o B2 (`mlp_weighted`, "ponderação
fixa pelo prior, sem gradiente na porta"). Não está claro se a
"inicialização pura" do parecer é o B2 com a porta congelada no valor
inicial do PGSG, ou um braço novo. A escolha decide o parágrafo do B4.

### A reprodução independente da orientação (01/10, 18:05)

A orientação refez a reprodução no código do repositório dela.

**Bate exatamente nos dois:** coluna 0 = água; PLS 0,9191 / 0,2957;
RMSECV 0,2093 ± 0,0269 com H\* = 10; gordura com H\* = 12, 0,9462 /
0,2428; as portas não treinadas reproduzindo os oito valores; Gasoline com
H\* = 5, 0,9752 / 0,1453. Também a correlação treinada do Tecator e o
deslocamento máximo dos logits.

**Diverge nos braços de rede:**

| braço | este trabalho | orientação |
|---|---|---|
| Plain CNN, gordura | 0,005 [−0,53; 0,17] | 0,410 [−0,02; 0,80] |
| PGSG 5-fold, gordura | 0,868 | 0,859 |
| PGSG ANOVA teste único, água | 0,922 | 0,932 |

**Dois erros meus, apontados por ela e procedentes:**

- O relatório 3b dizia que o protocolo declarado não reproduz "nenhum"
  dos oito valores. Medido valor a valor, em 10 sementes, na precisão
  publicada: a banda do topo (10/10 nos dois conjuntos), o peso do Tecator
  (3/10) e o O–H (5/10) são compatíveis; a correlação do Tecator, o C–H e
  o peso e a correlação do Gasoline são excluídos (0/10). São quatro
  compatíveis e quatro excluídos. O erro veio de generalizar o critério da
  varredura, que olhava só peso e correlação juntos, e de uma tolerância
  frouxa no C–H (7,21% marcado "ok" contra 7,4%).
- O relatório 3 passou a dizer, em 30/09, que o 0,235 da Plain CNN fica
  fora da faixa. Com 50 sementes ele fica dentro, no percentil 96. A
  "correção" de 30/09 foi conclusão de 10 sementes — a armadilha de sempre.

**Três achados dela, a incorporar:** o `compute_priors.py` mapeia `'Fat'`
para a coluna 0, então o próprio prior ANOVA foi calculado sobre a água; o
± 0,018 da Seção 4.2 não corresponde a nenhuma dispersão (ela obtém 0,0439
com ddof=0 e 0,0491 com ddof=1, os mesmos que eu havia medido na auditoria
de 30/09, mais 0,022 de erro-padrão); e as Figs. 2 e 3 usam constantes
consistentes com a Tabela 1 publicada.

Ela pediu dois scripts e quatro conferências: semeadura, forma do `y` na
perda, qual modelo é a Plain CNN, e contra qual conjunto a paciência
observa. As quatro foram conferidas no código e estão iguais às dela:
`torch.manual_seed(s)` antes de instanciar, `y` em 1-D, `BandSelectNet`
com porta e prior (o mesmo do `create_model`), e paciência no teste para o
teste único e na fold para o 5-fold.

### Investigação da divergência, em 01/10

Medido em scripts de rascunho, fora do repositório. **O código desses
rascunhos se perdeu** (pasta temporária da sessão); os números abaixo
ficam como registro e precisam ser refeitos em `scripts/` antes de entrar
em qualquer relatório.

- **Sensibilidade às sementes, 50 sementes, medianas por bloco de 10:**
  ANOVA teste único na água, 0,921 a 0,924; PGSG 5-fold na gordura, em 30
  sementes, 0,868 a 0,876; Plain CNN na gordura, −0,001 a 0,071, com
  máximo de 0,17 em 50 sementes. As duas primeiras diferenças são pequenas,
  mas ficam fora da variação entre blocos; a da Plain CNN é incompatível —
  não é semente.
- **Variações da Plain CNN na gordura, 10 sementes:** 100 épocas, sem
  parada, paciência 30, weight decay 1e-4, receita do modelo leve,
  lr 0,001, prior da água, `y` sem padronizar (o `preprocessing.py`, versão
  sem "fixed", não padroniza o `y`) e guardar a melhor época. Nenhuma
  chegou perto de 0,41; a mais próxima foi guardar a melhor época, com
  mediana 0,161.

Sem o script dela, não dá para saber de que lado está a diferença.

### Os scripts enviados (01/10, 18:52)

Enviados `scripts/verificar_pipeline_tecator.py` e
`scripts/verificar_varredura_treino.py`, com instruções de uso, a
admissão dos dois erros e o pedido do script dela. Antes do envio, os
dois tiveram as docstrings e os comentários encurtados e os marcadores
`# noqa` removidos. Nenhuma linha de cálculo nem de saída mudou: rodados
depois da limpeza, a saída saiu idêntica, linha a linha, aos anexos dos
relatórios.

Resposta dela às 19:03: "Obrigado". **Nada mais até hoje** — nem o script
dela, nem resposta à divergência.

### Estado em 21/10

- Os relatórios **ainda não foram corrigidos** (os dois erros acima e os
  três achados dela). Foram segurados para corrigir tudo de uma vez depois
  da comparação com o script dela.
- O parecer não foi respondido, e o ADR 013 segue proposto.
- Nada commitado desde `895e1f8`; o `main` local está 3 commits à frente do
  `origin`, e nada foi enviado ao GitHub.
- O congelamento do protocolo estava marcado para a semana 11, por volta de
  27/10 (DIARIO de 25/08 e 28/09). O parecer exige que a reinterpretação da
  H5 entre no protocolo antes da grade, e a pergunta 1, que trava o
  congelamento, provavelmente nunca foi enviada.

### Os testes de 01/10, refeitos em script

Os três testes que tinham ficado só em rascunho agora estão em
`scripts/verificar_divergencia_redes.py`, que usa as funções do
`verificar_pipeline_tecator.py` para não haver diferença de protocolo. Os
números saíram **idênticos** aos de 01/10, em todas as linhas: os oito
valores (4 compatíveis, 4 excluídos), as medianas por bloco de sementes e
as dez variações da Plain CNN, com a mais próxima, guardar a melhor época,
ainda em mediana 0,161 contra os 0,410 da orientação. Levou 4,5 minutos.
Suíte: 97 passed, 1 skipped.

### ADR 013: o parágrafo do B4

O parecer não pergunta, determina; por isso o parágrafo foi escrito sem
consulta prévia, com a leitura adotada declarada no próprio ADR, para a
orientação corrigir se discordar. Seção nova, "O braço B4":

- o B4 se desdobra em **porta na inicialização** (porta fixa em
  `softmax(logit(clip(s))/τ)`, sem gradiente, resto da rede treinado) e
  **PGSG treinado** (protocolo declarado);
- "sem nenhum passo de treino" é lido como a **porta** sem treino, porque
  uma rede inteira sem treino não prevê;
- com essa leitura, a porta na inicialização é o **B2** do pipeline, desde
  que a ponderação fixa do B2 seja a porta inicial e não o prior bruto — e
  não são a mesma coisa: no Tecator a porta inicial põe 21,5% do peso na
  maior banda, o prior bruto normalizado põe 2,4% (medido hoje). O ADR fixa
  a primeira, e `Δ_aprendizado = B4 − B2` passa a medir a hipótese do
  parecer;
- "reproduzir o modelo publicado" passa a ser feito por partes: as portas
  publicadas contra a porta na inicialização, os R² publicados contra o PGSG
  treinado, como faixa.

Status: segue **proposto** até a orientação ler a adição.

**Próximo**
Pôr a nova direção do parecer no `PROTOCOLO.md`, antes do congelamento.
Depois, mandar o ADR 013 à orientação, com a pergunta sobre o prazo de
congelamento e um lembrete sobre o script dela.
Depois corrigir os relatórios — os dois erros e os três achados dela —, com
o novo script como anexo, de preferência já com a comparação contra o
script dela.

## 2026-10-27

**A orientação escreveu hoje** ("Rodrigo, tudo bem?", 10:31), a primeira
mensagem desde 01/10. Hoje é também a data em que o `PROTOCOLO.md` marcava
o congelamento (semana 11). As semanas desde 01/10 foram tomadas pelo
período de eleição no trabalho, no TRE.

### Relatórios corrigidos, como prometido à orientação em 01/10

- **Relatório 3b:** "o protocolo declarado não reproduz nenhum dos oito
  valores" passou a "quatro compatíveis, quatro excluídos", com a tabela
  valor a valor em 10 sementes. A causa do erro estava também no script: o
  `verificar_secao52_pgsg.py` comparava com tolerâncias frouxas (0,3 ponto
  no C–H, 0,005 no peso) e marcava "ok" o C–H treinado de 7,21% contra
  7,4%. Passou a comparar na precisão publicada — arredonda o medido para
  as mesmas casas do artigo —, o mesmo critério da orientação.
- **Relatório 3:** a Plain CNN voltou a "na cauda": o 0,235 publicado fica
  no percentil 96 em 50 sementes. A "correção" de 30/09 ("fora da faixa")
  vinha de 10 sementes. Entraram os dois achados da orientação — o prior
  ANOVA, VIP e RF também calculado sobre a água, e o ± 0,018 que não
  corresponde a nenhuma dispersão — e uma seção sobre a divergência com a
  reprodução dela, com o `verificar_divergencia_redes.py` como segundo
  anexo. A divergência segue em aberto, à espera do script dela.

**Correção à entrada de 21/10:** ali está "as dez variações da Plain CNN".
São nove variações mais a receita original, e o peso do KL não foi variado
sozinho — faz parte da "receita do modelo leve".

### A nova direção no protocolo, como proposta

A proposta (`docs/fontes/tcc_rodrigo.pdf`) só pôde ser lida hoje: o
extrator improvisado embaralhava a fonte do arquivo. Instalado o `pypdf`
6.21.3 no `~/venv-tcc`, só como ferramenta de leitura, fora do
`requirements.txt`. Lidas as hipóteses H1–H7, duas coisas que eu supunha
estavam erradas:

- **Não existe hipótese para o Δ_aprendizado.** O H4 é outro termo
  (Δ_vs-clássico: a porta contra a melhor seleção clássica). A hipótese do
  parecer é, portanto, nova — entrou como **H8**.
- **A H5 é "a hipótese positiva do trabalho"**, nas palavras da proposta, e é
  justamente a que o parecer manda reinterpretar. A H6 (B4 contra B3 em
  reprodutibilidade) é atingida pelo mesmo mecanismo, e o parecer não a cita.

Seção nova no `PROTOCOLO.md`, "Hipóteses e braços: ajustes depois do
parecer de 01/10/2026", com status **proposto**: a H8; a reinterpretação da
H5 e, por inferência minha, da H6; o B4 desdobrado como no ADR 013; o B5
com a inicialização corrigida — proposta: escalar os logits por `c < 1`,
com a distância inicial entre os dois primeiros logits na ordem do que o
treino move, e `c` fixado nas sementes de exploração; e um braço B2', a
porta corrigida congelada, acréscimo meu, para o contraste com o B5 isolar
o gradiente. Perguntas 14 (esses ajustes) e 15 (o prazo de congelamento)
abertas no `PERGUNTAS.md` e na tabela do protocolo; a pergunta 3 ganhou
adendo — o código do modelo de referência foi cedido em 29/09.

Revisão final contra as duas mensagens de 01/10: a tabela principal do
relatório 3 ainda trazia VIP, RF e Random init como ponto, sem a faixa entre
sementes, contra o "valores de rede vão como faixa, não como ponto" da
orientação. As faixas já estavam no anexo; passaram à tabela.

Última leitura, como a orientação vai ler — só com os anexos na mão:

- o ADR 013 apontava para o "DIARIO de 21/10", que ela não tem (nada foi ao
  GitHub desde 21/09); passou a apontar para a seção do relatório 3;
- o protocolo dizia que o Jaccard alto **entre partições** é o esperado de
  modelos com "a mesma inicialização". Isso vale para as folds, que dividem
  o mesmo prior; entre partições o prior é recalculado, e o quanto ele muda
  nunca foi medido. A frase passou a ser atribuída ao parecer, com essa
  ressalva, e a medida ficou como primeira tarefa do piloto;
- o ADR 013 passou a dizer que o braço "porta na inicialização" treina o
  resto da rede com o mesmo protocolo e orçamento do PGSG treinado, e que
  os R² comparados à dispersão do PGSG treinado são os das redes;
- o cabeçalho do protocolo deixou de dizer só "congela ~27/10": cita a
  pergunta 15 e a H8 proposta.

### Revisão de ponta a ponta

**Reprodutibilidade:** os oito scripts de verificação, rodados do zero,
deram saída idêntica, linha a linha, aos anexos dos quatro relatórios.
Suíte: 97 passed, 1 skipped. Nenhum `__pycache__` no código do artigo.

**Conferido pela primeira vez:** a afirmação de que nenhum script do
pipeline do Tecator chama `torch.manual_seed` vinha das sessões anteriores
sem conferência. Conferida: a única chamada em toda a árvore está em
`revision_talanta/`, de outro artigo.

**Três afirmações acima da medida, corrigidas nos relatórios:**

- 3b: "o alvo correto não muda nada; a banda de 931 nm tem o mesmo valor" —
  a própria tabela mostra 0,215 contra 0,217 e 0,348 contra 0,353. Passou a
  "praticamente não muda".
- 3b, Seção 3.4: "os logits andam no máximo ~2, qualquer que seja o peso do
  termo" — o deslocamento só foi medido no λ do artigo; para os outros é a
  conta do passo do Adam. Passou a dizer qual é medida e qual é conta.
- 3: a comparação ANOVA × aleatório na gordura (p = 0,307) é de 10
  sementes, e a mediana do ANOVA nessa coluna varia de 0,908 a 0,942 entre
  blocos de 10. Ganhou a ressalva de que é frágil ali.

**Releitura do ADR 013 — uma lacuna de conteúdo.** O "PGSG treinado" era
definido como "o protocolo declarado no artigo", e no artigo a paciência
observa o próprio conjunto de teste — o vazamento que o relatório 3 aponta.
No protocolo deste trabalho o braço não vê o teste (contrato `Arm`). O ADR
e a tabela de braços do protocolo passaram a dizer: hiperparâmetros do
artigo, parada sobre uma fold de validação interna; a parada sobre o teste
fica só na reexecução fiel, para comparação. Também no ADR 013: o item do
ADR 004 dizia que a conclusão dele "precisa ser revisitada", quando o
adendo de 30/09 já a registra como caída; e "os R² das redes caem na
dispersão do PGSG treinado" passou a "de cada braço treinado", porque a
Plain CNN não é o PGSG leve.

### Checagem sistemática: cada número e cada citação contra a fonte

Em vez de reler, cruzei por script todos os números do texto dos quatro
anexos — ADR 013, a seção nova do protocolo, relatórios 3 e 3b — contra as
saídas medidas dos scripts, o artigo e as mensagens da orientação, levando
em conta o arredondamento; e cada citação, palavra por palavra, contra o
parecer, o manuscrito, a carta e os highlights.

**Números que estavam no texto sem nenhum script que os produzisse** — medidos
em rascunhos que se perderam, ou num comando avulso:

- ADR 013: o 0,946 → 0,9426 / 0,9428 das réplicas. Agora em
  `scripts/verificar_replicas_tecator.py`, que reproduz também os 22 pares,
  os 22 com `y` idêntico, os 2 agrupados pelo ADR 009 e os 7 que atravessam
  a partição. Sustenta também o A1.
- Relatório 3b: a tabela do pico (bandas 39–41: prior, logit, porta), o vale
  de 862 nm e o 2,4% do prior bruto citado no ADR 013. Agora impressos pelo
  `verificar_secao52_pgsg.py`, e batem.
- Relatório 3: os erros-padrão 0,0196 e 0,0220 do ± 0,018. Saíram do texto;
  ficaram os desvios 0,0439 e 0,0491, que a orientação obteve também.

**Citações que não eram literais:** "8 of the top-10 bands appeared
consistently in all 5 folds" (o texto real tem "in the top-10 selections
of"); a frase da carta, citada sem "Tecator (…)" e "content"; e, no ADR 013,
uma paráfrase do parecer junto de uma citação dele — agora citado como
está ("o modelo publicado corresponde ao primeiro deles").

Depois das correções, nenhum número dos quatro anexos fica sem fonte.
Suíte: 97 passed, 1 skipped.

**Próximo**
Mandar à orientação o ADR 013 com o parágrafo do B4, os relatórios 3 e 3b
corrigidos, o `PROTOCOLO.md` com a seção nova, a pergunta sobre o prazo e o
pedido do script dela.

### Envio à orientação (16:57–16:58)

Mensagem de resposta ao "tudo bem?", explicando a pausa pelo período de
eleição no TRE, com três anexos, na versão final do dia:

- `docs/ADR/013-ancora-do-portao-do-estagio-2.md` — com a seção "O braço B4";
- `results/verificacao_3_pipeline_com_o_alvo_correto.md` e
  `results/verificacao_3b_secao_5_2.md` — corrigidos com os dois erros e os
  três achados apontados por ela em 01/10.

Dois pedidos: que ela diga se concorda com a leitura do B2 no ADR 013, e o
script dela da reprodução, por causa da Plain CNN. Conferido pelo tamanho
dos arquivos que os três enviados são as versões finais.

**Decisão minha:** o `PROTOCOLO.md` — a seção nova "Hipóteses e braços" e a
pergunta do prazo de congelamento — **não foi enviado** e fica para depois.
A grade só roda no segundo semestre. A seção segue no arquivo, marcada como
proposta, e as perguntas 14 e 15 seguem abertas e não enviadas. O prazo de
~27/10 do protocolo passou sem congelamento.

**Próximo**
Esperar a resposta sobre o ADR 013 e o script dela. Enquanto isso, seguir o
Estágio 2, que não depende dela: o custo do `IPLSArm` nos outros três
conjuntos, e depois o CARS, o GA-PLS e o VIP.

### Custo do iPLS nos quatro conjuntos — interrompido, parcial

`scripts/medir_custo_ipls.py`, novo: `evaluate()` com o PLS completo e o
`IPLSArm` em busca completa, `seed_split` 0, `seed_algo` 0. Os R² são de uma
partição só — conferem o encanamento, não são resultado.

| conjunto | PLS completo | iPLS, busca completa | razão |
|---|---|---|---|
| Tecator | 101 ajustes, 0,2 s | 9.056 ajustes, 16,0 s | 89,7× em ajustes, 71,3× em tempo |
| Gasoline | 101 ajustes, 0,1 s | 15.749 ajustes, 27,4 s | 155,9× em ajustes, 234,1× em tempo |
| Mango | 101 ajustes, 14,9 s, **H = 20** | **quebrou** | — |
| bioprocess | — | **interrompido** aos ~50 min, sem resultado | — |

O Tecator repete a medida de 28/09 (89,7× em ajustes): o braço não mudou.

**Dois achados no Mango, a investigar antes de qualquer correção:**

1. **O iPLS quebra:** o `mdatools::ipls` dá "system is exactly singular"
   (`solve.default(crossprod(xloadings, weights))`) dentro da busca nas
   folds. Hipótese, não conferida: o `glob_ncomp` vem do PLS completo, que
   escolheu 20 componentes, e intervalos de ~30 bandas vizinhas, muito
   colineares depois do SNV, não sustentam tantos componentes. O recorte
   atual do `int.ncomp` é pela largura do intervalo, não pelo posto.
2. **O PLS completo bateu no teto:** `MAX_COMPONENTS = 20` em
   `src/tcc/arms/pls.py`, e no Mango a regra de um erro-padrão escolheu
   exatamente 20. Escolha no limite da grade sugere que o teto pode ser
   baixo demais para n = 11.691. Mexe no A1, a referência de todos os
   braços, e numa regra do protocolo — não alterar sem medir.

**Próximo**
Investigar os dois achados do Mango; rodar o bioprocess sozinho, sem o
filtro que segurava a saída, para acompanhar o progresso; depois, o ADR 014
do VIP, com o desenho proposto em 27/10 (limiar por CV entre 0,8, 1,0, 1,2 e
1,5, parcimônia escolhendo o maior limiar, seleção aninhada por fold).

## 2026-10-28

### Custo do iPLS, refeito um conjunto por vez — e os dois achados do Mango

Tecator e Gasoline refeitos: mesmos ajustes de 27/10 (9.056 e 15.749; 89,7×
e 155,9× o PLS completo). O tempo varia de uma execução para outra.

**O erro do iPLS no Mango tem causa nos dados.** Diagnóstico em rascunho,
sobre o treino da `seed_split` 0:

- o CSV do Mango cobre **285 a 1200 nm** (306 bandas, passo 3 nm), e o
  loader usa todas as colunas numéricas;
- **25 bandas são constantes** — o mesmo valor nas 11.691 amostras, desvio
  exatamente zero: 285–306 nm (8) e 1152–1200 nm (17). O posto numérico do
  espectro é 281 = 306 − 25;
- Tecator, Gasoline e bioprocess não têm nenhuma banda constante;
- o `mdatools::ipls` quebra ("system is exactly singular") sempre nos
  intervalos das pontas, que contêm esses canais: o bloco não sustenta o
  número de componentes pedido. Os intervalos do meio funcionam em todos os
  `int_num` testados.

**O PLS completo do Mango está limitado pelo teto de componentes.** Com
`MAX_COMPONENTS = 20`, a regra de um erro-padrão escolhe 20 (RMSECV 1,034);
com teto 40, escolhe **32** (RMSECV 0,919, cerca de 11% melhor). Tirar as 25
bandas constantes não muda isso (H\* 32 também). São dois problemas
independentes. O segundo atinge o A1, a referência de todos os braços:
com o teto atual ele fica artificialmente pior no Mango. No Tecator e no
Gasoline o teto não pesa (H\* = 3).

**Nada foi alterado.** Correções possíveis, a decidir: tirar do Mango as
bandas de variância zero (curadoria, mexe no ADR 006, aceito — vai como
proposta); subir o `MAX_COMPONENTS` (muda o `n_fits` de referência do PLS e,
provavelmente, testes que fixam 101). Pergunta maior, não verificada: a
literatura do Mango parece usar só 684–990 nm — fica para a revisão
dirigida e para a orientação.

O bioprocess ainda não foi medido.

### As duas correções do Mango, aplicadas

**Canais mortos.** O `_load_mango()` remove as 25 bandas constantes, com
trava que falha se a fonte mudar; Mango passa a 281 bandas (309–1149 nm).
Adendo de 28/10 no ADR 006, com o novo `sha256`
(`6c79f05e…26a3`). Decisão minha, não vista pela orientação; o status do
ADR 006 segue "aceito" para a decisão original.

**Teto de componentes.** `MAX_COMPONENTS` de 20 para 40 em
`src/tcc/arms/pls.py`, e o `PLSArm` passou a avisar quando a escolha cai no
teto. Adendo de 28/10 em "Validação cruzada interna", no `PROTOCOLO.md`.
Decisão minha, não vista pela orientação.

Testes novos: `test_no_constant_band` (quatro conjuntos) e o par
`test_warns_when_choice_hits_the_ceiling` /
`test_no_warning_when_choice_is_below_the_ceiling`. Os dois primeiros
conferidos por mutação — tirar o aviso e deixar de remover as bandas fazem
cada um falhar —, com os arquivos restaurados e o hash conferido. Suíte:
**103 passed, 1 skipped**.

**Efeito colateral do teto, medido.** A comparação de pré-processamento do
Tecator (`compare_preprocessing_tecator.py`, versionada) foi refeita com o
teto 40:

- **SNV — o pré-processamento do protocolo — não muda:** R² médio 0,9686,
  maior H\* 13, igual ao de antes, linha a linha.
- **As variantes com derivada pioram em algumas sementes:** a busca vai a
  21–31 componentes, o RMSECV cai e o R² no teste cai junto (pior caso
  0,964 → 0,841, derivada, semente 4) — sinal de CV otimista com muitos
  componentes. SNV→derivada passa de 0,9688 para 0,9676 de R² médio, abaixo
  do SNV: a escolha de 17/09 se reforça.

Hipótese testada e **não confirmada**: que o otimismo venha dos pares
idênticos em folds diferentes (A1). Agrupando os pares, o H\* cai em quatro
das sete linhas e sobe em três, e o teste é confundido — mudar os grupos
muda também a partição.

O arquivo versionado da comparação foi **restaurado à versão do git**: é a
evidência da decisão de 17/09, citada no protocolo, e não deve ser trocado
calado. Os números acima ficam só aqui. Decisão: manter o teto 40, porque
corrige o Mango e não muda nada no que o protocolo usa.

### Custo do iPLS: a tabela dos quatro conjuntos, com teto 40

`scripts/medir_custo_ipls.py`, `seed_split` 0, `seed_algo` 0. O bioprocess
terminou em 2 h 31 min, dentro do limite de 3 h que eu tinha deixado. Tecator
e Gasoline foram refeitos depois, com o teto 40, para a tabela seguir uma
regra só; no bioprocess, o PLS completo foi refeito sozinho com teto 40 (o
iPLS tinha rodado com o código carregado antes da mudança).

| conjunto | PLS completo | iPLS, busca completa | razão em ajustes |
|---|---|---|---|
| Tecator | H = 3, 201 ajustes, 0,4 s | 9.156 ajustes, 17,4 s | 45,6× |
| Gasoline | H = 3, 176 ajustes, 0,3 s | 15.824 ajustes, 30,2 s | 89,9× |
| Mango | H = 32, 201 ajustes, 116,8 s | 15.282 ajustes, 901,9 s | 76,0× |
| bioprocess | H = 7, 201 ajustes, 274,8 s | 22.239 ajustes, 9.059,1 s (teto 20) | — |

- **O `n_fits` do iPLS inclui a busca do PLS completo:** com o teto 40, o
  iPLS do Tecator ganhou exatamente os 100 ajustes que o PLS ganhou (9.056 →
  9.156), e o do Gasoline, 75 (15.749 → 15.824; o Gasoline para em 35
  candidatos, pelo tamanho da menor fold). Por essa conta, o iPLS do
  bioprocess com teto 40 daria 22.339 ajustes, cerca de 111× — **estimado,
  não medido**. A escolha não muda: H = 7 fica abaixo dos dois tetos.
- **O tempo é só ordem de grandeza.** O Mango e boa parte do bioprocess
  rodaram ao mesmo tempo; a razão em tempo não entra na tabela.
- R² de uma partição só, para conferir o encanamento: o iPLS do Tecator
  repete o 0,9415 de 28/09; Gasoline, PLS 0,9839 e iPLS 0,9610;
  bioprocess, PLS 0,8677 e iPLS 0,8712 (10 intervalos, 1.309 de 1.870
  bandas).

**O que isso pesa na grade:** com dez sementes, só o iPLS no bioprocess
passa de 25 horas. Cabe, rodando por partes; o custo do GA-PLS e do CARS
ainda não foi medido. A decisão (faixa menor de `int_num` no bioprocess,
busca reduzida, ou aceitar o custo) é da orientação, antes de congelar o
protocolo.

### Braço VIP (ADR 014, proposto)

**Fontes.** Tentei ler as referências primárias do VIP: Wold et al. 1993 e
2001, Chong e Jun 2005, Mehmood et al. 2012 e 2020, Farrés et al. 2015.
Nenhuma abriu, por ser paga ou porque o site bloqueou o acesso automático
(Mehmood 2020 é aberta, mas a editora recusou). Não forcei o download. O que
li: a documentação da Eigenvector (VIP "próximo de 1 ou maior" é importante;
eliminar em rodadas é mal sustentado; cita Chong e Jun) e o código e o manual
dos dois pacotes R já instalados. O ADR marca o que vem de fonte lida e o
que não vem; a faixa de limiares {0,8; 1,0; 1,2; 1,5} é escolha minha, a
conferir com Chong e Jun.

**Achado: o `plsVarSel` e o `mdatools` não calculam o mesmo VIP.**
`scripts/verificar_vip.py`, com SNV, autoescala e H = 5: o VIP do projeto
bate com o `plsVarSel::VIP` até 1e-14 nos quatro conjuntos. Com o
`mdatools::vipscores`, a diferença chega a 0,86 (Mango). Diagnóstico em
rascunho, no Tecator: o `mdatools` usa os pesos do SIMPLS, `R = W(P'W)⁻¹`,
e com eles a fórmula do projeto reproduz o pacote até 1,6e-12. A escolha
muda a seleção (Gasoline, VIP ≥ 0,8: 339 bandas com `W`, 200 com `R`). O
braço segue o `plsVarSel` (`W`). Adendo no ADR 008.

**Implementação.** `src/tcc/arms/vip.py`: o VIP sai do mesmo `PLSRegression`
autoescalado do A1, com H pela regra de um erro-padrão, e a seleção é
aninhada por fold. O limiar é escolhido pela regra de um erro-padrão com
desempate para o **maior** limiar (menos bandas), e um limiar que esvazie
algum fold sai da disputa. O PLS final é reajustado nas bandas com o mesmo
H, recortado. `band_scores` é o VIP.

**Testes.** `tests/test_vip.py`, 13 testes, incluindo o verificador
anti-vazamento do ADR 011 no braço e uma versão vazada que ele reprova. Cinco
mutações conferidas, cada uma derrubando pelo menos um teste, com o arquivo
restaurado e o hash conferido. Três delas passavam na primeira rodada:
desempate pelo menor limiar, corte estrito e tirar a normalização de `w_a`.
Os testes foram reforçados até as três caírem. Suíte: **116 passed, 1
skipped**.

**Custo e encanamento** (`scripts/medir_custo_vip.py`, `seed_split` 0):

| conjunto | PLS: R², ajustes | VIP: R², ajustes | limiar | bandas |
|---|---|---|---|---|
| Tecator | 0,9660, 201 | 0,9658, 222 | 1,2 | 16 de 100 |
| Gasoline | 0,9839, 176 | 0,9817, 202 | 1,0 | 108 de 401 |
| Mango | 0,8676, 201 | 0,8570, 227 | 0,8 | 143 de 281 |
| bioprocess | 0,8677, 201 | 0,8753, 227 | 1,2 | 345 de 1870 |

O VIP custa cerca de 1,1 vez o PLS em ajustes; o iPLS, de 46 a 111 vezes. Os
R² são de uma partição só e não são resultado. No Tecator, o limiar 1,5
esvaziou algum fold e saiu da disputa.

Decisão minha, não vista pela orientação.

**Mehmood, Sæbø e Liland (2020), lido.** Consegui o PDF pela CAPES, e ele
ficou fora do repositório. Ele confirma:
- a fórmula do braço, com os *loading weights* `w_a` do NIPALS, e não os
  pesos do SIMPLS;
- a origem: Wold, Johansson e Cocchi (1993), com o nome VIP dado por
  Eriksson et al. (2001);
- o corte "geralmente aceito" em 1;
- a validação cruzada dupla para ajustar o limiar de métodos de filtro, que
  é o desenho aninhado do braço.

No estudo de simulação deles, o limiar ajustado ficou em 0,90. ADR 014
atualizado com seção e tabela de cada afirmação. Continuam sem leitura
direta: Wold 1993 e 2001, Chong e Jun 2005 (de onde viria uma faixa de
limiares) e Farrés 2015. Os valores 0,8, 1,2 e 1,5 seguem como escolha minha.

**Próximo.** GA-PLS (`plsVarSel::ga_pls`) e depois o CARS (libPLS). Pegar
pela CAPES o Wold 2001 e o Chong e Jun 2005, guardar fora do git (o
repositório é público e os artigos são pagos) e conferir o ADR 014 contra
eles.

## 2026-10-29

### Conferência do ADR 014 contra as fontes

Cada afirmação do ADR 014 foi conferida contra o PDF de Mehmood et al.
(2020), lido agora por inteiro, e contra as saídas dos scripts. Batem: a
fórmula, a origem e o nome (referências 13 e 19), o corte em 1 (referências
19 a 21: Eriksson 2001, Chong e Jun 2005, Gosselin 2010), o limiar 0,90 da
Tabela 2, a validação cruzada dupla (Seção 4.3), a licença CC BY e todos os
números da tabela de custo.

**Correções à entrada de 28/10:**
- **Diferença para o `plsVarSel`.** "Até 1e-14" era impreciso: a diferença
  máxima foi 1,3e-14, o que continua sendo erro de arredondamento.
- **Limiar 1,5 no Tecator.** Não esvaziou "algum fold": esvaziou os cinco.
  Medido agora, na `seed_split` 0: o maior VIP por fold fica entre 1,26 e
  1,30, e a conta fecha (200 da busca de H + 5 + 15 + 2 = 222 ajustes). A
  afirmação de 28/10 tinha sido deduzida da contagem, sem medir.
- **Custo do iPLS.** O 111 da faixa "46 a 111 vezes" é a estimativa do
  bioprocess, não uma medida.
- **Leituras pendentes.** A lista de 28/10 omitia Mehmood et al. (2012), que
  também não foi lido.
- **Wold 2001 e Chong e Jun 2005.** Conferi que esses dois só saem pagos. Não vão ser buscados por outra via. Ficam como citação
  secundária, com os valores 0,8, 1,2 e 1,5 declarados como escolha minha.

ADR 014 ajustado nesses pontos, e com mais um apoio: Mehmood et al.
classificam o VIP como método de filtro, de uma passada (Seção 3.1), e
chamam de *wrapper* a versão em rodadas (Seção 3.2). É a escolha do braço.

Para o GA-PLS, o mesmo artigo descreve o algoritmo (Seção 3.2.1, atribuído a
Hasegawa et al.) e traz a taxa de mutação ajustada no estudo deles (R0 =
8,39, Tabela 2). Ainda não conferi o que isso significa na escala da função
`ga_pls`.

### GA-PLS: o `plsVarSel::ga_pls` não serve como está

Antes de desenhar o braço, li o código do `ga_pls` (`plsVarSel` 0.10.0), da
função que avalia cada cromossomo (`plsVarSel:::evaluateX`) e do motor
genético (`genalg::rbga.bin`, 0.2.1). Depois conferi rodando, com
`scripts/verificar_ga_pls_plsvarsel.py` (Tecator, SNV, `set.seed(1)`,
defaults do pacote: `GA.threshold` 10, população 100, 5 gerações).

1. **A seleção devolvida é o cromossomo com mais variáveis, não o de menor
   erro.** A última linha do `ga_pls` faz `which.max(rowSums(population))`
   e ignora as avaliações. Medido: devolveu 14 bandas com PRESS 1018,0, quando
   a população final tinha um cromossomo de 9 bandas com PRESS 880,7. O PRESS
   com as 100 bandas é 1025,1, então a seleção devolvida quase não melhora
   sobre o espectro inteiro.
2. **A avaliação usa folds próprias.** `plsr(validation = "CV")` sorteia
   segmentos aleatórios, sem as folds do protocolo e sem os grupos do ADR 009.
   Réplicas do Mango e do bioprocess cairiam em segmentos diferentes, o que dá
   um PRESS otimista.
3. **O número de componentes é fixo.** Por código, o PRESS é sempre o de 4
   componentes (`ncomp = min(5, k)`, índice `ncomp - 1`), e não o da regra de
   um erro-padrão. A avaliação também não autoescala, ao contrário do A1.
4. **Cromossomo com menos de 2 variáveis recebe PRESS fixo 100.** Esse valor
   não depende da escala de y. No Tecator ele é muito menor que qualquer PRESS
   real (cerca de 880 a 1025), ou seja, um cromossomo de 1 banda "venceria" se
   aparecesse. Na população medida, o menor tinha 4 bandas, então não
   aconteceu.

Com o mesmo `set.seed`, a seleção se repete; com sementes diferentes, muda.
O mapeamento `seed_algo` → `set.seed` do ADR 008 funciona.

O ADR 008 escolheu o `plsVarSel` para o GA-PLS sem ter lido esse código. Usar
o `ga_pls` como está seria o "braço aleijado" que o pipeline proíbe. A saída
muda a decisão do ADR 008 e precisa ser decidida antes de qualquer código.

### GA-PLS: pacote GA com a nossa avaliação (ADR 015, proposto)

**Decisão.** Motor genético do pacote R `GA` (Scrucca 2013, 3.2.5, instalado
hoje), com avaliação e escolha final nossas. Era a opção que eu recomendei
entre quatro: GA mais a nossa avaliação, `genalg` mais a nossa avaliação, o
`ga_pls` como está, ou perguntar ao professor antes.

**O custo, e como ficou viável.** Cada avaliação é uma CV com 4 PLS. Com o
`PLSRegression`, medi 0,77 s no Mango e 3,18 s no bioprocess por avaliação.
Com os padrões do pacote (50 × 100) e a seleção aninhada, isso daria cerca de
5 h e 21 h por partição (estimativa). A saída foi calcular a avaliação por
kernel PLS (Dayal e MacGregor 1997) sobre os produtos cruzados `X'X` e `X'y`
de cada fold, feitos uma vez com todas as bandas. Conferido num rascunho
contra o `_fit_pls` nos quatro conjuntos, com metade das bandas sorteada:

| conjunto | maior dif. relativa no RMSE | avaliação antes | agora | ganho |
|---|---|---|---|---|
| Tecator | 1,2e-14 | 0,022 s | 0,0003 s | 82× |
| Gasoline | 3,3e-14 | 0,005 s | 0,0017 s | 3× |
| Mango | 3,8e-13 | 1,477 s | 0,0097 s | 152× |
| bioprocess | 5,1e-15 | 1,995 s | 0,0641 s | 31× |

Com isso, população e gerações vão à CV entre (30, 50) e (50, 100), como o
pipeline pede, em vez de serem fixadas.

**Primeira medição, com a população inicial padrão do GA** (cada bit com
chance 0,5), `scripts/medir_custo_gapls.py`, `seed_split` 0:

| conjunto | PLS: R² | GA-PLS: R² | bandas | ajustes | tempo |
|---|---|---|---|---|---|
| Tecator | 0,9660 | 0,9652 | 38 de 100 | 125.298 | 9,7 s |
| Gasoline | 0,9839 | 0,9795 | 193 de 401 | 126.415 | 36,8 s |
| Mango | 0,8676 | 0,8746 | 136 de 281 | 126.694 | 110,0 s |
| bioprocess | 0,8677 | 0,8722 | 921 de 1870 | 127.289 | 2.579,8 s |

Os quatro escolheram (50, 100). **O braço ficou perto da metade das bandas**
(38 a 49%): a população começa com metade e a mutação do GA
(`gabin_raMutation`) troca um bit por vez, então não desce. Lido no código
do pacote, não suposto. Decisão: densidade inicial fixa em 0,1. Fica entre o
padrão do `plsVarSel` (1 para 10, cerca de 9%) e o valor ajustado em Mehmood
et al. 2020 (R0 = 8,39, cerca de 11%; que esse R0 seja o mesmo parâmetro é
leitura minha). Testes e mutações refeitos; medição refeita abaixo.

**Testes.** `tests/test_gapls.py`, 13 testes, entre eles:
- o kernel PLS igual ao `_fit_pls`;
- a seleção final sendo o melhor cromossomo;
- a população inicial com cerca de 10%;
- o verificador anti-vazamento, com uma versão vazada que ele reprova.

Nove mutações, todas derrubando pelo menos um teste, com o arquivo
restaurado e o hash conferido. Suíte: **129 passed, 1 skipped**.

**Medição com densidade 0,1:**

| conjunto | PLS: R² | GA-PLS: R² | (pop., ger.) | bandas | ajustes | tempo |
|---|---|---|---|---|---|---|
| Tecator | 0,9660 | 0,9646 | (30, 50) | 16 de 100 | 111.030 | 14,9 s |
| Gasoline | 0,9839 | 0,9755 | (50, 100) | 40 de 401 | 126.415 | 18,4 s |
| Mango | 0,8676 | 0,8794 | (50, 100) | 54 de 281 | 126.694 | 228,6 s |
| bioprocess | 0,8677 | 0,8703 | (30, 50) | 185 de 1870 | 112.899 | 479,7 s |

R² de uma partição, não resultado. O bioprocess rodou em 8 minutos. No
Gasoline e no bioprocess, o número de bandas ficou em cerca de 10%, igual à
densidade inicial: ela funciona como preferência forte pelo tamanho do
subconjunto. Registrado no ADR 015 como fragilidade, a levar à orientação.

ADR 015 escrito (proposto) e adendo no ADR 008: o GA-PLS deixa o `plsVarSel`.
Decisão minha, não vista pela orientação.

**Próximo.** CARS (libPLS), o último braço clássico.

## 2026-11-04

### As duas mensagens da orientação (29/10, 16:48, e 30/10, 13:55)

**29/10**, com o script `verify_plaincnn.py`:
- **A divergência da Plain CNN** (relatório 3, em aberto desde 01/10) foi um
  erro de chamada na reprodução dele. `create_model_light(n_bands,
  n_outputs=1, prior_path=None)` e `create_model(n_bands, n_outputs=1,
  prior_type='anova', prior_path=None)` não têm a mesma assinatura. O
  caminho do prior, passado como terceiro argumento posicional, caiu em
  `prior_type` no modelo pesado, e a Plain CNN dele treinou sem prior. A
  minha implementação (instanciando `BandSelectNet` direto) foi dada como
  a certa.
- **ADR 013:** o confundidor `fc1(x ⊙ g) = (W1·diag(g))·x`. O B2 alcança
  qualquer primeira camada que o B4 alcance, reescalando W1, então
  Δ = B4 − B2 ≈ 0 não distingue porta parada de porta absorvida pelo MLP.
  Pediu também: reportar o Δ com o deslocamento da porta, o que o
  Δ_ponderação passa a medir, o KL inerte no B2, e "mesmo orçamento" como
  a mesma regra de parada. Palavras dele: "Com essas adições, o ADR 013
  passa a aceito."
- Argumento nomeado como regra no código.

Respondi no mesmo dia (19:12–19:13). Disse que rodei o script e que a causa
se confirma, mas que os números não saíram iguais aos dele. Avisei que, no
`train_light`, o decaimento de peso pega os logits da porta. Perguntei se a
H8 devia ser ajustada do mesmo jeito. E adiantei que o iPLS levou cerca de
2,5 h numa partição do bioprocess.

**30/10**, com o script `verify_wd_on_gate.py`:
- **O decaimento na porta.** Ele mediu, e o deslocamento de 1,45 a 1,92 que
  nós dois líamos como "o treino move a porta" é, na maior parte,
  encolhimento L2 rumo ao uniforme. Pediu para corrigir isso no relatório
  3b.
- **H8:** ajustar com três mecanismos para o Δ ≈ 0 (porta que não anda,
  MLP que absorve, encolhimento L2), nomeando as medidas que os separam.
  Fixar o termo: no pgsg_0 o que trava o topo é a distância de 11,5
  logits contra o passo do Adam, não atenuação de gradiente.
- **B4 fiel ao artigo** (porta com decaimento) **e B4 limpo** (porta
  isenta): escolher no protocolo, antes de rodar.
- **Ambiente:** retirou a observação dele sobre a água (o prior "melhora",
  0,100 contra 0,002), que aqui deu a direção oposta. Pediu uma linha no
  relatório 3 dizendo que o mesmo script dá medianas diferentes em máquinas
  diferentes.
- **Custo do iPLS:** perfilar antes de otimizar; nada de reduzir semente
  em silêncio; o custo é resultado; paralelismo, com a pergunta de que
  máquina eu tenho; e, se for preciso cortar, um espectro por mistura no
  bioprocess, que ele também apresenta como correção de vazamento.
- Um teste que falhe se alguma fábrica for chamada com mais de dois
  argumentos posicionais.

### Os dois scripts dele, rodados aqui

Rodei cada script duas vezes, fora do repositório e sem alterar nada. As
duas rodadas deram resultado idêntico, e não ficou `__pycache__` na pasta
do pgsg. Ambiente: torch 2.14.1+cpu, numpy 2.5.2, scikit-learn 1.9.0.

**`verify_plaincnn.py`** (10 sementes por célula, mediana [mín; máx]):
- **A causa se confirma.** Minha célula, porta ANOVA + `train_proper` na
  gordura, dá 0,005 [−0,53; 0,17], o mesmo número que eu tinha. A célula
  que reproduz a dele, sem prior + `train_light`, continua sendo a única da
  gordura claramente acima de zero.
- **Os números não batem com os dele.** Nessa célula da gordura ele mediu
  0,361 [−0,02; 0,82], e aqui dá 0,226 [−0,02; 0,85].
- **Na água, a direção inverte:** ANOVA + `train_proper` dá −0,019, contra
  0,004 sem prior.

Tabela completa no Anexo 3 do relatório 3.

**`verify_wd_on_gate.py`** (modelo leve, 10 sementes):
- **Deslocamento máximo com o decaimento do artigo:** 1,694 na água e
  1,654 na gordura.
- **Com a porta isenta:** 0,278 e 0,301, cerca de seis vezes menor. Ele
  escreveu "sete vezes", com 1,81 e 1,69 no publicado.
- **Estatísticas de direção:** batem com as dele. Fração encolhida 0,765
  e 0,750; correlação com −θ₀ 0,806 e 0,810.
- **O R² não bate:**
  - com decaimento só no MLP, aqui dá 0,913 e 0,941, e ele mediu 0,887 e
    0,920;
  - com o decaimento do artigo, aqui dá 0,922 e 0,922, e ele mediu 0,925
    e 0,924.

  A conclusão dele, de que isentar a porta não custa desempenho, vale nas
  duas máquinas.
- **Sem decaimento nenhum,** o R² cai para 0,644 e 0,244.

Tabela no Anexo 4 do relatório 3b.

### O que mudou nos documentos

- **Relatório 3:**
  - fechei a seção da divergência, com a causa e a tabela das oito
    células, dele e daqui;
  - registrei a linha sobre máquinas diferentes e a observação da água
    que ele retirou;
  - deixei em aberto, sem causa, os PGSG 5-fold 0,868 contra 0,859 e a
    ANOVA na água 0,922 contra 0,932.
- **Relatório 3b:** corrigi a leitura do deslocamento como encolhimento,
  com a tabela dos três decaimentos. O Gasoline (1,22 a 1,79) também tem o
  decaimento na porta e não foi decomposto: só medi o Tecator.
- **ADR 013:**
  - **status "aceito (04/11/2026)"**, pela frase dele de 29/10, e com a
    nota de que ele ainda não viu a parte do decaimento (30/10) nem a nota
    da Plain CNN;
  - nova seção "O que o Δ mede", com os acréscimos que ele pediu e os três
    mecanismos;
  - a frase antiga do "mede diretamente" ficou, com uma nota de correção.
- **PROTOCOLO:**
  - H8 reescrita, com Δ = R²(B4-limpo) − R²(B2), TOST, os três mecanismos e
    as medidas;
  - o termo "saturação" ficou só para o efeito do clip;
  - o B4 foi dividido em B4-fiel e B4-limpo. Sem qualificador, "B4"
    significa B4-limpo, exceto na comparação com o artigo;
  - "mesmo orçamento" passou a significar a mesma regra de parada;
  - a seção continua "proposto".
- **Decisão minha, a confirmar com ele:** o B3 e o B5 com a porta isenta.
  O critério do `c` do B5 foi escrito sobre o deslocamento com decaimento
  (~2); com a porta isenta, ele cai para ~0,3. Vai à pergunta 14.

### Argumento nomeado, com teste

`tests/test_named_arguments.py` varre `src`, `scripts` e `tests` pela
árvore sintática. O teste falha se uma classe de `src/tcc`, ou um
classmethod dela, for chamada com mais de dois argumentos posicionais ou
com `*args`.
- **Na primeira passada,** ele achou as quatro chamadas
  `_CrossProducts.of(...)` do GA-PLS (`src/tcc/arms/gapls.py` e
  `tests/test_gapls.py`). Passaram a ser nomeadas.
- **Mutação conferida:** um arquivo temporário com `VIPArm(1.0, 3, (0.8,
  1.0))` foi pego. Apaguei o arquivo depois.
- **Suíte:** 132 passed, 1 skipped (remedida hoje, depois da última mudança
  num script).

### Bioprocess: os números da mistura

Conferi os 6.472 espectros e as 3.191 misturas da mensagem dele. Batem. Os
3.433 do ADR 009 são das 6.960 linhas de antes do descarte dos sem glicose
(ADR 007). Depois dele ficam 6.472 linhas e 3.191 grupos: 3.168 com 2
espectros, 1 com 4 e 22 com 6.

O agrupamento do ADR 009 já mantém as réplicas de uma mistura no mesmo
fold, inclusive na CV interna. O vazamento que ele descreve não acontece no
nosso código. Cortar para um espectro por mistura continua possível, mas
agora só por custo. O comentário de `_load_bioprocess` cita as 3.433 junto
do agrupamento das 6.472 linhas e merece uma nota.

### Custo do iPLS: onde está

Medi com `scripts/perfilar_custo_ipls.py` (bioprocess, `seed_split` 0, fold
externo 0: 3.882 linhas, 4 segmentos internos, `glob_ncomp` 7).

| int_num | tempo da chamada | ajustes estimados | ms por ajuste |
|---|---|---|---|
| 10 | 135,7 s | 226 | 600,7 |
| 15 | 254,9 s | 496 | 513,8 |
| 20 | 220,9 s | 721 | 306,4 |
| 25 | 513,3 s | 1.296 | 396,1 |
| 30 | 573,8 s | 1.726 | 332,4 |

- **A decomposição bate com a medida de 28/10.** Os 5 candidatos × 5
  folds, supondo os folds iguais ao 0, dão 8.493 s, contra 9.059 s
  medidos. Ficaram de fora a chamada final e a diferença entre folds.
- **O ajuste do mdatools é bem mais caro que o do `PLSRegression`.** Num
  ajuste isolado, nas larguras de 62 a 187 bandas, ele custa de 44 a 168
  ms, e o `PLSRegression` de 5 a 50 ms.
- **Rprof** (int_num 10, num Rscript à parte, porque de dentro do rpy2 ele
  não amostra): 77% do tempo em `crossprod`, que o R entrega ao BLAS.
- **O BLAS e o LAPACK do R são os de referência,** de uma thread só.

Então o custo vem das duas coisas: muitos ajustes, e cada ajuste caro
porque cai num BLAS lento. Ainda não separei quanto do custo por ajuste é
o BLAS e quanto é o que o mdatools calcula a mais em cada ajuste.

**Paralelismo** (K processos, cada um com a chamada int_num 30):

| K | vazão em relação a K=1 |
|---|---|
| 2 | 1,86× |
| 4 | 2,92× |
| 8 | 3,25× |

Cada processo fica mais lento à medida que K sobe: 584 s com K=1, cerca de
1.470 s com K=8.

**Máquina:** Intel Core i5-13450HX, 16 threads, 24 GB de RAM (o WSL
enxerga cerca de 11 GB). Até aqui o iPLS rodou uma partição por vez.

**Em aberto:**
- **OpenBLAS para o R.** Exige `sudo apt`, muda o ambiente e pode mexer nas
  últimas casas dos números. Não testado. Se for feito, entra declarado.
- **Nenhuma semente foi cortada.** Qualquer corte entra declarado antes de
  rodar, como ele pediu.

### Os scripts dele

Não copiei `verify_plaincnn.py` nem `verify_wd_on_gate.py` para `scripts/`.
O repositório é público, e os scripts são dele. Os relatórios citam os dois
como "não versionado". Vou perguntar se posso versionar.

**Próximo.** Responder à orientação: a máquina, o custo do iPLS, o
B3/B5/B2' com a porta isenta e o critério do `c`, o ADR 013 marcado como
aceito, o agrupamento do bioprocess e a permissão para versionar os
scripts. Depois, o CARS.

## 2026-11-05

### Nota no comentário de `_load_bioprocess`

O comentário citava "5.089 blocos vizinhos, 3.433 composições" junto do
agrupamento das 6.472 linhas. Medi os dois números de novo, e os dois são
das 6.960 linhas de antes do descarte dos sem glicose (ADR 007). Nas 6.472
que ficam, são 4.734 blocos vizinhos e 3.191 composições, o número de
grupos que `load("bioprocess")` devolve. Acrescentei uma nota ao comentário
e não mudei código. O ADR 009 cita os mesmos dois números, mas ali o texto
já diz que o descarte vem depois, então deixei como está.

### Gasoline: o deslocamento da porta, decomposto

O relatório 3b dizia que o deslocamento de 1,22 a 1,79 do Gasoline tinha o
mesmo decaimento na porta, sem medir quanto dele era encolhimento. Medi
com `scripts/verificar_decaimento_porta.py`. É um script meu, com a mesma
receita e as mesmas medidas do `verify_wd_on_gate.py` da orientação, que
não copiei. O Tecator entra como controle e reproduziu exatamente os
números de 04/11. Rodei duas vezes, com saída idêntica, em 16 s cada uma, e
não ficou `__pycache__` na pasta do pgsg.

Gasoline, 10 sementes, mediana:

| decaimento | maior deslocamento | fração encolhida | correlação com −θ₀ | R² |
|---|---|---|---|---|
| o do artigo | 1,344 [1,223; 1,789] | 0,995 | 0,724 | 0,945 |
| nenhum | 0,612 | 0,213 | −0,172 | 0,943 |
| só no MLP | 0,660 [0,487; 0,837] | 0,217 | −0,161 | 0,945 |

O Gasoline não repete o Tecator:
- **O encolhimento é cerca de metade do deslocamento,** contra cerca de
  cinco sextos no Tecator.
- **Com a porta isenta, a maioria das bandas se afasta de zero:** só cerca
  de 22% encolhem, e a correlação com −θ₀ fica negativa.
- **O R² não depende do decaimento.**
- **O topo continua imóvel:** 0,66 contra uma distância de 12,2.

Não medi por que os dois conjuntos diferem.

Atualizei:
- o relatório 3b (o parágrafo do Gasoline, com a tabela, e o Anexo 5);
- o parágrafo "Por quê" e a nota do critério do `c` no PROTOCOLO, onde a
  razão de "seis vezes" é a do Tecator;
- o mecanismo (c) do ADR 013, que é aceito, com uma frase datada dizendo
  que o peso do encolhimento muda entre os conjuntos. A orientação não viu
  essa frase.

### PROTOCOLO: a pergunta 15 sai

Decisão minha: tirei do PROTOCOLO a pergunta 15 (prazo do congelamento na
semana 11, ~27/10). A data já passou, e o congelamento depende da pergunta
14. O Status do topo deixou de citar a data e a pergunta 15, e passou a
dizer que o congelamento espera a aprovação da mudança de desenho do
parecer de 01/10 (pergunta 14). A pergunta 15 continua no histórico do git
e no `PERGUNTAS.md`, que não mexi.

### PROTOCOLO: a pergunta 14 completa, e o custo como resultado

- **Pergunta 14.** A linha da tabela e a seção 14 do `PERGUNTAS.md`
  passaram a listar as duas questões que o texto do PROTOCOLO já mandava
  para ela: em qual deslocamento se baseia o critério do `c` (com ou sem
  decaimento na porta) e a porta isenta no B3 e no B5.
- **Orçamento.** Acrescentei um parágrafo com o que a orientação disse em
  30/10: o custo de cada braço é resultado e entra na figura de custo por
  braço do pipeline, e nenhuma redução de sementes ou partições é feita em
  silêncio. Até aqui isso só estava no DIARIO de 04/11.

### Argumento nomeado também nas fábricas do pgsg

Revisando as mensagens de 29 e 30/10, vi que o teste de 04/11 só cobria
as classes do `src/tcc`. As fábricas do código do artigo, que são as do
erro de 29/10, ficavam de fora. Achei seis chamadas posicionais a elas nos
scripts de verificação:
- `verificar_varredura_treino.py:69`
- `verificar_secao52_pgsg.py:88`
- `verificar_kl_secao34.py:74`
- `verificar_pipeline_tecator.py:269`, `:271` e `:273`

Pelas assinaturas, a ordem batia em todas, então nenhum resultado estava
errado. Mesmo assim, as seis passaram a usar argumento nomeado. O teste
ganhou a lista `PGSG_FACTORIES` (`BandSelectNet`, `BandSelectNetLight`,
`SpectralGatingLayer`, `create_model`, `create_model_light`), escrita à
mão porque o código do artigo não está no repositório.

Conferido de três formas:
- **O teste reprova as versões do commit `5cd970f`:** as seis chamadas
  aparecem, e nenhuma nas versões novas.
- **Os modelos são idênticos:** com a mesma semente, cada chamada nomeada
  constrói um modelo com `state_dict` igual ao da posicional, para os três
  formatos.
- **Suíte:** 133 passed, 1 skipped. Não ficou `__pycache__` no pgsg.
