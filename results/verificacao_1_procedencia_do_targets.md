# Verificação 1 — o `targets.csv` é o insumo das rodadas publicadas?

*Rodrigo Fernandes — 30/09/2026*

> **O que foi pedido:** Confirme que o `targets.csv` é mesmo o insumo das rodadas publicadas — data de modificação, histórico do git do repositório, e qual script o gerou a partir de qual fonte. Se houver o script de exportação, ele mostra a troca literalmente.

### Resposta curta

**Sim, é o insumo das rodadas publicadas** — mas quem prova isso é a
reprodução numérica, não o histórico do git.

### Os três itens pedidos

**Data de modificação.** Os arquivos do zip enviado estão todos com
29/09/2026 09:44, que é a data em que foram extraídos. Eles não datam nada.
Porém o `overleaf_submission.zip`, que veio junto, **preserva a data de cada
entrada**: as figuras da submissão são de **21/05/2026, 17:45**.

**Histórico do git.** A pasta enviada veio sem `.git`. O repositório público
que o manuscrito declara — `github.com/clarimar/prior-guided-spectral-gating`
— está acessível, e foi clonado para esta verificação. São 18 commits, de
23/05/2026 a 09/09/2026. O `targets.csv` e o `spectra.csv` entraram no
**commit inicial** (`42c0b30`, 23/05/2026 10:01) e **nunca foram
alterados**. Os dois são idênticos por `sha256` aos arquivos do zip.

**Ressalva importante:** as figuras da submissão são de 21/05, dois dias
*antes* do commit inicial. O git, portanto, **não cobre o período em que os
resultados foram gerados**. O que sustenta "é o insumo das rodadas
publicadas" é a reprodução exata dos números — a coluna 0 dá R² 0,9191 e
RMSE 0,2957, contra 0,919 e 0,296 da Tabela 1 —, e não o histórico.

**Qual script o gerou, a partir de qual fonte.** O script não está no
repositório, e nunca esteve: em toda a história foram apagados 21 arquivos,
nenhum deles um script. Os dois scripts de download presentes
(`src/data/download.py` e `src/data/download_old.py`) declaram a fonte como
`data(meatspec, package="pls")`, mas **o pacote `pls` não distribui esse
conjunto** — ele tem apenas `gasoline`, `mayonnaise`, `oliveoil` e `yarn`,
conferido no R desta máquina. O `meatspec` existe no pacote `faraway`, onde
traz somente a gordura, e não as três colunas: conferido em 30/09 no
`faraway` 1.0.9 do CRAN, cujo `meatspec` tem 215 linhas e as colunas `V1` a
`V100` e `fat`. Em qualquer dos casos,
aqueles scripts cairiam no tratamento de erro e não poderiam ter gerado
estes arquivos.

**A fonte de fato** é o `scikit-fda` ou o `fda.usc` — os dois entregam o
mesmo X, então os dados não distinguem qual. O que identifica o **modo de
geração** é o eixo: o cabeçalho do `spectra.csv` é `850nm, 852nm, …,
1047nm, 1050nm`, e os `argvals` dessas bibliotecas são `850,0 / 852,0202 /
… / 1047,9798 / 1050,0`. O cabeçalho é esse eixo truncado para inteiro —
1047,9798 virou `1047nm`, não 1048. Um CSV do StatLib ou do OpenML não
traria esses valores quebrados para truncar. O arquivo foi gerado por
código, a partir de uma dessas bibliotecas.

**Onde o script pode estar.** `src/data/download.py:73`, o `README_1.md` e o
`setup_project.py` apontam para `~/Dropbox/chemometric-band-selection/`, o
projeto anterior. O script de exportação e a data original podem estar lá,
ou no histórico de versões do Dropbox.

---

## Anexo — saída de `scripts/verificar_origem_targets.py`

Reproduzível com:

```bash
python scripts/verificar_origem_targets.py
```

```

==========================================================================
 1. DATA DE MODIFICACAO DOS ARQUIVOS DO ZIP
==========================================================================

  2026-09-29 09:44  data/raw/tecator/targets.csv
  2026-09-29 09:44  data/raw/tecator/spectra.csv
  2026-09-29 09:44  src/data/download.py
  2026-09-29 09:44  scripts/baseline_pls.py
  2026-09-29 09:44  revision_r1/one_se_output.txt

  -> todas iguais (2026-09-29 09:44): e a data de extracao do zip,
     nao a da rodada. Estes arquivos nao datam nada.

  o overleaf_submission.zip preserva a data de cada entrada:
    2026-05-21 17:45  overleaf_submission/figures/fig3_parameter_efficiency.png
    2026-05-21 17:45  overleaf_submission/README_OVERLEAF.txt
    -> ha data original, e ela e ANTERIOR ao commit inicial do
       GitHub (ver secao 2). Logo o git nao cobre o periodo em
       que os resultados foram gerados.

==========================================================================
 2. HISTORICO DO GIT
==========================================================================

  .git dentro do zip (prior-guided-spectral-gating-main/): NAO EXISTE
  -> o zip veio sem historico.

  clone do repositorio publico em /home/rodrigo_vieira/pgsg-github: ok
     (github.com/clarimar/prior-guided-spectral-gating, o que o
      manuscrito declara na disponibilidade de codigo)

  commits: 18

  primeiro e ultimo:
    42c0b30  2026-05-23  Clarimar José Coelho  Initial commit: Prior-guided spectral gating framework
    762d43d  2026-09-09  Clarimar José Coelho  revision_talanta: PLAN.md final (grade completa + decisões); carta antecipada em historico/

==========================================================================
 3. QUANDO O targets.csv ENTROU, E SE MUDOU DEPOIS
==========================================================================

  data/raw/tecator/targets.csv:
    42c0b30  2026-05-23 10:01:41 -0300  Initial commit: Prior-guided spectral gating framework

  data/raw/tecator/spectra.csv:
    42c0b30  2026-05-23 10:01:41 -0300  Initial commit: Prior-guided spectral gating framework

  -> um commit so para cada: entraram e nunca mais foram
     alterados.

  arquivos apagados em toda a historia: 21
    destes, scripts (.py/.R/.sh): nenhum
    os demais: revision_r2/elsarticle.zip ... revision_r2/pgsg_1_R2.spl
  -> nenhum script foi removido da historia: o script de
     exportacao nao esteve neste repositorio.

==========================================================================
 4. O ARQUIVO DO GITHUB E O DO ZIP SAO O MESMO?
==========================================================================

  data/raw/tecator/targets.csv
    github: 3115d04920e67d810cc368c10991bf7110e5057c08fd6091c79d9f1d625142b2
    zip   : 3115d04920e67d810cc368c10991bf7110e5057c08fd6091c79d9f1d625142b2
    -> IDENTICOS byte a byte
  data/raw/tecator/spectra.csv
    github: cc8b2b09e621b570c4f36a2a005bac5844d2a7ac80e1b4281d21fab88310845d
    zip   : cc8b2b09e621b570c4f36a2a005bac5844d2a7ac80e1b4281d21fab88310845d
    -> IDENTICOS byte a byte

  -> o arquivo publicado e o que foi enviado sao o mesmo. Com a
     reproducao dos numeros, e o insumo das rodadas publicadas.

==========================================================================
 5. QUAL SCRIPT DECLARA TER GERADO O targets.csv
==========================================================================

  src/data/download.py:
    linha  49: Y = np.array(ro.r('meatspec$Y'))
    linha  53: pd.DataFrame(Y, columns=['Fat', 'Water', 'Protein']).to_csv(
    linha  73: print("write.csv(meatspec$Y, '~/Dropbox/chemometric-band-selection/data/raw/tecator/targets.csv', row.names=FALSE)")
    linha  92: write.csv(meatspec$Y, file.path(output_dir, 'targets.csv'), row.names=FALSE)

  src/data/download_old.py:
    linha  55: Y = np.array(ro.r('meatspec$Y'))
    linha  59: pd.DataFrame(Y, columns=['Fat', 'Water', 'Protein']).to_csv(
    linha  79: print("   write.csv(meatspec$Y, 'tecator_targets.csv', row.names=FALSE)")
    linha 255: Y = np.array(ro.r('meatspec$Y'))
    linha 262: pd.DataFrame(Y, columns=['Fat', 'Water', 'Protein']).to_csv(
    linha 295: write.csv(meatspec$Y,

  -> declaram o meatspec do pacote R 'pls', e escrevem os nomes das
     colunas na mao.

==========================================================================
 6. ESSA FONTE EXISTE? O PACOTE 'pls' TEM O meatspec?
==========================================================================

  conjuntos do pacote 'pls': gasoline, mayonnaise, oliveoil, yarn
  'meatspec' esta na lista: False
  pacotes instalados com meatspec: nenhum

  -> o meatspec nao existe no pacote declarado. Ele existe no pacote
     R 'faraway', mas ali traz so a gordura, e nao as tres colunas.
     Em qualquer dos casos, aqueles scripts cairiam no except: nao
     foram eles que geraram estes arquivos.

==========================================================================
 7. O QUE FOI GRAVADO, E QUAL E A FONTE DE FATO
==========================================================================

   pos  rotulo no CSV      min      max    = de fato
     0            Fat    39.30    76.60         agua
     1          Water     0.90    49.10      gordura
     2        Protein    11.00    21.80     proteina

  cabecalho do spectra.csv: 850nm, 852nm, 854nm, 856nm, ...
  -> nomes de comprimento de onda. Aquele script faz pd.DataFrame(X),
     que geraria 0, 1, 2, ... Nao foi ele.

  skfda (fetch_tecator): X (215, 100), y (215, 3), target_names ['fat', 'water', 'protein']
  spectra.csv identico ao X do skfda, linha a linha: True

  ressalva: o X do fda.usc e identico ao do skfda, entao esta
  igualdade nao diz QUAL das duas bibliotecas foi usada - diz apenas
  que nao foi o meatspec.

  o que diz o modo de geracao e o eixo:
    cabecalho do spectra.csv, ultimas 5: 1041nm, 1043nm, 1045nm, 1047nm, 1050nm
    argvals da biblioteca, ultimos 5   : 1041.9192, 1043.9394, 1045.9596, 1047.9798, 1050.0000
    argvals truncados para inteiro == cabecalho: True
    -> o cabecalho e o eixo da biblioteca truncado (1047.9798 virou
       1047nm, nao 1048). Um CSV do StatLib ou do OpenML nao traria
       esses valores quebrados para truncar: o arquivo foi gerado
       por codigo a partir de uma dessas bibliotecas.

  correspondencia coluna a coluna do targets.csv com o y do skfda:
    CSV col 0 (Fat) == skfda col 1 (water)
    CSV col 1 (Water) == skfda col 0 (fat)
    CSV col 2 (Protein) == skfda col 2 (protein)

==========================================================================
 CONCLUSAO
==========================================================================

  1. O targets.csv entrou no commit inicial do repositorio publico e
     nunca foi alterado. E byte a byte igual ao que foi enviado.
     RESSALVA: o zip do Overleaf traz figuras de 21/05, anteriores ao
     commit inicial (23/05), entao o git NAO cobre o periodo em que
     os resultados foram gerados. Quem prova que este arquivo e o
     insumo das rodadas publicadas e a reproducao numerica exata
     (PLS 0.9191 / 0.2957), nao o historico.

  2. O meatspec nao existe no pacote R declarado ('pls'). A
     fonte de fato e o scikit-fda ou o fda.usc - os dois entregam o
     mesmo X, entao os dados nao distinguem qual. O eixo truncado no
     cabecalho mostra que o arquivo foi gerado por codigo a partir
     de uma delas. O y e o mesmo com as colunas 0 e 1 TROCADAS: o
     conteudo ficou em agua, gordura, proteina, e o cabecalho na
     ordem das bibliotecas, gordura, agua, proteina.

  3. O script que fez a troca nao esta NESTE repositorio e nunca
     esteve: nenhum script foi apagado em toda a historia. Onde ele
     pode estar: src/data/download.py:73, README_1.md e
     setup_project.py apontam para ~/Dropbox/chemometric-band-
     selection/, o projeto anterior. O script e a data original
     podem estar la, ou no historico de versoes do Dropbox.
```
