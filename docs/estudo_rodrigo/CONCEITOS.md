# Conceitos-base do Estágio 0

Material de estudo pessoal. Não é entregável nem parte da monografia — serve
para consulta rápida quando algum destes conceitos voltar nos estágios
seguintes.

Os três conceitos aqui não são de quimiometria. São de avaliação de modelo, e
valem para qualquer área que treine um modelo a partir de dados.

---

## 1. Treino e teste

### O problema

Temos 215 amostras de carne. Cada uma tem um espectro (100 números, a absorção
de luz em 100 comprimentos de onda) e o teor de gordura medido em laboratório.

Queremos um método que olhe o espectro e acerte a gordura. A pergunta é: como
saber se ele é bom?

A resposta ingênua seria dar as 215 amostras para o método aprender, depois
perguntar a gordura das mesmas 215 e ver quanto ele acerta. Isso não funciona.

### Por que não funciona

Imagine um método que apenas **guarda uma tabela**: amostra 1 → 22,5%,
amostra 2 → 40,1%, e assim por diante.

Perguntando a gordura de qualquer uma das 215, ele consulta a tabela e acerta
perfeitamente. Pela medida ingênua, seria o melhor método do mundo.

Mas diante de uma amostra nova, da produção de hoje, ele não acha nada na
tabela. É inútil.

### Overfitting

Quando um método guarda respostas em vez de aprender o padrão, chama-se
**overfitting** (sobreajuste).

O caso da tabela é o extremo óbvio. O perigo real é que métodos de verdade
fazem isso de forma **parcial e invisível** — um pouco de padrão real, um pouco
de decoreba. Olhando só a nota nos dados de treino, não dá para distinguir os
dois.

O risco é maior quando há muitas variáveis para pouco dado. O Tecator tem 215
amostras e 100 variáveis por amostra — situação que a proposta chama de
**n ≪ p** ("n muito menor que p"). Aí decorar é fácil.

### A solução

Separar os dados **antes** de qualquer coisa acontecer.

- **Conjunto de treino** — o método vê os espectros e as respostas certas. É
  com isso que ele aprende.
- **Conjunto de teste** — fica trancado. O método não vê o espectro nem a
  resposta. Não sabe que existe.

Depois que o método terminou de aprender, mostramos só os espectros do teste e
perguntamos a gordura. Comparamos com as respostas certas que estavam
guardadas.

O método da tabela erra tudo nesse esquema — porque nunca viu aquelas
amostras. E era isso que queríamos descobrir.

### Generalizar

É a capacidade de acertar em dado nunca visto. É a única coisa que interessa,
porque na fábrica todas as amostras são novas.

### No nosso código

`evaluate()` reserva 25% das amostras — 54 no Tecator — e essas 54 não chegam
perto do método até ele terminar de treinar. As outras 161 são o treino.

O erro medido nas 54 se chama **RMSEP**. É o número que vai para a tabela final
do TCC.

### Por que 25%

Não é regra, é escolha, e tem tensão nos dois lados:

- Teste maior → medida mais confiável, mas sobra menos para o método aprender
- Teste menor → mais dado para o treino, mas a nota fica instável

**Pendência aberta:** o paper de referência usou 20%. Precisa ser decidido antes
do protocolo congelar (semana 11), principalmente por causa do Gasoline — com
60 amostras, 25% deixaria só 15 no teste, e 15 é pouco para medir qualquer
coisa com confiança.

---

## 2. Semente (seed)

### O problema

Vamos reservar 54 amostras das 215. Quais 54?

Não pode ser "as 54 primeiras" — a ordem do arquivo pode ter padrão escondido
(amostras ordenadas por gordura, por lote de produção). Se tiver, o teste vira
um grupo enviesado.

Então sorteamos: embaralha as 215 e pega 54.

### O problema do sorteio

Sorteio dá resultado diferente a cada execução. Isso quebra duas coisas
essenciais:

**Reprodutibilidade.** O TCC precisa ser refazível. Se o professor, um revisor,
ou eu mesmo em novembro rodar o código, tem que dar o mesmo número. Com sorteio
livre, cada execução dá um resultado.

**Comparação justa.** Se o PLS pegar um sorteio e o CARS pegar outro, eles
fizeram provas diferentes. As notas não são comparáveis.

### A solução

O computador não sorteia de verdade. Ele calcula números que *parecem*
aleatórios, a partir de um valor inicial. Esse valor inicial é a **semente**
(*seed*).

Mesma semente → mesma sequência de números → mesmo sorteio, sempre.

Semente 42 hoje, semente 42 daqui a três meses, semente 42 na máquina do
revisor: as mesmas 54 amostras no teste.

É isso que torna o resultado reproduzível **e** a comparação justa — a mesma
semente vai para os doze métodos, e todos recebem a mesma partição.

### As duas sementes

Este TCC tem duas, e elas controlam sorteios diferentes.

**`seed_split`** — controla *quais amostras vão para o teste*. A divisão dos
dados.

**`seed_algo`** — controla a *aleatoriedade interna do método*. Alguns métodos
sorteiam por dentro: uma rede neural começa com pesos aleatórios; o CARS sorteia
subconjuntos de amostras a cada rodada. Rodando duas vezes com os mesmos dados,
podem dar respostas ligeiramente diferentes.

### Por que separar

Porque respondem a perguntas diferentes:

| Se variar | Descobre |
|---|---|
| `seed_split` | o método aguenta partições diferentes dos dados? |
| `seed_algo` | o método dá resposta parecida consigo mesmo? |

A primeira é sobre **generalização** — o resultado depende de quais amostras
calharam de cair no treino?

A segunda é sobre **estabilidade** — rodando duas vezes no mesmo dado, ele
concorda consigo mesmo?

A hipótese H5 é sobre isso: a porta espectral pode não ser mais precisa que o
CARS, mas talvez seja muito mais estável — escolhendo sempre as mesmas bandas,
enquanto o CARS muda a cada execução.

### Onde estava o perigo

Se as duas se misturassem, a medida vira lixo.

Para medir instabilidade, fixamos `seed_split` e variamos `seed_algo`. Se a
partição mudasse junto, o resultado diferente poderia vir de duas causas — o
método é instável, **ou** ele viu dados diferentes. E não haveria como saber
qual.

Por isso o pipeline chama isso de "a decisão mais importante do trabalho e a
mais fácil de errar".

### No nosso código

Duas garantias:

1. As duas sementes alimentam geradores independentes (`SeedSequence.spawn`).
   Mexer numa não afeta a outra.
2. O método **nunca recebe** `seed_split`. Só recebe a aleatoriedade derivada
   de `seed_algo`. Sem acesso, não pode depender dela nem por acidente.

O `RandomArm` nos testes existe para verificar isso — é a correção do achado
crítico da auditoria de 25/08.

---

## 3. Validação cruzada

### O problema

O PLS fabrica variáveis novas a partir das 100 bandas — os componentes
latentes. Ele precisa decidir **quantos usar**. Cinco? Dez? Quinze?

- Poucos demais: não captura o suficiente, erra muito.
- Muitos demais: começa a decorar. Overfitting de novo.

Esse número é um **hiperparâmetro** — uma configuração do método, escolhida
antes dele treinar. Cada método tem os seus: o iPLS escolhe quantos intervalos,
o CARS quantas iterações, o VIP o limiar de corte.

### Onde testar as opções

**No teste?** Proibido. Usar as 54 amostras guardadas para escolher o número de
componentes faz com que elas deixem de ser dado nunca visto. A medida final
fica contaminada.

**No treino?** Não funciona. Mais componentes sempre acerta mais no próprio
treino — escolheríamos sempre o máximo, que é justamente o caso de decoreba.

Precisamos de um terceiro lugar. E ele sai de dentro do próprio treino.

### A ideia

Pega as 161 amostras de treino e corta em 5 pedaços. Cada pedaço é uma **fold**.

Depois, 5 rodadas:

```
rodada 1:  treina em 2,3,4,5   →  avalia no 1
rodada 2:  treina em 1,3,4,5   →  avalia no 2
rodada 3:  treina em 1,2,4,5   →  avalia no 3
rodada 4:  treina em 1,2,3,5   →  avalia no 4
rodada 5:  treina em 1,2,3,4   →  avalia no 5
```

Cada pedaço serve de avaliação exatamente uma vez, e de treino nas outras
quatro.

No fim, 5 notas. A média delas é o desempenho daquela configuração.

Repete tudo para cada opção (5 componentes, 10, 15...) e fica com a que teve a
melhor média.

### Por que "cruzada"

Porque os papéis se revezam. Cada pedaço é ora treino, ora avaliação. Os papéis
cruzam.

### Por que "interna"

Porque acontece **dentro do treino**. As 54 amostras do teste externo não
participam de nada disso — continuam trancadas.

### Os dois erros

Daí os dois nomes no `Result`:

| | Onde nasce | Serve para |
|---|---|---|
| `rmse_cv` | na CV interna, dentro do treino | o método escolher sua configuração |
| `rmsep` | no teste externo | comparar os 12 métodos |

O `rmse_cv` é número de bastidor. O `rmsep` é o número do TCC.

### Quem gera as folds

**A `evaluate()`, não o método.** Ela corta o treino em 5 pedaços e entrega
prontos.

Dois motivos:

1. Todos os doze métodos ensaiam sobre exatamente os mesmos pedaços. Justiça.
2. As folds derivam de `seed_split`. Assim, ao variar `seed_algo` para medir
   instabilidade, os pedaços não mudam junto — e a medida fica limpa.

Está registrado no ADR 001.

### O MeanArm

Ignora as folds completamente, porque não tem hiperparâmetro nenhum para
escolher. Chuta a média e pronto. Por isso o `rmse_cv` dele volta como `nan` —
"não se aplica".

---

## Resumo em uma frase cada

- **Treino e teste:** guardar uma parte dos dados para medir se o método
  acerta em amostra que nunca viu.
- **Semente:** o número que fixa o sorteio, para o resultado ser reproduzível e
  a comparação justa. Aqui são duas, controlando sorteios diferentes que não
  podem se misturar.
- **Validação cruzada:** revezar pedaços do treino para o método escolher sua
  própria configuração sem tocar no teste externo.
