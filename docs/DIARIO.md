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
sobre a seleção aninhada:

| braço | R² | RMSEP | n_fits | tempo |
|---|---|---|---|---|
| A1 `pls_full` | 0,9660 | 2,2605 | 101 | 0,2 s |
| A3 `ipls(int_num=20)` | 0,9710 | 2,0893 | 106 | 6,3 s |
| A3 `ipls` (busca) | 0,9415 | 2,9656 | 151 | 23,7 s |

Viável no Tecator. **Não** extrapolar daqui: o bioprocess tem n=6.472 e
p=1.870, e o custo precisa ser medido lá antes de qualquer promessa sobre
a grade. E os R² são de **uma** partição — não são resultado, são prova de
que o encanamento funciona.

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
dentro. Medido: `n_fits` 6 para o A3 contra 101 do A1, com o A3 gastando
~25× mais tempo. A tabela de custo do manuscrito diria o oposto da
verdade, e o pipeline é explícito quanto ao propósito do campo ("se o
GA-PLS consumir 40× mais ajustes que o MLP, isso precisa aparecer na
tabela"). Passou a ser estimado a partir do que o mdatools reporta —
iterações da busca forward em `int.stat`, intervalos restantes por
iteração, segmentos de CV. Agora: 1.757 contra 101, razão de 17,4× em
ajustes contra 24,6× em tempo, que é a ordem de grandeza certa. Declarado
como **estimativa**, não contagem exata: o interior do pacote não é
instrumentado.

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

**Próximo**
Medir o custo do `IPLSArm` nos outros três conjuntos, sobretudo no
bioprocess, antes de seguir para o CARS. Se a seleção aninhada não couber
lá, isso é resultado e vira decisão de protocolo.
