# ADR 014 — VIP com limiar

**Data:** 2026-10-28
**Status:** proposto

## Contexto

Segundo braço clássico do Estágio 2, depois do iPLS (ADR 012). O ADR 008
(proposto) decidiu fazer o VIP em Python, por ser fórmula fechada sobre o
PLS, sem passar pelo R. O pipeline lista o braço como `vip_threshold` e pede
que o limiar seja ajustado por validação cruzada interna, como os
hiperparâmetros dos outros braços. Também manda registrar em ADR cada decisão
que o método original deixa em aberto.

**O que foi lido e o que não foi.** Lido por inteiro: Mehmood, Sæbø e
Liland (2020), *J. Chemometrics* 34, e3226 (acesso aberto, CC BY; PDF obtido
pela CAPES em 28/10/2026). *(Nota de 06/11: o PDF não foi encontrado no
computador ao organizar os arquivos do TCC; por ser de acesso aberto, pode
ser baixado de novo.)* Não lidos, só
resumos e citações de terceiros: Wold, Johansson e Cocchi (1993), capítulo
em *3D QSAR in Drug Design*, onde o VIP é proposto; Wold, Sjöström e
Eriksson (2001), *Chemom. Intell. Lab. Syst.* 58, 109–130; Chong e Jun
(2005), *Chemom. Intell. Lab. Syst.* 78, 103–112, o estudo de simulação
sobre o corte do VIP; Mehmood, Liland, Snipen e Sæbø (2012), *Chemom.
Intell. Lab. Syst.* 118, 62–69; Farrés, Platikanov, Tsakovski e Tauler
(2015), *J. Chemometrics* 29, 528–536. **A leitura deles entra na revisão
dirigida; se algum contradisser uma escolha daqui, o ADR é corrigido antes
de qualquer execução que entre em resultado.**

O que Mehmood et al. (2020) estabelecem, com a seção ao lado:

- **Origem e nome** (Seção 3.1.3): o VIP foi introduzido por Wold, Johansson
  e Cocchi (1993) como *variable influence on projection*; o nome VIP é de
  Eriksson et al. (2001, livro da Umetrics).
- **Fórmula** (Seção 3.1.3, sobre o algoritmo da Seção 2): a mesma escrita
  na Decisão abaixo, com os *loading weights* `w_a` normalizados do PLS de
  escores ortogonais (NIPALS) e `SS_a = q_a² t_a't_a`.
- **Corte**: a variável pode ser eliminada se o VIP ficar abaixo de um
  limiar escolhido pelo usuário, e o artigo diz que é "geralmente aceito"
  selecionar quando o VIP passa de 1, citando Eriksson et al. (2001), Chong e
  Jun (2005) e Gosselin et al. (2010).
- **Ajuste do limiar** (Seção 4.3 e Tabela 2): no estudo de simulação, o
  limiar do VIP foi ajustado pelo RMSEP de validação cruzada e ficou em
  **0,90**. O artigo recomenda validação cruzada dupla para métodos de filtro
  como o VIP: o treino é dividido de novo para ajustar o parâmetro.
- **Conclusão** (Seção 6): seleção de variáveis não garante melhorar a
  predição.

O que foi conferido diretamente, além do artigo:

- **A documentação da Eigenvector** (PLS_Toolbox, página `Vip`) diz que uma
  variável com VIP "próximo de 1 ou maior" pode ser considerada importante e
  que valores bem abaixo de 1 indicam candidatas à exclusão. Ela cita Chong e
  Jun (2005) como referência e alerta que excluir em rodadas sucessivas pelo
  VIP não é bem sustentado: ao refazer o modelo, sempre aparecem novas
  variáveis abaixo do corte.
- **O código dos dois pacotes R instalados** para os outros braços (ADR 008):
  `plsVarSel::VIP` (0.10.0) e `mdatools::vipscores` (0.16.0). O manual do
  `plsVarSel` cita Mehmood et al. (2012) e (2020) e menciona "o corte de 1
  usado para o VIP"; a função `VIP` não tem argumento de limiar.
- **A medição em `scripts/verificar_vip.py`**, descrita abaixo.

## Decisão

**Fórmula.** VIP de Wold para resposta única, com os pesos `W` do PLS
(NIPALS):

```
VIP_j = sqrt( p · Σ_a SS_a (w_ja / ||w_a||)² / Σ_a SS_a ),   SS_a = q_a² · t_a't_a
```

`SS_a` é a parte da variância de y explicada pelo componente `a`. Pela
construção, a média dos VIP² é exatamente 1, e daí vem a convenção do corte
em 1: acima dele, a banda pesa mais do que a média. Conferido nos quatro
conjuntos (média 1,000000000000).

**Os dois pacotes R não calculam o mesmo VIP, e este braço segue o
`plsVarSel`.** Conferido em `scripts/verificar_vip.py`, com SNV, autoescala e
H = 5 nos quatro conjuntos:

- o `vip_scores` do projeto bate com o `plsVarSel::VIP` em todos, com
  diferença máxima de 1,3e-14 (erro de arredondamento);
- com o `mdatools::vipscores` a diferença chega a 0,22 (Tecator), 0,35
  (Gasoline), 0,86 (Mango) e 0,22 (bioprocess, 500 primeiras linhas).

A causa foi isolada num diagnóstico em rascunho, no Tecator: o `mdatools`
ajusta o PLS por SIMPLS (o `method` padrão do `mdatools::pls`) e usa os
pesos desse algoritmo, `R = W(P'W)⁻¹`. Com `R` no lugar de `W`, a fórmula do
projeto reproduz o `mdatools` até 1,6e-12. Os dois pacotes chamam de "VIP"
quantidades diferentes, e a escolha muda a seleção. Com limiar 0,8, por
exemplo:

| conjunto | bandas com VIP ≥ 0,8, pesos `W` | pesos `R` (mdatools) |
|---|---|---|
| Tecator (p = 100) | 72 | 71 |
| Gasoline (p = 401) | 339 | 200 |
| Mango (p = 281) | 200 | 155 |
| bioprocess (p = 1870) | 724 | 703 |

O braço usa `W` por quatro razões: é a fórmula escrita em Mehmood et al.
(2020), com os *loading weights* do NIPALS; é o que o código do `plsVarSel`,
dos mesmos autores, usa (`loading.weights` do pacote `pls`); é o que o
`PLSRegression` do scikit-learn, que é NIPALS, entrega diretamente; e deixa o
VIP coerente com o regressor do projeto. **Ainda não verificado no
original:** a forma escrita por Wold et al. (1993). A revisão de 2020 atribui
a fórmula a eles e a escreve com `W`, mas é fonte secundária.

**Modelo que calcula o VIP.** O mesmo `PLSRegression` do `PLSArm`, com
autoescala. Assim o seletor e o regressor trabalham na mesma geometria. No
iPLS isso não acontece, e é a pergunta 13 (ADR 012). A ressalva é que o VIP
depende do escalonamento: com autoescala, uma banda de pouca variância pesa
tanto quanto as outras.

**Número de componentes do modelo do VIP.** Regra de um erro-padrão do
`PLSArm` sobre todo o `X_train`, igual ao `glob_ncomp` do iPLS. Pelo mesmo
motivo do iPLS, esse valor agrega todas as folds, e por isso o verificador
anti-vazamento (ADR 011) roda com ele fixo (`n_components`) e com o limiar
fixo.

**Limiar.** A banda é selecionada quando `VIP ≥ limiar`, com o limite
inclusivo. Candidatos declarados a priori, iguais nos quatro conjuntos:

```
limiar ∈ {0,8; 1,0; 1,2; 1,5}
```

O 1,0 é a convenção "geralmente aceita" registrada em Mehmood et al. (2020).
O limite inclusivo segue a forma do artigo: elimina-se a variável com VIP
abaixo do limiar. A faixa inclui um valor abaixo de 1 porque, no estudo
deles, o limiar ajustado por validação cruzada ficou em 0,90, ou seja, o
ótimo não está necessariamente em 1. **Os valores 0,8, 1,2 e 1,5 em si são
escolha deste ADR**, não tirados de fonte lida; a conferir com Chong e Jun
(2005), que estudaram o corte.

**Escolha do limiar.** Regra de um erro-padrão sobre o RMSE da CV, como no
`PLSArm` e no iPLS, mas com desempate para o **maior** limiar dentro do
limite. Um limiar maior seleciona menos bandas, ou seja, dá o modelo mais
parcimonioso em variáveis. Aqui o "mais simples" é declarado no sentido
certo antes de qualquer resultado. No iPLS, o desempate pelo menor `int_num`
escolhe o modelo com mais bandas, e isso está em aberto na pergunta 12.

**Limiar que esvazia a seleção.** Se, com um limiar, algum fold fica sem
nenhuma banda, esse candidato sai da disputa. Isso só pode acontecer acima de
1: como a média dos VIP² é 1, o maior VIP é sempre pelo menos 1, então 0,8 e
1,0 nunca esvaziam. Se o limiar escolhido esvaziar a seleção no treino
inteiro, o braço falha com erro, em vez de seguir sem bandas.

**Seleção aninhada.** É a validação cruzada dupla que Mehmood et al. (2020)
recomendam para métodos de filtro. Dentro de cada fold, o VIP vem de um PLS
ajustado só em `fold_train`. Um único ajuste por fold serve aos quatro limiares, porque o
VIP não depende do limiar. `cv_selections` traz as bandas de cada fold no
limiar escolhido.

**Modelo entregue.** VIP do PLS ajustado no treino inteiro, bandas com
`VIP ≥ limiar` e o mesmo `PLSRegression` reajustado só nelas, com o número de
componentes recortado pelo que o subconjunto suporta. É o mesmo `_fit_pls`
do iPLS. O número de componentes **não** é buscado de novo depois da seleção:
assim, o A1 e este braço diferem só pelo subconjunto de bandas, como o A1 e o
iPLS. A alternativa, uma segunda busca de H sobre as bandas selecionadas,
fica registrada e não foi adotada.

**Uma passada, não eliminação em rodadas.** O braço corta uma vez. É o VIP
como método de filtro, na classificação de Mehmood et al. (2020, Seção 3.1):
ajusta-se um PLS e usa-se a saída dele para escolher as variáveis, em duas
etapas. Repetir filtro e reajuste é o que eles chamam de método *wrapper*
(Seção 3.2). A eliminação repetida pelo VIP também é a que a documentação da
Eigenvector diz ser mal sustentada, e a "limiarização de VIP" do pipeline é o
corte único.

**`band_scores`.** O VIP do modelo do treino inteiro, um valor por banda. É
o primeiro braço clássico com escore contínuo; o iPLS devolve `None`.

## Consequências

`src/tcc/arms/vip.py` (`VIPArm`, nome `vip_threshold`, e a função
`vip_scores`) e `tests/test_vip.py`. Os testes cobrem:

- média dos VIP² igual a 1;
- a fórmula vetorizada contra um laço escrito à mão;
- invariância à escala de cada `w_a`;
- o limiar inclusivo;
- o desempate pelo maior limiar, numa curva montada à mão;
- o descarte do limiar que esvazia um fold;
- a contagem de ajustes;
- o número de componentes igual ao do `PLSArm`;
- o verificador anti-vazamento do ADR 011 aplicado ao braço, junto com uma
  versão vazada (VIP calculado no treino inteiro) que o verificador
  reprova.

Cinco mutações conferidas: desempate pelo menor limiar, não descartar o
limiar vazio, não normalizar `w_a`, não pesar por `SS_a` e corte estrito.
Cada uma derruba pelo menos um teste, e o arquivo foi restaurado com o hash
conferido. Uma delas, tirar a normalização de `w_a`, só foi pega depois de um
teste novo: o scikit-learn já entrega pesos com norma 1, então nos dados reais
a mudança não aparecia.

`n_fits` é contagem exata, não estimativa como no iPLS: a busca de H do
`PLSArm`, um PLS por fold para o VIP, um por fold e por limiar na busca, o
PLS do VIP final e o PLS entregue.

**Custo medido** (`scripts/medir_custo_vip.py`, `seed_split` 0, `seed_algo`
0, busca completa). O VIP custa cerca de 1,1 vez o PLS completo em ajustes,
contra 46 a 111 vezes do iPLS (DIARIO de 28/10; o 111, do bioprocess, é
estimado):

| conjunto | PLS completo | VIP | limiar escolhido | bandas |
|---|---|---|---|---|
| Tecator | 201 ajustes | 222 ajustes | 1,2 | 16 de 100 |
| Gasoline | 176 ajustes | 202 ajustes | 1,0 | 108 de 401 |
| Mango | 201 ajustes | 227 ajustes | 0,8 | 143 de 281 |
| bioprocess | 201 ajustes | 227 ajustes | 1,2 | 345 de 1870 |

No Tecator, o limiar 1,5 esvaziou os cinco folds (o maior VIP por fold ficou
entre 1,26 e 1,30, medido em 29/10) e saiu da disputa: por isso são 15
ajustes de busca, e não 20 (200 da busca de H + 5 + 15 + 2 = 222). Os R² dessa partição única servem só para
conferir o encanamento e estão no DIARIO.

Decisão minha, não vista pela orientação. Fica como proposta até ela ver,
junto com o ADR 008, do qual este depende.

**Nota (10/11/2026): a regra de réplicas do Tecator mudou** (ADR 009; 180
grupos em vez de 208). O braço foi medido de novo no Tecator
(`seed_split` 0): limiar 1,2, 16 bandas de 100 e 222 ajustes, os mesmos
da tabela acima, com R² 0,9628, igual ao do PLS completo nessa partição.
