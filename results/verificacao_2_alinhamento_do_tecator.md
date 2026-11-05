# Verificação 2 — a coluna 0 é a água, e as 215 linhas estão alinhadas?

*Rodrigo Fernandes — 30/09/2026*

> **O que foi pedido:** Confira a identidade da coluna 0 contra a água do `fda.usc`, elemento a elemento, não só por min/max. E confirme o alinhamento das 215 linhas entre `targets.csv` e a matriz X.

### Resposta curta

**A coluna 0 é a água**, com diferença exatamente zero nas 215 linhas. **As
linhas não foram embaralhadas:** X e y estão alinhados. O erro está somente
na ordem das colunas de y em relação ao cabeçalho gravado.

### Identidade, elemento a elemento

A coluna 0 do `targets.csv`, rotulada `Fat`, foi comparada contra **cada
uma** das três colunas do `tecator$y` do `fda.usc`, nas 215 linhas:

| comparada contra | linhas iguais | maior diferença | diferença média |
|---|---|---|---|
| `Fat` | **0 de 215** | 7,57e+01 | 4,58e+01 |
| `Water` | **215 de 215** | **0,00e+00** | **0,00e+00** |
| `Protein` | 0 de 215 | 5,92e+01 | 4,55e+01 |

É o contraste que decide: identidade perfeita com a água, e distância grande
da gordura. Não é semelhança de faixa — são os mesmos valores.

O quadro completo das três colunas:

| no `targets.csv` | corresponde a | linhas iguais |
|---|---|---|
| 0, rotulada `Fat` | `Water` | 215 de 215 |
| 1, rotulada `Water` | `Fat` | 215 de 215 |
| 2, rotulada `Protein` | `Protein` | 215 de 215 |

### Alinhamento das 215 linhas

O `spectra.csv` é idêntico ao `tecator$absorp` linha a linha, **na ordem**, e
o `targets.csv` é idêntico ao `tecator$y` linha a linha, **na ordem**. Como
na fonte a linha *i* do espectro e a linha *i* do alvo são a mesma amostra,
os dois arquivos estão alinhados entre si: a linha *i* do `spectra.csv`
corresponde à linha *i* do `targets.csv`.

Isso importa porque limita o estrago. Se as linhas estivessem embaralhadas,
não haveria correção mecânica possível. Estando apenas as colunas trocadas,
a correção é trocar a coluna.

**Controle negativo.** Embaralhando as linhas de propósito, as duas
checagens passam a falhar. Sem isso, um teste que sempre dá "verdadeiro" não
provaria nada.

**Sobre as repetições.** O conjunto tem 22 espectros repetidos e 37 linhas de
alvo repetidas, e a **mesma contagem aparece na fonte** — não é artefato do
CSV. A comparação acima é posicional, linha *i* contra linha *i*, então
repetição não gera ambiguidade.

### Confronto com uma fonte independente: o OpenML 505

O `scikit-fda` **não é fonte independente** do `fda.usc`: o
`skfda.datasets.fetch_tecator` chama `_fetch_fda_usc("tecator")`, isto é, lê
do próprio `fda.usc`. Conferir os dois mostra que o resultado não depende do
caminho de leitura, e nada além disso.

Por isso a identificação foi refeita contra o **OpenML 505**, uma
distribuição separada do Tecator, com as colunas nomeadas `moisture`, `fat`,
`protein` (segundo anexo, `scripts/verificar_openml_tecator.py`). Ele tem
240 amostras; as 215 do `spectra.csv` são as 215 primeiras, na mesma ordem,
com diferença zero no espectro. Elemento a elemento:

| no `targets.csv` | no OpenML 505 | linhas iguais |
|---|---|---|
| 0, rotulada `Fat` | `moisture` | 215 de 215 |
| 1, rotulada `Water` | `fat` | 215 de 215 |
| 2, rotulada `Protein` | `protein` | 215 de 215 |

Duas fontes que rotulam as colunas de forma independente — `Water` no
`fda.usc`, `moisture` no OpenML — dão a mesma resposta. A ressalva que fica:
as duas descendem do mesmo arquivo original do StatLib, então são
independentes como distribuição e como rotulagem, não como medida.

O conteúdo do `targets.csv` está exatamente na ordem do OpenML (umidade,
gordura, proteína), e o cabeçalho na ordem do `fda.usc` (Fat, Water,
Protein). Isso é compatível com o mecanismo descrito pela orientação em
29/09, mas não decide qual lado foi mexido: o espectro do OpenML também é
idêntico ao do `fda.usc`, e só o cabeçalho truncado do `spectra.csv`
(verificação 1) aponta para uma das bibliotecas como origem do X.

---

## Anexo 1 — saída de `scripts/verificar_alinhamento_tecator.py`

Reproduzível com:

```bash
python scripts/verificar_alinhamento_tecator.py
```

```

==========================================================================
 1. A FONTE INDEPENDENTE: O TECATOR DO fda.usc
==========================================================================

  tecator$y     : (215, 3), colunas ['Fat', 'Water', 'Protein']
  tecator$absorp: (215, 100)

   pos  nome no fda.usc      min      max    media
     0              Fat     0.90    49.10    18.14
     1            Water    39.30    76.60    63.20
     2          Protein    11.00    21.80    17.68

==========================================================================
 2. A COLUNA 0 CONTRA CADA COLUNA DO fda.usc, ELEMENTO A ELEMENTO
==========================================================================

  215 linhas nas duas fontes (targets.csv 215, fda.usc 215)

  a pergunta da orientacao: a coluna 0, rotulada 'Fat', e a agua?

              contra    iguais    maior dif    dif media
                 Fat     0/215     7.57e+01     4.58e+01
               Water   215/215     0.00e+00     0.00e+00   <== identica
             Protein     0/215     5.92e+01     4.55e+01

  -> a coluna 0 e identica a AGUA e esta longe da gordura. O
     contraste e o que separa identidade de faixa parecida.

  as outras duas colunas, para o quadro completo:

                 CSV          fda.usc    iguais    maior dif
               0 Fat          1 Water   215/215     0.00e+00
             1 Water            0 Fat   215/215     0.00e+00
           2 Protein        2 Protein   215/215     0.00e+00

==========================================================================
 3. AS 215 LINHAS DE X E DE y ESTAO ALINHADAS?
==========================================================================

  targets.csv: (215, 3)
  spectra.csv: (215, 100)
  mesmo numero de linhas: True

  linhas repetidas em X: 22 no CSV, 22 na fonte
  linhas repetidas em y: 37 no CSV, 37 na fonte
  -> mesma contagem: sao repeticoes do proprio conjunto, nao
     artefato do CSV. A comparacao abaixo e posicional, linha i
     contra linha i, entao repeticao nao gera ambiguidade.

  spectra.csv == tecator$absorp, linha a linha, na ordem: True
  targets.csv == tecator$y, linha a linha, na ordem:      True

  -> no fda.usc a linha i de absorp e a linha i de y sao a mesma
     amostra. Os dois arquivos reproduzem a fonte na mesma ordem,
     linha por linha. Logo a linha i do spectra.csv corresponde a
     linha i do targets.csv: X e y estao alinhados.

     O unico embaralhamento e entre COLUNAS de y:
       CSV col 0 (Fat) = fda.usc col 1 (Water)
       CSV col 1 (Water) = fda.usc col 0 (Fat)
       CSV col 2 (Protein) = fda.usc col 2 (Protein)

  controle negativo (a checagem tem dentes?):
    com as linhas embaralhadas, X ainda casa: False
    com as linhas embaralhadas, y ainda casa: False
    -> as duas falsas: a checagem detecta reordenacao de linhas.

==========================================================================
 4. O RESULTADO DEPENDE DO CAMINHO DE LEITURA?
==========================================================================

  scikit-fda target_names: ['fat', 'water', 'protein']
  fda.usc colnames       : ['Fat', 'Water', 'Protein']

  o y do skfda e o do fda.usc tem o mesmo conteudo: True

  ressalva: o skfda.fetch_tecator chama _fetch_fda_usc('tecator'),
  entao os dois leem a MESMA fonte. Isto mostra que o resultado
  nao depende do caminho de leitura, nao que ha duas fontes.

  correspondencia do CSV com o skfda (repetida da verificacao 1):
    CSV col 0 (Fat) == skfda col 1 (water)
    CSV col 1 (Water) == skfda col 0 (fat)
    CSV col 2 (Protein) == skfda col 2 (protein)

==========================================================================
 CONCLUSAO
==========================================================================

  A coluna 0 do targets.csv, rotulada 'Fat', e a agua - conferido
  elemento a elemento contra o fda.usc, nas 215 linhas, com
  diferenca zero, e contra a gordura a diferenca e enorme.

  As linhas nao foram embaralhadas: X e y estao alinhados, linha a
  linha, com a fonte. O erro esta so na ordem das COLUNAS de y em
  relacao ao cabecalho gravado.
```

## Anexo 2 — saída de `scripts/verificar_openml_tecator.py`

Reproduzível com:

```bash
python scripts/verificar_openml_tecator.py
```

```

==========================================================================
 1. A FONTE: OPENML 505
==========================================================================

  nome tecator, versao 1, md5 bc1cfff2d40bc7e47e7b6aa0826f3d5d
  formato (240, 125)
  colunas de espectro: 100 (absorbance_1 ... absorbance_100)
  colunas de alvo, na ordem do arquivo: ['moisture', 'fat', 'protein']
    moisture  min  32.80  max  76.60
    fat       min   0.90  max  58.50
    protein   min   8.80  max  23.20

==========================================================================
 2. QUAIS LINHAS DO OPENML SAO AS 215 DO targets.csv?
==========================================================================

  targets.csv: (215, 3), cabecalho ['Fat', 'Water', 'Protein']
  spectra.csv: (215, 100)

  espectro: maior |OpenML[0:215] - spectra.csv| = 0.00e+00
  cada linha do spectra.csv casa com a mesma posicao no OpenML: True
  -> as 215 sao as 215 primeiras do OpenML, na mesma ordem; as 25 ultimas ficam de fora.

==========================================================================
 3. CADA COLUNA DO targets.csv CONTRA CADA COLUNA DO OPENML
==========================================================================

  O OpenML nomeia as colunas; o targets.csv tambem. Elemento a
  elemento, nas 215 linhas:

       targets.csv     OpenML    iguais   maior dif
  0            Fat   moisture   215/215    0.00e+00  <==
  0            Fat        fat     0/215    7.57e+01
  0            Fat    protein     0/215    5.92e+01

  1          Water   moisture     0/215    7.57e+01
  1          Water        fat   215/215    0.00e+00  <==
  1          Water    protein     0/215    3.72e+01

  2        Protein   moisture     0/215    5.92e+01
  2        Protein        fat     0/215    3.72e+01
  2        Protein    protein   215/215    0.00e+00  <==


==========================================================================
 CONCLUSAO
==========================================================================

  coluna rotulada 'Fat'      no targets.csv = 'moisture' no OpenML 505
  coluna rotulada 'Water'    no targets.csv = 'fat' no OpenML 505
  coluna rotulada 'Protein'  no targets.csv = 'protein' no OpenML 505

  O conteudo do targets.csv esta na ordem do OpenML (moisture,
  fat, protein), e o cabecalho gravado e Fat, Water, Protein. A coluna rotulada
  'Fat' e a umidade - confirmado numa fonte independente
  do fda.usc.
```
