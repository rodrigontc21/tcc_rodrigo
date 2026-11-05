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

**Adendo (27/10/2026).** Respondida na prática, sem resposta escrita à
pergunta: a orientação cedeu o código-fonte do artigo em 29/09, guardado em
`docs/fontes/prior-guided-spectral-gating-main/`, fora do versionamento. O
repositório público declarado no artigo
(`github.com/clarimar/prior-guided-spectral-gating`) também está acessível.
Falta a vendorização com SHA-256 que o pipeline pede para o Estágio 3.

---

### 6. Linguagem dos braços clássicos
Aberta em: 2026-08-20
Enviada em: 2026-09-21 (sem resposta)
Reescrita em: 2026-09-28 — a versão anterior dizia que o `plsVarSel` tinha
CARS, o que não é verdade

O pipeline recomenda preferir implementações estabelecidas a reescrever, e
não indica linguagem — todos os blocos de código dele são Python. Fui
atrás de onde estão as implementações estabelecidas, método a método:

- **iPLS**: `mdatools`, em R;
- **GA-PLS**: `plsVarSel`, em R;
- **VIP**: é fórmula fechada sobre pesos e loadings do PLS, faço direto em
  Python, sem atravessar a ponte;
- **CARS**: nenhum dos dois tem. Conferi no ambiente — o `plsVarSel`
  exporta 31 funções e nenhuma é CARS. Eu tinha escrito o contrário no
  ADR 008, sem verificar.

Segui pelo R para o iPLS e o GA-PLS, com o `rpy2` isolado atrás da
interface `Arm`, e por isso migrei o ambiente para o Linux (o `rpy2` não
funciona bem no Windows, e exigiu atualizar o R de 4.3.3 para 4.6.1). O
iPLS já está implementado e passando nos testes.

**Para o CARS, decidi e registrei no ADR 008**, em vez de trazer a escolha
solta: vou usar o `libPLS`, a biblioteca do grupo do Hongdong Li, primeiro
autor do artigo que define o CARS, com artigo próprio publicado no
*Chemometrics and Intelligent Laboratory Systems*. A alternativa seria o
`carsAlgo`, do CRAN, que se descreve como "inspired from the work of Li et
al. (2009)" — reimplementação de terceiros, que é justamente o que não
serve para o portão. O libPLS não é pacote, são arquivos soltos, então a
proveniência fica por commit fixo e `sha256`, como fiz com o tarball do
`pls` e o CSV do Mango.

**O senhor aprova o caminho em R para o iPLS e o GA-PLS?** E vê problema
em usar o libPLS para o CARS?

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

### 10. Critério de número de componentes dentro da busca de intervalos do iPLS — [trava o portão do Estágio 2]
Aberta em: 2026-09-28 (reescrita no mesmo dia — a primeira versão descrevia
o mecanismo errado)

O `PLSArm` escolhe componentes pela regra de um erro-padrão, como o senhor
apontou em 14/09 e como o artigo de referência faz (`selectNcomp` do
pacote `pls`, método `onesigma`). O `mdatools` não oferece essa regra: o
`ncomp.selcrit` dele aceita só `"min"` (o default) e `"wold"`.

O ponto é onde esse critério age. Dentro do `ipls.forward`, **cada
intervalo candidato é ajustado e pontuado com o `ncomp.selcrit`**, e o
vencedor de cada passada sai do RMSE calculado com o número de componentes
que aquele critério escolheu para aquele intervalo. Medido no Tecator
(`seed_split` 0, teto 8, 20 intervalos):

| `ncomp.selcrit` | componentes por intervalo | bandas selecionadas |
|---|---|---|
| `"min"` | 5, 5, 4, 6, 4 | 20 |
| `"wold"` | 4, 2, 3, 5, 4, 3, 3 | 30 |

Ou seja: o número de componentes varia de intervalo para intervalo, e
trocar o critério **muda quais bandas são selecionadas**.

Consequência: mesmo fixando `glob.ncomp` no valor da nossa regra de um
erro-padrão — que é o que implementei —, ele funciona só como **teto**. A
complexidade que de fato decide a seleção continua vindo do critério do
mdatools. Alinhar de verdade exigiria aplicar a regra de um erro-padrão
dentro de cada candidato de intervalo, o que significa reimplementar por
fora a busca do pacote, e aí o argumento de "usar implementação
estabelecida" se perde.

Três saídas, e não sei qual o senhor prefere:

1. aceitar o `"min"` do mdatools dentro da seleção e declarar a divergência
   como limitação, mantendo o `glob.ncomp` como teto pela nossa regra;
2. usar `"wold"`, que é menos agressivo que o mínimo puro, se o senhor o
   considerar mais próximo da regra de um erro-padrão;
3. reimplementar a busca de intervalos por fora, para que a regra seja a
   mesma em todos os braços, abrindo mão da implementação de referência.

**Resposta:**

---

### 11. O portão do Estágio 2 é executável como está escrito? — [trava o critério de aceitação do Estágio 2]
Aberta em: 2026-09-28

O pipeline põe como critério não negociável do Estágio 2: "antes de
qualquer comparação com braços neurais, reproduzir valores publicados de
RMSEP para Tecator e Gasoline com iPLS e CARS, dentro da faixa reportada
na literatura".

Fazendo a revisão dirigida, uma busca preliminar (só resumos, sem acesso
aos textos completos) sugere que esses valores talvez não existam:

- **iPLS**, Nørgaard et al. (2000): o artigo original usa um conjunto NIR
  de 60 amostras de **cerveja**, prevendo extrato original, com RMSEP de
  0,17% plato. Não usa Tecator nem Gasoline.
- **CARS**, Li et al. (2009): aplica o método a NIR de produtos
  agrícolas, **milho** entre eles. Não vi menção a Tecator nem Gasoline.
- Procurei também trabalhos de terceiros que aplicassem iPLS ou CARS a
  esses dois conjuntos e não encontrei — há RMSEP publicado para o
  Tecator por outros métodos, mas não por esses dois.

A ressalva é grande: foi busca superficial, em resumos, e ausência aí não
é prova de ausência.

Se os valores realmente não existirem, vejo três saídas e não sei qual o
senhor prefere:

1. validar a implementação nos conjuntos dos artigos originais (cerveja
   para o iPLS, milho para o CARS) — o de cerveja parece estar disponível
   em pacote R. Valida a implementação, que me parece ser o que o portão
   quer, ainda que não nos conjuntos deste trabalho;
2. continuar procurando trabalho de terceiros nesses conjuntos;
3. redefinir o portão.

Pergunto agora porque o pipeline dá quatro semanas aos braços clássicos,
e descobrir isso com os três braços prontos seria exatamente o
"descobrir em outubro e refatorar" que o senhor me alertou em 27/08.

**Resposta:**

---

### 12. Que critério deve escolher o número de intervalos do iPLS? — [trava o Estágio 2]
Aberta em: 2026-09-28

Implementei a escolha de `int.num` com a mesma regra de um erro-padrão do
PLS: entre os candidatos dentro de um erro-padrão do mínimo, fica o menor.
No PLS isso é parcimônia — menos componentes, modelo mais simples. No iPLS
**o sinal se inverte**, e eu não tinha percebido: menos intervalos
significa intervalos mais largos, logo mais bandas retidas. Medido no
Tecator, `seed_split` 0:

| `int.num` | largura | bandas selecionadas |
|---|---|---|
| 10 | 10 | 30 |
| 20 | 5 | 10 |
| 30 | 3 | 6 |

O menor `int.num` é o **menos** parcimonioso na grandeza que importa num
método de seleção, que é o número de variáveis. Nesse mesmo `seed_split` o
menor erro de CV estava em 25, a regra escolheu 10, e o R² no teste externo
caiu de 0,9710 (com 20) para 0,9415.

Não mudei nada, de propósito: trocar o critério depois de ver esses números
seria escolher regra olhando resultado. Deixei a regra atual declarada no
[ADR 012](../ADR/012-ipls-via-mdatools.md) com o defeito exposto, para o
senhor decidir entre:

1. manter como está (menor `int.num` dentro de um erro-padrão), aceitando a
   inversão como consequência declarada;
2. inverter o desempate — entre os candidatos dentro de um erro-padrão,
   ficar com o **maior** `int.num`, ou seja, o de menos bandas;
3. desempatar diretamente pelo número de bandas retidas, e não pelo número
   de intervalos;
4. argmin puro do erro de CV, sem regra de um erro-padrão neste
   hiperparâmetro.

Se a regra mudar, os números do iPLS no Tecator que registrei precisam ser
refeitos.

**Resposta:**

---

### 13. Escalonamento na seleção de intervalos do iPLS — [afeta a H5]
Aberta em: 2026-09-28

O `mdatools` pontua os intervalos com `center = TRUE, scale = FALSE`, que é
o default dele. O `PLSRegression` que ajusta o modelo final autoescala, que
é o default do scikit-learn e o que o nosso PLS (A1) usa. Então os
intervalos são escolhidos sob uma métrica e o modelo é ajustado sob outra.

Medi o tamanho do efeito no Tecator, `int.num = 20`, seis `seed_split` da
faixa exploratória:

| `seed_split` | Jaccard entre as duas seleções | R² (FALSE) | R² (TRUE) |
|---|---|---|---|
| 0 | 0,333 | 0,9710 | 0,9669 |
| 1 | 0,500 | 0,9549 | 0,9526 |
| 2 | 0,750 | 0,9735 | 0,9712 |
| 3 | 1,000 | 0,9722 | 0,9722 |
| 4 | 0,182 | 0,9685 | 0,9651 |
| 5 | 1,000 | 0,9710 | 0,9710 |

Na acurácia não muda nada — terceira casa decimal, sem vencedor
consistente. Mas o Jaccard médio entre as duas configurações é 0,63: mais
de um terço do conjunto de bandas muda só por causa dessa opção.

É isso que me preocupa. A H5 é sobre reprodutibilidade do conjunto de
bandas, medida por Jaccard. Se uma opção de escalonamento não declarada
move o Jaccard nessa magnitude, parte do que eu atribuiria ao método pode
ser efeito de um default de pacote.

Deixei `scale` como parâmetro, com o default `FALSE` do pacote preservado,
sem mudar nada. Eu defenderia alinhar o seletor ao regressor
(`scale = TRUE`), porque o intervalo deveria ser escolhido sob a mesma
geometria em que o modelo será julgado. O argumento contrário é que
`FALSE` é o default da implementação de referência, e o pipeline manda
preferir implementação estabelecida. O senhor prefere qual?

(Descartei desligar o autoescalonamento do nosso PLS no A3: aí o A3
deixaria de usar o mesmo regressor do A1, e a decomposição perderia a
propriedade de os braços diferirem por exatamente uma característica.)

**Resposta:**

---

### 14. Os ajustes do parecer de 01/10 no protocolo — [trava o congelamento e o Estágio 3]
Aberta em: 2026-10-27

O parecer de 01/10 pediu três mudanças de desenho. Elas estão no
`PROTOCOLO.md`, seção "Hipóteses e braços", como proposta. Quatro pontos
precisam do aval da orientação:

1. **H8, nova:** Δ_aprendizado = R²(B4) − R²(B2) equivalente a zero por
   TOST. A proposta não tinha hipótese para esse termo.
2. **A correção do B5:** das três que o parecer oferece, a proposta é
   escalar os logits iniciais por um fator `c < 1`, de modo que a distância
   entre os dois primeiros logits fique na ordem do que o treino consegue
   mover (~2, contra 11,5 hoje), com `c` fixado nas sementes de exploração.
3. **O braço B2':** a porta corrigida congelada, acréscimo deste trabalho,
   para que B5 e o braço com que é comparado difiram só pelo gradiente.
4. **A H6:** o parecer pede para reinterpretar a H5; a mesma leitura parece
   valer para a H6 (B4 contra B3 em reprodutibilidade), porque a vantagem
   pode vir da saturação do prior.

**Resposta:**

---

### 15. Prazo do congelamento do protocolo — [trava o congelamento]
Aberta em: 2026-10-27

O protocolo estava marcado para congelar na semana 11 (~27/10). O Estágio 2
está incompleto (só o iPLS implementado), o Estágio 3 não começou, e a
mudança de desenho do parecer ainda não foi aprovada. O prazo se mantém?

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

**Adendo (30/09/2026).** A ressalva se confirmou. Com o código-fonte do
paper, cedido em 29/09, ficou estabelecido que os resultados publicados do
Tecator foram calculados sobre a **água**: a coluna 0 do `targets.csv`,
rotulada `Fat`, contém a água. A orientação aceitou o achado em 29/09. Com
isso, "erro de prosa" e "nenhum resultado do paper está comprometido" deixam
de valer; a resposta acima fica como registro do que se sabia em 03/09. A
decisão do ADR 004 para este trabalho não muda. Ver o adendo de 30/09 no
[ADR 004](../ADR/004-proveniencia-do-tecator.md).