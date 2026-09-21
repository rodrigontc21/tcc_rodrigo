# Perguntas para a orientação

Fila de dúvidas. Enviar em lote, não pingando.
Marcar com [x] quando respondida e anotar a resposta.

---

## Pendentes

### 1. Eixo de semente e a H5 — [prioridade alta, trava o protocolo]
Aberta em: 2026-08-20
Enviada em: 2026-08-28 (sem resposta direta até o momento)

O Estágio 0 do pipeline observa que PLS, iPLS e limiarização de VIP são
determinísticos dado o conjunto de treino: com `seed_split` fixo, o Jaccard
deles é trivialmente 1, e comparar a porta contra eles no eixo `seed_algo`
seria comparação sem significado. O documento indica que a afirmação de
reprodutibilidade deve sair do eixo `seed_split`.

Isso altera o enunciado da H5 da proposta, que fala em "Jaccard entre
sementes". O senhor quer que eu reescreva a H5 nesses termos antes de
congelar o protocolo?

**Resposta:**

---

### 2. Formato do resumo da revisão dirigida
Aberta em: 2026-08-20

Na conversa do dia 19 perguntei se o resumo deveria comparar os métodos entre
si ou tratar cada um separadamente, e a resposta ("isso") ficou ambígua para
uma pergunta de duas alternativas.

Proposta: uma ficha individual por método (iPLS, CARS, GA-PLS, VIP) e uma
tabela comparativa ao final. Serve?

**Resposta:**

---

### 3. Repositório do modelo de referência
Aberta em: 2026-08-20

O Estágio 3 do pipeline pede que o braço `gate_prior` (B4) reproduza o modelo
publicado do grupo, vendorizado com SHA-256. Existe repositório disponível do
código do Guilherme Coelho?

**Resposta:**

---

### 6. Linguagem dos braços clássicos
Aberta em: 2026-08-20

O pipeline recomenda preferir implementações estabelecidas a reescrever. Boa
parte das implementações consagradas de iPLS, CARS e GA-PLS está em pacotes R
(`mdatools`, `plsVarSel`). O senhor prefere implementação em Python, ou o uso
dos pacotes R via `rpy2` nos braços clássicos?

**Resposta:**

---

### 7. Cálculo do prior dentro da validação cruzada interna — [trava o Estágio 3]
Aberta em: 2026-08-25

O pipeline é categórico ao exigir que a seleção de variáveis clássica
aconteça dentro da validação cruzada interna, nunca antes dela, sob pena de
vazamento. O prior que inicializa a porta (B4) usa os rótulos de treino para
estimar relevância de banda — conceitualmente a mesma operação.

Se o CARS seleciona dentro da CV enquanto o prior da porta é calculado sobre
o treino inteiro, a comparação fica enviesada a favor da porta. O prior deve
ser recalculado dentro de cada fold, como os selecionadores clássicos?

**Resposta:**

---

### 8. Semente algorítmica na grade principal — [trava o Estágio 5]
Aberta em: 2026-08-25

Os termos Δ são pareados por (conjunto, `seed_split`), mas os braços B1–B4
são estocásticos, então cada célula da grade tem também um `seed_algo`. Duas
opções: uma semente por célula (diagonal), mais barata; ou média sobre 3 a 10
sementes, que estreita o intervalo de confiança ao custo de 3× a 10× no tempo
de execução dos braços neurais.

Os testes de equivalência de H2–H4 só concluem com intervalo estreito dentro
da margem. Qual das duas o senhor prefere para a grade principal?

**Resposta:**

---

### 9. Divisão 48/12 do Gasoline no protocolo da literatura — [trava o portão do Estágio 2]
Aberta em: 2026-09-21

O paper (Seção 4.1) só diz "48/12 train-test split", sem dizer quais
linhas vão para cada lado. A documentação do pacote R `pls` não define
divisão para o gasoline; a vinheta usa 50/10 sequencial, não 48/12. Testei
as candidatas com o PLS H = 5 do paper: a divisão sequencial 48/12 dá R²
0,923, e `train_test_split(test_size=0.2, random_state=42)` do scikit-learn
dá R² 0,9752 e RMSE 0,1453, batendo com os 0,975 e 0,145 publicados. Isso
também bate com o "seed 42" citado na Seção 4.2. Propus essa divisão no
[ADR 010](../ADR/010-divisao-de-literatura-do-gasoline.md), mas é
inferência pelos números, não fonte escrita.

O código do pgsg_1 confirma essa divisão para o Gasoline? E, se a semente
42 for de uma divisão aleatória, a do Tecator no paper também era
aleatória, e não os 172 primeiros sequenciais que aprovamos em 01/09? Com
a mesma semente, o Tecator dá R² 0,9489, também diferente dos 0,919
publicados.

**Resposta:**

---

## Respondidas

### [x] 4. Conjuntos de dados 3 e 4
Aberta em: 2026-08-20
Respondida em: 2026-09-17

Tecator e Gasoline consigo por fontes públicas. Mango DMC v3 e o conjunto
Raman de bioprocesso o grupo já possui, ou preciso localizar?

**Resposta:** os dois conjuntos vêm de fontes públicas. Mango: Mendeley
Data 46htwnp833, cortado para as safras 1–4 (11.691 amostras), com a
coluna `Set` preservada; curadoria aprovada pela orientação em 17/09/2026
([ADR 006](../ADR/006-curadoria-do-mango-safras-1-4.md)). Bioprocess:
`bioprocess_substrates` via `raman-data`, alvo glicose, definido pela
orientação em 14/09/2026 e já implementado; aprovado com pendência em
17/09/2026: a aprovação definitiva depende da confirmação da distribuição
dos 488 espectros sem glicose, enviada em 21/09/2026
([ADR 007](../ADR/007-alvo-do-bioprocess-glicose.md)).

---

### [x] 5. Proveniência do Tecator — faixa do alvo divergente
Aberta em: 2026-08-20
Respondida em: 2026-09-03

Carreguei o Tecator via `scikit-fda` (que o obtém do pacote R `fda.usc`) e
obtive teor de gordura variando de 0.9% a 49.1%, com 215 amostras e 100
bandas. O paper descreve a faixa como 7% a 76%.

Como o Tecator circula em variantes distintas (215 e 240 amostras, com e sem
pré-processamento), quero confirmar qual fonte exata foi usada no artigo antes
de fixar a camada de dados.

**Resposta:** as fontes são equivalentes. O orientador verificou o código
de ingestão do grupo (pgsg_1): os dados do paper vieram do OpenML (base
505), e o `y` bruto de lá (min 0,9, max 49,1, média 18,14) bate exatamente
com o que o `fda.usc` entrega. A faixa "7–76%" do paper é erro de prosa —
no `summary()` do R, 7,30 é o 1º quartil da gordura e 76,60 é o máximo da
água. Nenhum resultado do paper está comprometido. Decisão registrada no
[ADR 004](../ADR/004-proveniencia-do-tecator.md): Tecator canônico via
`skfda`/`fda.usc`, alvo fat selecionado por nome, com hash do arquivo
carregado — e a ressalva de que o loader inspecionado é o da rodada de
revisão (`revision_pgsg_0_r1`); a submissão original permanece não
verificada.