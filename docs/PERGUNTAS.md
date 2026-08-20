# Perguntas para a orientação

Fila de dúvidas. Enviar em lote, não pingando.
Marcar com [x] quando respondida e anotar a resposta.

---

## Pendentes

### 1. Eixo de semente e a H5 — [prioridade alta, trava o protocolo]
Aberta em: 2026-08-20

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

### 4. Conjuntos de dados 3 e 4
Aberta em: 2026-08-20

Tecator e Gasoline consigo por fontes públicas. Mango DMC v3 e o conjunto
Raman de bioprocesso o grupo já possui, ou preciso localizar?

**Resposta:**

---

### 5. Proveniência do Tecator — faixa do alvo divergente
Aberta em: 2026-08-20

Carreguei o Tecator via `scikit-fda` (que o obtém do pacote R `fda.usc`) e
obtive teor de gordura variando de 0.9% a 49.1%, com 215 amostras e 100
bandas. O paper descreve a faixa como 7% a 76%.

Como o Tecator circula em variantes distintas (215 e 240 amostras, com e sem
pré-processamento), quero confirmar qual fonte exata foi usada no artigo antes
de fixar a camada de dados.

Obs.: investigar as variantes por conta própria antes de enviar esta pergunta.

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

## Respondidas

(nenhuma ainda)