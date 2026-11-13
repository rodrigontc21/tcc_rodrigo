# Janelas de atribuição espectroscópica (plausibilidade química)

**Status:** rascunho, 13/11/2026. Base da tabela de plausibilidade química do
Estágio 6 (ADR 019): fração das bandas selecionadas que caem em janelas de
atribuição documentada. **Só entra posição lida na fonte, com a frase
conferida no texto.** Nada daqui está no código ainda.

## Confirmado na fonte (lido no texto ou no resumo, como indicado)

### Tecator (gordura; transmitância 850–1048 nm)

ElMasry, G.; Nakauchi, S. (2016). Prediction of meat spectral patterns based
on optical properties and concentrations of the major constituents. *Food
Science & Nutrition* 4(2):269–283. doi:10.1002/fsn3.286 (acesso aberto,
PMC4779495; lido em 13/11).

| posição | constituinte | atribuição, nas palavras da fonte | fonte primária citada |
|---|---|---|---|
| 930 nm | gordura | "combinations of stretching and bending of the methyl and methylene (CH2) groups in fatty acids" | Ozanich et al. (1992) |
| 1040 nm | gordura | idem (os "two small absorption peaks at 930 and 1040 nm") | Ozanich et al. (1992) |
| 970 nm | água | "high-order combination bands of symmetric and asymmetric stretching modes of the O–H bond" | Xu et al. (2010); Wang et al. (2013) |

O alvo é a gordura. A água entra como banda de interferente: no Tecator,
gordura e água variam em sentidos opostos.

**Avaliação da fonte (13/11):** é fonte secundária: o próprio artigo cita
Ozanich et al. (1992) para a gordura e Xu et al. (2010) para a água. As
**posições** (930, 1040 e 970 nm) aparecem iguais em outras fontes da
busca, mas a **atribuição** varia: este artigo fala em combinações de
estiramento e deformação de CH2 e CH3; outras fontes falam em harmônica de
C–H, e uma chega a chamar 930 nm de quarta harmônica. Por isso a tabela
registra a posição e a frase da fonte, sem afirmar a ordem da harmônica. O
Borggaard e Thodberg (1992), origem do conjunto Tecator, não traz
atribuição de bandas pelo que se achou.

**A referência padrão, lida em 13/11:** Workman, J., Jr.; Weyer, L. (2008).
*Practical Guide to Interpretive Near-Infrared Spectroscopy*. CRC Press
(Taylor & Francis). ISBN 978-1-57444-784-2. PDF obtido pelo Rodrigo; cópia
em `docs/privado/`. Na tabela de atribuições do apêndice (o livro escreve
ν para a fundamental, 2ν para a 1ª harmônica, 3ν para a 2ª e 4ν para a
3ª):
- **930 nm:** "C–H methylene (–CH2) C–H (4ν), methylene C–H, Hydrocarbons,
  aliphatic" (p. 240), ou seja, 3ª harmônica do CH2, como na Tabela I do
  Golic et al. (2003);
- **1041 nm:** "C–H methylene C–H, associated with linear aliphatic ...
  (3νCH2 and δCH2) combination" (p. 242), ou seja, combinação de
  estiramento e deformação, como o ElMasry e Nakauchi descrevem a banda de
  1040 nm;
- **água:** o capítulo de água dá o pico da água líquida em 976 nm
  ("the water peaks at 6900 cm−1 (1450 nm) and ... (976 nm)", p. 69), e a
  Tabela 6.2 lista 979 nm para a água líquida perto do congelamento; a
  atribuição dessa linha da tabela não saiu legível na extração do texto e
  não foi registrada.

**Com isso a divergência se desfaz:** as duas bandas de gordura têm origens
diferentes. A de 930 nm é harmônica do CH2 (Workman e Weyer; Golic et al.)
e a de 1040 nm é combinação de estiramento e deformação do CH2 (Workman e
Weyer; ElMasry e Nakauchi). O ElMasry e Nakauchi chamam as duas de
combinação, o que vale só para a de 1040 nm.

### Bioprocess (glicose; Raman 390–3385 cm⁻¹)

Dumouilla, V.; Dussap, C.-G. (2021). Online analysis of D-glucose and
D-mannose aqueous mixtures using Raman spectroscopy: an in silico and
experimental approach. *Bioengineered* 12(1):4420–4431.
doi:10.1080/21655979.2021.1955550 (acesso aberto, PMC8806848; Tabela 1
lida em 13/11). Solução aquosa de D-glicose a 30% de matéria seca, laser
de 785 nm.

| deslocamento (cm⁻¹) | intensidade | atribuição (Tabela 1) | região, na Tabela 1 |
|---|---|---|---|
| 1126 | média | δ(COH) | impressão digital |
| 1061 | média | ώ(CH2) | impressão digital |
| 1017 | forte | δ(COH) | impressão digital |
| 899 e 910 | média | δ(COH) | impressão digital |
| 846 | média | δ(COH) | anomérica |
| 1462, 1367 | forte | δ(CH2) | deformações CH2 e CH |
| 1336 | média | δ(CH) | deformações CH2 e CH |
| 1264 | média | ώ(CH2) | deformações CH2 e CH |
| 447, 417 | média, forte | δ(CCO) | baixo número de onda |
| 2945, 2898 | forte | ν(CH2) | estiramento CH2 |

Ressalvas da própria fonte:
- as bandas de 850 e 918 cm⁻¹, antes atribuídas às formas α e β da
  glicose, aparecem também na manose ("might not strictly related to the
  D-glucose molecule");
- o resumo do artigo diz que a glicose é monitorada em 974 cm⁻¹, mas o
  texto e a Tabela 1 dizem o contrário (960 e 974 cm⁻¹ são só da manose);
  fica valendo a Tabela 1;
- o bioprocess tem outros açúcares e substratos, que dividem várias
  dessas bandas. A banda da água (1645 cm⁻¹, δ HOH) e a de O–H (3400 cm⁻¹,
  fora da faixa do conjunto) não são da glicose.

**Corroboração independente (lida em 13/11):** Du, K.; Zhao, M.; Wang, T.;
Qu, G.; Cai, H. (2026). A DFT-based Raman spectral atlas and vibrational
assignment of aqueous glucose structures and derivatives. *Communications
Chemistry* 9. doi:10.1038/s42004-026-02118-z (acesso aberto). Simulação DFT
com espectro experimental. Concorda nas bandas principais:
- "an intense characteristic peak at 1125 cm⁻¹ signifies the chair
  conformation of pyranose";
- "a strong peak in the 1040–1060 cm⁻¹ region corresponds to pyranose";
- o estiramento C–C "observed at 1022 cm⁻¹ experimentally";
- a deformação CCO do modo de respiração do anel em 1097 cm⁻¹.

A referência clássica é Mathlouthi e Vinh Luu (1980), *Carbohydrate
Research*, "Laser-Raman spectra of d-glucose and sucrose in aqueous
solution", que é paga e não foi lida.

**Avaliação:** duas fontes independentes, abertas e revisadas, uma
experimental e uma com DFT, concordam em 1125, ~1060 e ~1020 cm⁻¹. É a
parte mais sólida da tabela.

### Mango (matéria seca; Vis-NIR 309–1149 nm) — texto completo lido

Golic, M.; Walsh, K.; Lawson, P. (2003). Short-wavelength near-infrared
spectra of sucrose, glucose, and fructose with respect to sugar
concentration and temperature. *Applied Spectroscopy* 57(2):139–145.
doi:10.1366/000370203321535033. PDF obtido pelo Rodrigo em 13/11 (cópia
escaneada, lida pelas imagens das páginas); cópia em `docs/privado/`.
Fonte primária: as bandas foram confirmadas com soluções em D2O e com
sacarose deuterada, no grupo que estuda a matéria seca de manga.

**Tabela I** (p. 140), "literature-reported band assignments", em nm, com
as referências da própria tabela:

| atribuição | 1ª harmônica | 2ª harmônica | 3ª harmônica |
|---|---|---|---|
| estiramento O–H | 1410–1440 | 970 | 738 |
| combinações de O–H | 1100 | 840 | — |
| estiramento C–H | 1600–1800 | 1100–1230 | 910 |
| estiramento CH2 | 1720–1765 | 1215 | 930 |

Do texto e do resumo:
- "a third overtone band at 910 nm" para os grupos C–H de açúcar, e as
  calibrações de açúcar "relied strongly on the 910 nm sugar CH related
  bands";
- as vibrações de O–H em "750, 840, 960, and 985 nm"; com mais açúcar ou
  menos temperatura, a absorbância cai em 960 nm e sobe em 984 nm (mais
  ligação de hidrogênio);
- "A CH2 third overtone is reported at 930 nm";
- as bandas dessa região "are typically 'broad' (approximate bandwidth of
  50 nm), overlapped, and difficult to assign" (p. 139).

A matéria seca da manga é sobretudo carboidrato (açúcares e amido), mas a
fonte é de soluções de açúcar, não de fruta: a banda de amido não está aí.

**A revisão de fruta, que fecha o amido** (lida em 13/11): Walsh, K. B.;
Blasco, J.; Zude-Sasse, M.; Sun, X. (2020). Visible-NIR 'point'
spectroscopy in postharvest fruit and vegetable assessment: the science
behind three decades of commercial use. *Postharvest Biology and
Technology* 168:111246. doi:10.1016/j.postharvbio.2020.111246. PDF obtido
pelo Rodrigo; cópia em `docs/privado/`.
- **Amido:** os modelos de matéria seca são "relatively robust to stage of
  ripening, i.e., to proportion of starch and soluble sugars", o que a
  fonte atribui à "similarity of NIRS spectra of starch and sugar in
  water". Não há banda separada de amido a acrescentar: a de C–H em 910 nm
  cobre os dois.
- **C–H:** "Absorption near 910, 1100 and 1700nm is associated with C–H
  third, second and first overtone features", igual à Tabela I do Golic.
- **O–H:** "Absorption at 840, 960 and 1440nm is associated with the first,
  second and third overtones of O–H stretching". As posições batem com o
  Golic, mas a numeração não: a Tabela I do Golic põe 1410–1440 nm na 1ª
  harmônica, 970 nm na 2ª e 840 nm como combinação. Fica a numeração do
  Golic, fonte primária; a divergência fica registrada.
- **Pigmentos, dentro da faixa do Mango:** clorofila em 680 nm ("The 680nm
  in-vivo peak"); carotenoides "with three peak maxima in the wavelength
  range from 420 to 503nm" (beta-caroteno perto de 475 nm, xantofilas perto
  de 435 nm); antocianina em 530–550 nm. Ligam-se à cor e à maturação, não
  diretamente à matéria seca.

**Consequência para o Tecator:** a Tabela I atribui 930 nm à 3ª harmônica
do estiramento CH2 e 970 nm à 2ª harmônica do estiramento O–H. As posições
batem com o ElMasry e Nakauchi (2016); a atribuição dele ("combinations of
stretching and bending") é outra. Ficam as duas, cada uma com a sua fonte.

### Gasoline (octanagem; NIR 900–1700 nm) — texto completo lido

Bohács, Gy.; Ovádi, Z.; Salgó, A. (1998). Prediction of gasoline properties
with near infrared spectroscopy. *Journal of Near Infrared Spectroscopy*
6:341–348. PDF obtido pelo Rodrigo em 13/11, lido inteiro; cópia em
`docs/privado/` (fora do git). Mesma faixa e resolução do conjunto: "900 to
1700 nm spectral range (401 data points)". 350 gasolinas; RON e MON
previstos com R de 0,975 e 0,972.

| posição | atribuição, nas palavras da fonte (p. 343) |
|---|---|
| 1144 nm | "aromatic C–H second ... overtone" |
| 1674 nm | "aromatic C–H ... first overtone" |
| 1190 nm | "methyl C–H second overtone" |
| 1395 nm | "combination of the methylene C–H stretching vibrations" |

A frase inteira: "At the wavelengths of 1144 and 1674 nm the aromatic C–H
second and first overtone, at 1190 nm the methyl C–H second overtone, at
1395 nm combination of the methylene C–H stretching vibrations were
observed." A fonte cita também Evans et al. (1951, *Anal. Chem.* 23:1604),
que contou os grupos metila, metileno e C–H aromático em combustíveis "using
the second overtone region (1100–1250 nm)".

**Confirmado na referência padrão** (Workman e Weyer, apêndice, pp. 242
e 249): 1142–1143 nm, "C–H aromatic ... (3ν), aromatic C–H"; 1194–1195 nm,
"C–H methyl ... (3ν)"; 1395 nm, "C–H methylene ... combination"; 1680–1685
nm, "C–H aromatic ... (2ν), aromatic C–H". As posições do Bohács et al.
(1144, 1190, 1395 e 1674 nm) e as atribuições batem.

**Ressalva:** a fonte atribui as bandas aos grupos de hidrocarbonetos, não
diz quais delas sustentam a previsão da octanagem. A ligação com a
octanagem é a do resumo do Kelly et al. (1989), abaixo, e a da composição,
a seguir.

**Por que esses grupos importam para a octanagem** (lido em 13/11):
Benavides, A.; Zapata, C.; Benjumea, P.; Franco, C. A.; Cortés, F. B.;
Ruiz, M. A. (2023). Predicting octane number of petroleum-derived gasoline
fuels from MIR spectra, GC-MS, and routine test data. *Processes*
11:1437. doi:10.3390/pr11051437 (acesso aberto, CC BY; PDF obtido pelo
Rodrigo, cópia em `docs/privado/`). Nas palavras da fonte:
- "isoparaffins have better performance than n-alkanes", e a octanagem
  "increases with the more central position of branches and with their
  bulkiness";
- na cromatografia, a gasolina de octanagem maior "had a higher content of
  aromatic hydrocarbons and multibranched isoparaffins".

O artigo é de infravermelho **médio** (2700–3500 cm⁻¹), então as posições
de banda dele não servem ao nosso NIR; serve só para a ligação entre
composição e octanagem. Que os aromáticos (1144 e 1674 nm) e a ramificação
(metila, 1190 nm) estejam ligados à octanagem é leitura minha juntando as
duas fontes, não frase de nenhuma delas.

## Ainda sem fonte lida (não usar) e fontes deixadas de lado

### Gasoline, fonte complementar

- **Confirmada só pelo resumo:** Kelly, J. J.; Barlow, C. H.;
  Jinguji, T. M.; Callis, J. B. (1989). Prediction of gasoline octane
  numbers from near-infrared spectral features in the range 660–1215 nm.
  *Analytical Chemistry* 61(4):313–320. doi:10.1021/ac00179a007. O resumo
  (OSTI 6271943, lido) diz que nessa faixa aparecem "vibrational overtones
  and combination bands of CH groups of methyl, methylene, aromatic, and
  olefinic functions", correlacionadas à octanagem. As posições do Kelly
  estão no texto completo, pago (ACS); com o Bohács et al. (1998), não são
  mais necessárias.
- O que apareceu nas buscas em **patentes** e **material de fabricante**
  ficou de fora.

### Mango, fontes que ficaram de lado

- **Lido, mas não é de matéria seca:** um artigo aberto de manga
  (*Horticulturae* 11(7):759, MDPI) cita o pico de 680 nm como clorofila.
- As buscas indicam a água em torno de 960–980 nm e C–H de açúcares em
  torno de 910 nm, mas **as fontes discordam até na ordem da harmônica**
  (uma chama 960 nm de primeira, outra de segunda). Não entra sem a fonte
  revisada.

## Em aberto, antes de virar código

1. **Largura das janelas.** As fontes dão a posição do pico, não a
   largura. A largura é escolha deste trabalho e precisa ser declarada
   antes da grade. Um número com fonte para o NIR de onda curta: o Golic
   et al. (2003) dá às bandas dessa região uma "approximate bandwidth of 50
   nm", o que sugeriria janelas de ±25 nm. No Raman não há número
   equivalente nas fontes lidas.
2. **Quais bandas contam:** só as do alvo, ou também as de interferente
   (a água no Tecator)? E no Raman, só a impressão digital ou todas as
   bandas da glicose?
3. **Os quatro conjuntos têm posições com fonte de texto completo**
   desde 13/11. O amido do Mango ficou resolvido pela revisão de Walsh et
   al. (2020): não há banda separada.
4. **No Mango, se os pigmentos contam.** A faixa do conjunto vai de 309 a
   1149 nm e inclui as bandas de clorofila e carotenoides, que não são da
   matéria seca. Se a janela for só a do alvo, ficam de fora.
