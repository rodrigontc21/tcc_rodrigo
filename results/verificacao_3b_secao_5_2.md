# Verificação 3, parte B — o que muda na Seção 5.2, na Fig. 1 e no argumento de interpretabilidade

*Rodrigo Fernandes — 27/10/2026; leitura do deslocamento da porta corrigida em 04/11/2026; Gasoline medido em 05/11/2026*

> **O que foi pedido:** …E atinge a Seção 5.2, que é o argumento central de interpretabilidade. […] Isso precisa ser reformulado, não só corrigido. […] Rode o pipeline completo com a coluna correta — PGSG inclusive, não só o PLS — para saber a extensão do que muda antes de escrever para o texto.

### Resposta curta

**Na Seção 5.2, o alvo correto praticamente não muda nada** — a banda de
931 nm continua sendo a de maior peso, com quase o mesmo peso (0,215 na
água, 0,217 na gordura). Mas a razão de não mudar é que
**os valores publicados correspondem às portas da inicialização**: um modelo
sem nenhum passo de treino os reproduz em todas as sementes, nos dois
conjuntos. Com o protocolo que o artigo declara (lr 0,01, 200 épocas,
paciência 30), quatro dos oito valores não são alcançados em nenhuma das 10
sementes testadas — a correlação com o prior e a região C–H no Tecator, o
peso e a correlação no Gasoline —, e os outros quatro são compatíveis com o
treino. Treino muito curto,
ou com *learning rate* cem vezes menor, chega a 0,001–0,002 do publicado,
mas não o reproduz de forma consistente. E o script do repositório que gera
esses números não treina.

O mesmo argumento — a correlação moderada com o prior como prova de
aprendizado — está também no **resumo**, na **conclusão** e na **Seção
3.4**, onde se apoia numa busca em grade do peso do KL cujas afirmações não
se reproduzem.

### O que muda com o alvo correto: quase nada

| | água (o que foi publicado) | gordura |
|---|---|---|
| banda de maior peso | 931 nm | 931 nm |
| peso | 0,215 | 0,217 |
| correlação com o prior | 0,348 | 0,353 |

A frase do texto — 931 nm corresponde ao estiramento C–H, ligado à gordura —
sobrevive à troca do alvo. Mas sobrevive por um motivo que a esvazia: a banda
não foi escolhida pelo modelo nem pelo alvo.

### Por que quase nada muda: os valores correspondem à inicialização

As portas de um modelo **sem um único passo de treino** reproduzem os valores
publicados, nos dois conjuntos:

| | sem treinar | depois de treinar | publicado |
|---|---|---|---|
| Tecator, banda de maior peso | 931 nm | 931 nm | 931 nm |
| Tecator, peso | **0,215** | 0,219 | **0,215** |
| Tecator, correlação com o prior | **0,348** | 0,335 | **0,348** |
| Tecator, região C–H | **7,39%** | 7,21% | **7,4%** |
| Tecator, região O–H | **3,54%** | 3,54% | **3,5%** |
| Gasoline, banda de maior peso | 154 | 154 | 154 |
| Gasoline, peso | **0,130** | 0,107 | **0,130** |
| Gasoline, correlação com o prior | **0,507** | 0,495 | **0,507** |

Oito valores, comparados na precisão em que foram publicados. **O modelo
não treinado bate em todos.** A coluna "depois de treinar" é de uma semente
só, e o pipeline original não fixa semente; por isso a comparação que vale
é a de dez sementes, valor a valor (segundo anexo do relatório 3,
`scripts/verificar_divergencia_redes.py`):

| valor publicado | treinado, 10 sementes | reproduz em |
|---|---|---|
| Tecator, banda de maior peso: 931 nm | 931 nm em todas | 10 de 10 |
| Tecator, peso: 0,215 | 0,213 a 0,219 | 3 de 10 |
| Tecator, região O–H: 3,5% | 3,5% a 3,6% | 5 de 10 |
| Gasoline, banda de maior peso: 154 | 154 em todas | 10 de 10 |
| **Tecator, correlação com o prior: 0,348** | 0,332 a 0,340 | **0 de 10** |
| **Tecator, região C–H: 7,4%** | 7,2% a 7,3% | **0 de 10** |
| **Gasoline, peso: 0,130** | 0,102 a 0,110 | **0 de 10** |
| **Gasoline, correlação com o prior: 0,507** | 0,487 a 0,500 | **0 de 10** |

Quatro valores são compatíveis com o treino declarado; **quatro são
excluídos por ele**, e o modelo não treinado reproduz os oito. Uma versão
anterior deste relatório dizia que o treino não reproduz nenhum dos oito e
contava a região C–H como compatível, por uma tolerância frouxa; as duas
coisas foram corrigidas a partir da reprodução da orientação, em 01/10.

Isso é coerente com o código: o `scripts/analyze_gates.py` cria um modelo
novo e lê as portas. Não há `torch.load` ali, e nenhum script do pipeline do
Tecator chama `torch.save` — não existe modelo treinado para carregar.

### Quanto treino ainda reproduz o publicado?

Para não afirmar mais do que a medida sustenta, o treino foi varrido em
épocas, *learning rate* e peso do KL, em 10 sementes, com o desenho e o
critério fixados antes de rodar (`scripts/verificar_varredura_treino.py`,
segundo anexo). "Reproduz" quer dizer: peso da maior porta **e** correlação
com o prior iguais ao publicado na terceira casa decimal, que é a precisão
publicada. Quantas das 10 sementes reproduzem:

| condição | Tecator | Gasoline |
|---|---|---|
| sem treino (0 épocas) | **10 de 10** | **10 de 10** |
| 1 a 5 épocas, lr 0,01, sem parada | 1 a 3 de 10 | 0 a 1 de 10 |
| 10 épocas ou mais, lr 0,01 | 0 de 10 | 0 de 10 |
| protocolo do artigo com lr 1e-4 (cem vezes menor) | 4 de 10 | 0 de 10 |
| protocolo do artigo com lr 3e-4 a 3e-3 | 0 de 10 | 0 de 10 |
| **protocolo do artigo** (lr 0,01, 200 épocas, paciência 30) | **0 de 10** | **0 de 10** |
| protocolo do artigo com KL de 0 a 10 | 0 de 10 | 0 de 10 |

Treino muito curto, ou com lr cem vezes menor, deixa as portas a 0,001–0,002
do publicado — praticamente iguais à inicialização —, e às vezes bate na
terceira casa. Só a inicialização bate em todas as sementes, nos dois
conjuntos. O peso do KL não aproxima: aumentá-lo puxa a correlação para
cima e o peso da maior porta para baixo, e nenhum valor testado reproduz.

**Consequência para o texto.** A legenda da Fig. 1 afirma que a correlação
moderada com o prior "*confirms genuine data-driven refinement rather than
mere reproduction of initialization*". Os valores publicados correspondem à
inicialização; com o protocolo declarado, a correlação treinada fica entre
0,332 e 0,340, e não em 0,348. A Seção 5.2 constrói o mesmo argumento a
partir do valor 0,348.

### O mecanismo: o pico vem da normalização do prior

O prior é normalizado por mínimo e máximo, então o **máximo vale exatamente
1**. O `clip(1 − 1e-7)` antes do logit manda esse valor para 16,12. A banda
vizinha, com 1% menos de prior, fica em 4,65:

| banda | prior | logit | porta |
|---|---|---|---|
| 40 (931 nm) | 1,000000 | 16,12 | **0,2148** |
| 39 (929 nm) | 0,990542 | 4,65 | 0,0217 |
| 41 (933 nm) | 0,975696 | 3,69 | 0,0179 |

Porta dez vezes maior por 1% de diferença no prior. O "*dramatic sharpening
of the peak at 931 nm*" que o texto atribui ao aprendizado é consequência
mecânica de `(p − mín)/(máx − mín)` → `clip` → `logit`. O mesmo mecanismo
produz o vale em 862 nm visível na figura, onde o prior mínimo vira −16,12.

**E é isso que impede o treino de mexer no topo.** No Tecator a banda
campeã começa 11,5 logits à frente da segunda; no protocolo do artigo, o
maior deslocamento de um logit em 10 sementes fica entre 1,45 e 1,92, e a
distância entre os dois primeiros termina entre 11,4 e 11,6. No Gasoline:
12,2 de distância inicial, deslocamento máximo de 1,22 a 1,79. O topo não
tem como mudar. As posições
de baixo, onde os logits estão próximos, reordenam — e é isso que a
estabilidade entre folds mede.

**Correção (04/11): o deslocamento de 1,45 a 1,92 é, na maior parte,
decaimento de peso, e não aprendizado.** O `train_light.py` passa
`model.parameters()` ao Adam com `weight_decay=1e-4`, e isso inclui os
logits da porta. L2 num logit puxa para zero, o que no softmax é puxar a
porta para o uniforme. A orientação mediu o efeito em 30/10
(`verify_wd_on_gate.py`), e eu repeti a medida nesta máquina, com duas
execuções idênticas. Tecator, protocolo do artigo, 10 sementes, mediana
[mínimo; máximo]:

| decaimento | maior deslocamento, água | maior deslocamento, gordura |
|---|---|---|
| 1e-4 em tudo (o do artigo) | 1,69 [1,45; 1,92] | 1,65 [1,56; 1,93] |
| nenhum | 0,24 [0,21; 0,32] | 0,25 [0,18; 0,31] |
| 1e-4 só no MLP, porta isenta | 0,28 [0,19; 0,32] | 0,30 [0,26; 0,36] |

Duas estatísticas por semente mostram a direção do movimento:
- a fração de bandas cujo |logit| diminuiu;
- a correlação entre o deslocamento e −θ inicial.

Encolhimento puro levaria as duas a 1. Com o decaimento do artigo, as
medianas ficam em 0,765 e 0,806 na água e em 0,750 e 0,810 na gordura. Com
a porta isenta, caem para 0,610 e 0,403 na água e 0,625 e 0,435 na gordura.

A orientação mediu:
- **direção:** 76% e 0,81 com o decaimento do artigo, ~60% e ~0,40 com a
  porta isenta. São os mesmos números daqui.
- **deslocamento máximo**, água e gordura: 1,81 e 1,69 com o decaimento do
  artigo, 0,27 e 0,30 com a porta isenta. São próximos dos daqui, mas não
  iguais.

A saída completa está no quarto anexo.

Com a porta isenta de L2, o movimento é cerca de seis vezes menor: uns 0,3
logit, contra 11,5 entre a primeira e a segunda banda. A frase "o treino
move a porta em até 1,45 a 1,92" estava errada. A conclusão acima, de que o
topo não tem como mudar, sai mais forte: o topo é ainda mais imóvel do que
aquele número sugeria.

**No Gasoline (medido em 05/11) o quadro é outro.** Para medir, usei
`scripts/verificar_decaimento_porta.py`, com a mesma receita e as mesmas
medidas da orientação, em duas execuções idênticas. O Tecator entra como
controle e reproduz os números acima. Gasoline, 10 sementes, mediana
[mínimo; máximo]:

| decaimento | maior deslocamento | fração encolhida | correlação com −θ inicial | distância 1º-2º no fim | R² de teste |
|---|---|---|---|---|---|
| 1e-4 em tudo (o do artigo) | 1,34 [1,22; 1,79] | 0,995 | 0,724 | 12,57 | 0,945 |
| nenhum | 0,61 [0,40; 0,85] | 0,213 | −0,172 | 12,20 | 0,943 |
| 1e-4 só no MLP, porta isenta | 0,66 [0,49; 0,84] | 0,217 | −0,161 | 12,20 | 0,945 |

Distância inicial entre os dois primeiros logits: 12,21.

- **O encolhimento é cerca de metade do deslocamento,** não a maior parte.
  Com a porta isenta, o maior deslocamento cai de 1,34 para 0,66.
- **A direção se inverte quando a porta fica isenta.** Com o decaimento do
  artigo, 99,5% das bandas terminam com |logit| menor. Com a porta isenta,
  só cerca de 22% terminam assim, e a correlação com −θ inicial fica
  negativa. Ou seja, a maioria das bandas se afasta de zero.
- **O topo continua imóvel nos três casos:** 0,66 logit no máximo, contra
  uma distância de 12,2.
- **O R² praticamente não muda com o decaimento,** ao contrário do
  Tecator, onde sem decaimento nenhum ele cai para 0,644.

O que essa diferença entre os dois conjuntos significa, eu não medi. A
saída completa está no quinto anexo.

Com a porta isenta, o R² de teste não piora: 0,913 na água e 0,941 na
gordura, contra 0,922 e 0,922 com o decaimento do artigo. Sem decaimento
nenhum, cai para 0,644 e 0,244. O decaimento importa para o MLP, não para a
porta.

### Item por item do texto publicado

**Confere:**

- "*highest gate weight (0.215) at 931 nm*" — sim, na inicialização.
- "*7.4% in the C–H region*" e "*3.5% in the O–H region*" — 7,39% e 3,54%.
- "*correlation … was 0.348*" (Tecator) e "*0.507*" (Gasoline) — exatos.
- "*top 20 … spanning bands 150–168*" (Gasoline) — **19 das 20** estão nesse
  intervalo, e são contíguas. A vigésima é a banda 261.

**Não confere:**

- "*the top ten selected bands span the region from 921 nm to 935 nm,
  collectively accounting for 7.4% of the total gate weight*" — as dez
  maiores vão de **923 a 1046 nm** e somam **34,4%**. O 7,4% é o peso da
  região C–H, não o das dez maiores: o texto atribui a uma coisa o número da
  outra. Duas das dez ficam perto de 1045 nm, no pico secundário que a própria
  legenda da Fig. 1 menciona.

**Compatível, mas sem valor típico:**

- "*8 of the top-10 bands appeared consistently in the top-10 selections of
  all 5 folds*" — em dez
  sementes, o número vai de **7 a 10** (`9, 8, 7, 8, 9, 10, 9, 10, 10, 8`),
  com mediana 9; o 8 publicado aparece em 3 das 10. É um valor possível, não
  o típico: com as cinco primeiras sementes a mediana seria 8, com as dez é
  9. E a estabilidade não é evidência de aprendizado — as cinco folds partem
  da mesma inicialização, calculada sobre o treino inteiro.

**Depende da leitura:**

A ablação de bandas não tem código no repositório, e "*zeroing out*" admite
duas leituras. A segunda tem ainda uma escolha que o texto não fixa: o
**prior das bandas removidas**. Mantido, a porta continua pondo ~21% do peso
na banda 931, cuja entrada agora é zero, e o treino não consegue redistribuir
esse peso. Zerado, a porta já nasce sem elas. Mediana e faixa em dez
sementes:

| leitura | dez maiores | dez ao acaso |
|---|---|---|
| zerar a entrada só na avaliação | −17,3 [−19,3; −15,6] | 0,00 [−0,39; 0,42] |
| retreinar, **mesmo prior** | 0,35 [0,18; 0,53] | 0,85 [0,73; 0,88] |
| retreinar, **prior zerado** nessas bandas | 0,63 [0,28; 0,72] | 0,86 [0,78; 0,88] |
| publicado | 0,431 | 0,794 |

A primeira leitura fica longe. As duas variantes da segunda ficam na
vizinhança — o publicado cai dentro da faixa de ambas —, e a escolha do prior
move bastante o resultado das dez maiores. Sem o código, não dá para dizer
qual foi a do artigo. **Em todas, a conclusão qualitativa se mantém:** remover
as bandas de maior peso derruba mais do que remover dez ao acaso.

### As figuras

- **Fig. 1** — a curva publicada é visualmente idêntica à inicialização,
  inclusive no vale de 862 nm. Isso **não** é usado como evidência: a curva
  de um modelo treinado no protocolo do artigo (pico entre 0,213 e 0,219)
  também seria visualmente igual, e a comparação não foi medida ponto a
  ponto. A evidência está nos valores da Tabela 2, acima.
- **Figs. 2 e 3** — são desenhadas de constantes escritas no próprio script
  (`scripts/create_main_figures.py:25-26`: `tecator_r2 = [0.919, 0.862,
  0.235]`). Batem com as tabelas por construção. Se as tabelas mudarem, as
  figuras precisam ser regeradas.

### A Seção 3.4 apoia o mesmo argumento numa busca em grade

A Seção 3.4 (`manuscript_R2.tex:267`, também no PDF publicado) diz que o
peso do KL, λ = 0,001, foi escolhido por busca em grade sobre {1e-4, 1e-3,
1e-2, 1e-1} numa fold de validação do Tecator, e afirma três coisas: com
λ = 0,001 a correlação com o prior fica em 0,35–0,51; com **λ ≥ 0,01 as
portas "colapsam para o prior" (r > 0,85)**; com **λ ≤ 1e-4 ficam
"indistinguíveis da inicialização aleatória"**.

Não há script dessa busca no repositório. Refeita com a grade do artigo e o
protocolo que o texto descreve — treino em quatro folds e validação na
quinta, folds do `cross_validate.py`, receita do `train_light.py` —, cada
fold como validação uma vez, em 10 sementes: 50 treinos por λ (terceiro
anexo, `scripts/verificar_kl_secao34.py`).

| λ | correlação com o prior, mediana [faixa] | r > 0,85 |
|---|---|---|
| 1e-4 | 0,337 [0,331; 0,348] | 0 de 50 |
| 1e-3 (o escolhido) | 0,337 [0,333; 0,342] | 0 de 50 |
| 1e-2 | 0,338 [0,333; 0,342] | 0 de 50 |
| 1e-1 | 0,347 [0,344; 0,351] | 0 de 50 |
| inicialização aleatória | 0,317 [0,173; 0,498] | 0 de 50 |

Nenhuma das três afirmações se reproduz. Nessa grade o λ praticamente não
move as portas: não há colapso para o prior em nenhum treino, e com
λ = 1e-4 as portas continuam onde a inicialização as pôs — agrupadas em
torno de 0,337, enquanto as da inicialização aleatória se espalham de 0,17
a 0,50. É coerente com o mecanismo acima. O passo do Adam tem a ordem do
*learning rate* qualquer que seja a escala da perda, então em 200 passos de
lr 0,01 cada logit anda no máximo cerca de 2. Isso foi medido no λ do artigo
(maior deslocamento de 1,45 a 1,92); para os outros λ é a mesma conta, não
uma medida. **Correção (04/11):** esse deslocamento é, na maior parte,
encolhimento pelo decaimento de peso. Com a porta isenta, cai para cerca de
0,3 (ver "O mecanismo", acima). O limite de cerca de 2 pelo passo do Adam
continua valendo como teto.

**Leitura de código, não medida:** o texto trata o prior como distribuição
de probabilidade ("*both g and s can be interpreted as probability mass
functions*"), mas o `band_select_net_light.py` usa os escores min-max
recortados diretamente como `prior_probs`, sem normalizar a soma para 1. O
termo que o código minimiza não é, portanto, a divergência KL da equação do
texto.

### Onde mais a afirmação aparece

No próprio artigo, além da Seção 5.2 e da Seção 3.4: o **resumo**
(`manuscript_R2.tex:139`: "*The moderate correlation between learned gates
and chemometric priors (0.35–0.51) confirms that the model refines domain
knowledge with data-driven learning rather than merely reproducing
initialization*") e a **conclusão** (linha 526, a mesma frase). As duas
estão no PDF publicado.

Fora do artigo: `submission_package/highlights.txt` ("correlation
0.35-0.51 with priors"), `cover_letter.txt` ("Tecator (931nm) corresponds
precisely to C-H absorption for fat content"), `paper_complete.txt` (a mesma Tabela 2) e
`revision_r2/pgsg_1_R2.tex:358`, que é de outro artigo mas herda a frase.

### Ressalvas

1. Que os valores publicados correspondam à inicialização é sustentado por
   **duas evidências de naturezas diferentes**: o código, que não carrega
   modelo treinado, e a medida — o não treinado bate nos oito valores em
   todas as sementes, o protocolo declarado não alcança quatro deles em
   nenhuma, e nenhuma variação de treino testada reproduz de forma
   consistente.
   Nenhuma sozinha bastaria. O que a medida **não** exclui é um treino
   diferente de todos os testados; por isso a afirmação é "corresponde à
   inicialização", e não "não houve treino".
2. A ablação, a estabilidade, as portas treinadas e a varredura de treino
   foram medidas em dez sementes. O pipeline original não fixa semente,
   então valores únicos não seriam comparáveis.
3. Isto **não** demonstra que a banda de 931 nm seja irrelevante. Ela é o
   máximo do ANOVA nos dois alvos, e a região C–H é quimicamente pertinente.
   O que a medida mostra é que a seleção vem do prior, não do treino.

---

## Anexo 1 — saída de `scripts/verificar_secao52_pgsg.py`

Reproduzível com:

```bash
python scripts/verificar_secao52_pgsg.py
```

```

==============================================================================
 TECATOR - FIG. 1 E SECAO 5.2, NAS DUAS CONDICOES
==============================================================================

   Computing ANOVA F-statistic...
  SEM TREINAR (a inicializacao)
  banda de maior peso (nm)                     medido  930.808   publicado 931.000   ok
  peso dessa banda                             medido    0.215   publicado   0.215   ok
  correlacao com o prior ANOVA                 medido    0.348   publicado   0.348   ok
  peso na regiao C-H, 920-930 nm (%)           medido    7.389   publicado   7.400   ok
  peso na regiao O-H, 965-975 nm (%)           medido    3.536   publicado   3.500   ok
  faixa das 10 maiores (nm)                    medido 923-1046     publicado 921-935
  peso somado das 10 maiores (%)               medido   34.429   publicado    7.4

  DEPOIS DE TREINAR
  banda de maior peso (nm)                     medido  930.808   publicado 931.000   ok
  peso dessa banda                             medido    0.219   publicado   0.215   DIFERE
  correlacao com o prior ANOVA                 medido    0.335   publicado   0.348   DIFERE
  peso na regiao C-H, 920-930 nm (%)           medido    7.213   publicado   7.400   DIFERE
  peso na regiao O-H, 965-975 nm (%)           medido    3.535   publicado   3.500   ok
  faixa das 10 maiores (nm)                    medido 923-1046     publicado 921-935
  peso somado das 10 maiores (%)               medido   34.576   publicado    7.4

  O PICO, SEM TREINAR: prior, logit e porta em volta de 931 nm
    banda 39 (929 nm)   prior 0.990542   logit   4.65   porta 0.0217
    banda 40 (931 nm)   prior 1.000000   logit  16.12   porta 0.2148
    banda 41 (933 nm)   prior 0.975696   logit   3.69   porta 0.0179
    prior minimo: banda 6 (862 nm), logit -16.12
    maior peso: porta inicial 0.215; prior bruto normalizado para somar 1 0.024

  DEPOIS DE TREINAR, 10 sementes
  peso da banda de maior peso                  faixa [0.213; 0.219]   publicado 0.215
  correlacao com o prior ANOVA                 faixa [0.332; 0.340]   publicado 0.348


==============================================================================
 GASOLINE - SECAO 5.2, LINHA 483
==============================================================================

   Computing ANOVA F-statistic...
  SEM TREINAR (a inicializacao)
  indice da banda de maior peso                medido  154.000   publicado 154.000   ok
  peso dessa banda                             medido    0.130   publicado   0.130   ok
  correlacao com o prior ANOVA                 medido    0.507   publicado   0.507   ok
  janela das 20 maiores                        medido 150-261      publicado 150-168
    quantas caem em 150-168                    19 de 20
    as que ficam fora                          [261]
    as 19 de dentro sao contiguas?             sim

  DEPOIS DE TREINAR
  indice da banda de maior peso                medido  154.000   publicado 154.000   ok
  peso dessa banda                             medido    0.107   publicado   0.130   DIFERE
  correlacao com o prior ANOVA                 medido    0.495   publicado   0.507   DIFERE
  janela das 20 maiores                        medido 150-261      publicado 150-168
    quantas caem em 150-168                    19 de 20
    as que ficam fora                          [261]
    as 19 de dentro sao contiguas?             sim

  DEPOIS DE TREINAR, 10 sementes
  peso da banda de maior peso                  faixa [0.102; 0.110]   publicado 0.130
  correlacao com o prior ANOVA                 faixa [0.487; 0.500]   publicado 0.507


==============================================================================
 ABLACAO DE BANDAS E ESTABILIDADE ENTRE FOLDS - LINHA 485
==============================================================================

  O artigo diz: 5-fold R2 0.862; zerando as 10 bandas de maior
  peso cai para 0.431; zerando 10 bandas ao acaso (20 sorteios)
  cai para 0.794. E 8 das 10 maiores aparecem nas 10 maiores das
  cinco folds.

  Nao existe script para isso no repositorio; refeito aqui sobre o
  mesmo protocolo do cross_validate.py.

  A descricao e ambigua: 'zeroing out' pode ser zerar a entrada na
  avaliacao, ou retreinar sem aquelas bandas. As DUAS leituras sao
  medidas abaixo, em varias sementes.

  E a leitura (ii) tem uma escolha que o texto nao fixa: o prior das
  bandas removidas. Mantido, a porta continua pondo ~21% do peso na
  banda 931, cuja entrada agora e zero, e o treino nao consegue
  redistribuir esse peso (o topo e imovel). Zerado, a porta ja nasce
  sem essas bandas. As duas variantes sao medidas, com os mesmos
  sorteios de bandas.

    semente 0 ok
    semente 1 ok
    semente 2 ok
    semente 3 ok
    semente 4 ok
    semente 5 ok
    semente 6 ok
    semente 7 ok
    semente 8 ok
    semente 9 ok

  R2 5-fold sem ablacao, 10 sementes:
       mediana    0.869  faixa [0.822; 0.894]   publicado 0.862

  leitura (i) - zerar a entrada so na avaliacao:
    as 10 de maior peso:
       mediana  -17.348  faixa [-19.282; -15.587]   publicado 0.431
    10 ao acaso:
       mediana    0.003  faixa [-0.386; 0.423]   publicado 0.794

  leitura (ii-a) - retreinar com aquelas bandas zeradas, MESMO prior:
    as 10 de maior peso:
       mediana    0.351  faixa [0.176; 0.526]   publicado 0.431
    10 ao acaso:
       mediana    0.849  faixa [0.729; 0.875]   publicado 0.794

  leitura (ii-b) - retreinar com aquelas bandas zeradas, prior
                   delas tambem zerado:
    as 10 de maior peso:
       mediana    0.631  faixa [0.283; 0.723]   publicado 0.431
    10 ao acaso:
       mediana    0.864  faixa [0.775; 0.876]   publicado 0.794

  -> a leitura (i) fica longe do publicado; as duas variantes da (ii)
     ficam na vizinhanca, e a escolha do prior move o resultado das
     10 de maior peso. Sem codigo no repositorio nao da para decidir
     qual foi a do artigo. Em todas, a conclusao qualitativa se
     mantem: tirar as bandas de maior peso derruba mais do que tirar
     10 ao acaso.

  bandas presentes nas 10 maiores das CINCO folds, por semente:
    [9, 8, 7, 8, 9, 10, 9, 10, 10, 8]   publicado 8
    mediana 9, faixa [7; 10]
    o 8 publicado aparece em 3 de 10
    com as 5 primeiras sementes a mediana seria 8: o numero depende de quantas se rodam,
    e o que a medida sustenta e a faixa, nao um valor tipico.

  nota: o prior e calculado uma vez sobre os 172 do treino e serve
  de inicializacao nas cinco folds, entao as cinco partem do mesmo
  ponto. A medida acima mostra que o treino AINDA ASSIM reordena o
  fim da lista - as 10 maiores nao sao identicas nas cinco folds.
  Ou seja: o topo e imovel, mas as posicoes de baixo, onde os
  logits estao proximos, se mexem. A estabilidade publicada nao e
  evidencia de aprendizado; e o que se espera de cinco modelos que
  partem da mesma inicializacao.
```

## Anexo 2 — saída de `scripts/verificar_varredura_treino.py`

Reproduzível com:

```bash
python scripts/verificar_varredura_treino.py
```

```
   Computing ANOVA F-statistic...

==============================================================================
 TECATOR - publicado: peso 0.215, corr 0.348
==============================================================================

  mediana [minimo; maximo] em 10 sementes. 'reproduz' = peso E
  corr iguais ao publicado na 3a casa.

  GRADE A - epocas fixas, sem parada, lr 0.01, KL 0.001
  0 epocas     peso 0.215 [0.215; 0.215]   corr 0.348 [0.348; 0.348]   reproduz em 10/10
  1 epocas     peso 0.214 [0.214; 0.215]   corr 0.348 [0.348; 0.349]   reproduz em  1/10
  2 epocas     peso 0.214 [0.214; 0.216]   corr 0.349 [0.347; 0.349]   reproduz em  1/10
  5 epocas     peso 0.214 [0.213; 0.217]   corr 0.349 [0.347; 0.350]   reproduz em  3/10
  10 epocas    peso 0.214 [0.212; 0.217]   corr 0.348 [0.346; 0.350]   reproduz em  0/10
  20 epocas    peso 0.214 [0.212; 0.218]   corr 0.347 [0.344; 0.350]   reproduz em  0/10
  50 epocas    peso 0.214 [0.212; 0.218]   corr 0.345 [0.342; 0.347]   reproduz em  0/10
  100 epocas   peso 0.215 [0.213; 0.218]   corr 0.342 [0.338; 0.344]   reproduz em  0/10
  200 epocas   peso 0.215 [0.213; 0.220]   corr 0.336 [0.332; 0.339]   reproduz em  0/10

  GRADE B - lr, 200 epocas, paciencia 30, KL 0.001
  lr 0.0001    peso 0.214 [0.214; 0.215]   corr 0.348 [0.348; 0.349]   reproduz em  4/10
  lr 0.0003    peso 0.214 [0.214; 0.214]   corr 0.348 [0.348; 0.349]   reproduz em  0/10
  lr 0.001     peso 0.214 [0.213; 0.215]   corr 0.347 [0.346; 0.348]   reproduz em  0/10
  lr 0.003     peso 0.214 [0.213; 0.215]   corr 0.346 [0.344; 0.347]   reproduz em  0/10
  lr 0.01      peso 0.215 [0.213; 0.219]   corr 0.337 [0.332; 0.340]   reproduz em  0/10

  GRADE C - peso do KL, 200 epocas, paciencia 30, lr 0.01
  KL 0         peso 0.215 [0.214; 0.219]   corr 0.338 [0.333; 0.340]   reproduz em  0/10
  KL 0.001     peso 0.215 [0.213; 0.219]   corr 0.337 [0.332; 0.340]   reproduz em  0/10
  KL 0.01      peso 0.215 [0.213; 0.218]   corr 0.338 [0.334; 0.342]   reproduz em  0/10
  KL 0.1       peso 0.208 [0.206; 0.212]   corr 0.347 [0.344; 0.350]   reproduz em  0/10
  KL 1         peso 0.166 [0.157; 0.173]   corr 0.429 [0.414; 0.447]   reproduz em  0/10
  KL 10        peso 0.141 [0.130; 0.146]   corr 0.487 [0.476; 0.525]   reproduz em  0/10

  LOGITS NO PROTOCOLO DO ARTIGO (lr 0.01, 200 ep, pac. 30, KL 0.001)
  maior deslocamento de uma banda   mediana 1.69  faixa [1.45; 1.92]
  distancia 1o-2o logit, inicio     11.47 a 11.47
  distancia 1o-2o logit, fim        11.41 a 11.57
   Computing ANOVA F-statistic...

==============================================================================
 GASOLINE - publicado: peso 0.13, corr 0.507
==============================================================================

  mediana [minimo; maximo] em 10 sementes. 'reproduz' = peso E
  corr iguais ao publicado na 3a casa.

  GRADE A - epocas fixas, sem parada, lr 0.01, KL 0.001
  0 epocas     peso 0.130 [0.130; 0.130]   corr 0.507 [0.507; 0.507]   reproduz em 10/10
  1 epocas     peso 0.129 [0.129; 0.130]   corr 0.507 [0.506; 0.507]   reproduz em  0/10
  2 epocas     peso 0.130 [0.129; 0.130]   corr 0.507 [0.506; 0.507]   reproduz em  1/10
  5 epocas     peso 0.130 [0.128; 0.130]   corr 0.506 [0.505; 0.508]   reproduz em  0/10
  10 epocas    peso 0.129 [0.127; 0.130]   corr 0.506 [0.505; 0.509]   reproduz em  0/10
  20 epocas    peso 0.128 [0.126; 0.129]   corr 0.505 [0.503; 0.509]   reproduz em  0/10
  50 epocas    peso 0.123 [0.120; 0.125]   corr 0.503 [0.500; 0.507]   reproduz em  0/10
  100 epocas   peso 0.114 [0.111; 0.116]   corr 0.498 [0.496; 0.503]   reproduz em  0/10
  200 epocas   peso 0.099 [0.096; 0.101]   corr 0.489 [0.485; 0.493]   reproduz em  0/10

  GRADE B - lr, 200 epocas, paciencia 30, KL 0.001
  lr 0.0001    peso 0.129 [0.129; 0.129]   corr 0.507 [0.507; 0.507]   reproduz em  0/10
  lr 0.0003    peso 0.128 [0.128; 0.129]   corr 0.507 [0.507; 0.507]   reproduz em  0/10
  lr 0.001     peso 0.126 [0.126; 0.127]   corr 0.506 [0.506; 0.507]   reproduz em  0/10
  lr 0.003     peso 0.121 [0.118; 0.122]   corr 0.504 [0.502; 0.506]   reproduz em  0/10
  lr 0.01      peso 0.107 [0.102; 0.110]   corr 0.495 [0.487; 0.500]   reproduz em  0/10

  GRADE C - peso do KL, 200 epocas, paciencia 30, lr 0.01
  KL 0         peso 0.107 [0.102; 0.111]   corr 0.495 [0.487; 0.500]   reproduz em  0/10
  KL 0.001     peso 0.107 [0.102; 0.110]   corr 0.495 [0.487; 0.500]   reproduz em  0/10
  KL 0.01      peso 0.107 [0.102; 0.110]   corr 0.497 [0.490; 0.502]   reproduz em  0/10
  KL 0.1       peso 0.105 [0.100; 0.109]   corr 0.517 [0.514; 0.526]   reproduz em  0/10
  KL 1         peso 0.102 [0.097; 0.105]   corr 0.558 [0.550; 0.574]   reproduz em  0/10
  KL 10        peso 0.097 [0.092; 0.101]   corr 0.617 [0.598; 0.644]   reproduz em  0/10

  LOGITS NO PROTOCOLO DO ARTIGO (lr 0.01, 200 ep, pac. 30, KL 0.001)
  maior deslocamento de uma banda   mediana 1.34  faixa [1.22; 1.79]
  distancia 1o-2o logit, inicio     12.21 a 12.21
  distancia 1o-2o logit, fim        12.24 a 12.90
```

## Anexo 3 — saída de `scripts/verificar_kl_secao34.py`

Reproduzível com:

```bash
python scripts/verificar_kl_secao34.py
```

```
   Computing ANOVA F-statistic...

==========================================================================
 SECAO 3.4 - A BUSCA EM GRADE DO PESO DO KL (manuscript_R2.tex:267)
==========================================================================

  correlacao das portas treinadas com o prior ANOVA,
  5 folds x 10 sementes = 50 treinos por linha

  lambda 0.0001  mediana 0.337  faixa [0.331; 0.348]  r > 0.85 em 0/50
  lambda 0.001   mediana 0.337  faixa [0.333; 0.342]  r > 0.85 em 0/50
  lambda 0.01    mediana 0.338  faixa [0.333; 0.342]  r > 0.85 em 0/50
  lambda 0.1     mediana 0.347  faixa [0.344; 0.351]  r > 0.85 em 0/50

  inicializacao aleatoria (sem prior, KL 0.001, como train_random.py):
                 mediana 0.317  faixa [0.173; 0.498]  r > 0.85 em 0/50

  o artigo afirma: lambda 0.001 -> r ~ 0.35-0.51; lambda >= 0.01 ->
  r > 0.85; lambda <= 1e-4 -> indistinguivel da inicializacao aleatoria.
```

## Anexo 4 — saída de `verify_wd_on_gate.py` (script da orientação, 30/10)

Rodado duas vezes em 04/11, com saída idêntica; torch 2.14.1+cpu, numpy
2.5.2, scikit-learn 1.9.0. O script não está versionado aqui. *Atualização
de 12/11: versionado, como chegou, em `scripts/orientacao/verify_wd_on_gate.py`,
com a autorização da orientação.*

```
python verify_wd_on_gate.py --repo <código do artigo>
======================================================================================
 GATE DISPLACEMENT UNDER THE ARTICLE'S PROTOCOL: learning or weight decay?
======================================================================================
  Light model, Tecator, 10 seeds.  median [min; max]
  shrink_frac = fraction of bands whose |logit| decreased (1.0 = pure shrinkage, ~0.5 = no preferred direction)
  rho_shrink  = corr(displacement, -theta_initial)  (1.0 = displacement is exactly proportional shrinkage)

  --- column 0 = water (as published) ---
  weight decay        max |disp|     median |disp|       shrink_frac        rho_shrink           test R2
  1e-4 (all)     1.694 [1.449; 1.920] 0.118 [0.094; 0.143] 0.765 [0.710; 0.820] 0.806 [0.788; 0.816] 0.922 [0.800; 0.960]
  0              0.235 [0.207; 0.318] 0.080 [0.060; 0.098] 0.595 [0.530; 0.640] 0.388 [0.336; 0.486] 0.644 [-1.690; 0.827]
  1e-4, MLP only 0.278 [0.189; 0.317] 0.094 [0.080; 0.104] 0.610 [0.580; 0.640] 0.403 [0.343; 0.452] 0.913 [0.879; 0.948]

  --- column 1 = fat ---
  weight decay        max |disp|     median |disp|       shrink_frac        rho_shrink           test R2
  1e-4 (all)     1.654 [1.555; 1.929] 0.134 [0.103; 0.171] 0.750 [0.720; 0.780] 0.810 [0.793; 0.820] 0.922 [0.844; 0.942]
  0              0.246 [0.176; 0.314] 0.085 [0.070; 0.127] 0.635 [0.560; 0.660] 0.427 [0.358; 0.558] 0.244 [-4.040; 0.754]
  1e-4, MLP only 0.301 [0.260; 0.363] 0.104 [0.083; 0.121] 0.625 [0.590; 0.650] 0.435 [0.360; 0.537] 0.941 [0.874; 0.965]

```

## Anexo 5 — saída de `scripts/verificar_decaimento_porta.py`

Rodado duas vezes em 05/11, com saída idêntica; mesmo ambiente do Anexo 4.
O Tecator é a coluna 0 (água), como controle.

```
python -B scripts/verificar_decaimento_porta.py
=== tecator (100 bandas), 10 sementes, mediana [mín; máx]; distância 1º-2º no início: 11.47
  decaimento 1e-4 em tudo
    maior deslocamento     1.694 [1.449; 1.920]
    fração encolhida       0.765 [0.710; 0.820]
    correlação c/ −θ₀      0.806 [0.788; 0.816]
    distância 1º-2º, fim   11.489 [11.413; 11.566]
    R² de teste            0.922 [0.800; 0.960]
  decaimento nenhum
    maior deslocamento     0.235 [0.207; 0.318]
    fração encolhida       0.595 [0.530; 0.640]
    correlação c/ −θ₀      0.388 [0.336; 0.486]
    distância 1º-2º, fim   11.428 [11.359; 11.511]
    R² de teste            0.644 [-1.690; 0.827]
  decaimento só no MLP
    maior deslocamento     0.278 [0.189; 0.317]
    fração encolhida       0.610 [0.580; 0.640]
    correlação c/ −θ₀      0.403 [0.343; 0.452]
    distância 1º-2º, fim   11.414 [11.357; 11.508]
    R² de teste            0.913 [0.879; 0.948]
=== gasoline (401 bandas), 10 sementes, mediana [mín; máx]; distância 1º-2º no início: 12.21
  decaimento 1e-4 em tudo
    maior deslocamento     1.344 [1.223; 1.789]
    fração encolhida       0.995 [0.993; 0.998]
    correlação c/ −θ₀      0.724 [0.704; 0.752]
    distância 1º-2º, fim   12.566 [12.238; 12.899]
    R² de teste            0.945 [0.918; 0.957]
  decaimento nenhum
    maior deslocamento     0.612 [0.403; 0.854]
    fração encolhida       0.213 [0.190; 0.252]
    correlação c/ −θ₀      -0.172 [-0.230; -0.095]
    distância 1º-2º, fim   12.198 [12.049; 12.374]
    R² de teste            0.943 [0.826; 0.959]
  decaimento só no MLP
    maior deslocamento     0.660 [0.487; 0.837]
    fração encolhida       0.217 [0.195; 0.254]
    correlação c/ −θ₀      -0.161 [-0.253; -0.081]
    distância 1º-2º, fim   12.201 [12.049; 12.371]
    R² de teste            0.945 [0.904; 0.961]
```
