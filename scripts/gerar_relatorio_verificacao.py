"""Roda um script de verificacao e escreve o resultado como Markdown.

A orientacao le documento, nao terminal. Este gerador executa o script
pedido, captura a saida e a envolve num relatorio com o enunciado do que
foi pedido, a resposta em prosa e a saida bruta como anexo.

Uso:
    python scripts/gerar_relatorio_verificacao.py 1
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "results"

VERIFICACOES = {
    "1": {
        "script": "scripts/verificar_origem_targets.py",
        "arquivo": "verificacao_1_procedencia_do_targets.md",
        "titulo": "Verificação 1 — o `targets.csv` é o insumo das rodadas "
                  "publicadas?",
        "pedido": (
            "Confirme que o `targets.csv` é mesmo o insumo das rodadas "
            "publicadas — data de modificação, histórico do git do "
            "repositório, e qual script o gerou a partir de qual fonte. Se "
            "houver o script de exportação, ele mostra a troca literalmente."
        ),
        "resposta": """
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
""",
    },
    "2": {
        "script": "scripts/verificar_alinhamento_tecator.py",
        "extras": ["scripts/verificar_openml_tecator.py"],
        "arquivo": "verificacao_2_alinhamento_do_tecator.md",
        "titulo": "Verificação 2 — a coluna 0 é a água, e as 215 linhas "
                  "estão alinhadas?",
        "pedido": (
            "Confira a identidade da coluna 0 contra a água do `fda.usc`, "
            "elemento a elemento, não só por min/max. E confirme o "
            "alinhamento das 215 linhas entre `targets.csv` e a matriz X."
        ),
        "resposta": """
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
""",
    },
    "3": {
        "script": "scripts/verificar_pipeline_tecator.py",
        "extras": ["scripts/verificar_divergencia_redes.py"],
        "arquivo": "verificacao_3_pipeline_com_o_alvo_correto.md",
        "titulo": "Verificação 3 — a extensão do que muda com o alvo correto",
        "pedido": (
            "Rode o pipeline completo com a coluna correta — PGSG inclusive, "
            "não só o PLS — para saber a extensão do que muda antes de "
            "escrever para o texto."
        ),
        "resposta": """
### Resposta curta

**O PGSG praticamente não muda. Quem muda é o PLS, que melhora.** Por isso a
distância entre os dois cresce: de 5,7% para 9,1%.

Este relatório cobre a Tabela 1 e a Seção 4.2. **A Seção 5.2, a Tabela 2 e
as figuras estão na parte B** (`verificacao_3b_secao_5_2.md`), e lá está o
achado principal: as portas publicadas correspondem às da inicialização, e
o protocolo de treino que o artigo declara não alcança quatro dos oito
valores publicados.

### A Tabela 1 do Tecator, refeita nas duas colunas

As linhas de rede são **mediana [mínimo; máximo]** entre 10 réplicas. O
pipeline original não fixa semente em lugar nenhum, então cada execução dá
um número diferente e uma medida única não diria nada.

| linha | publicado (R²) | coluna 0 = água | coluna 1 = gordura |
|---|---|---|---|
| PLS | 0,919 | **0,919** | **0,946** |
| PLS, 5-fold | 0,921 | 0,922 | 0,955 |
| Ours (ANOVA), teste único | 0,941 | 0,922 [0,80; 0,96] | 0,922 [0,84; 0,94] |
| Ours (ANOVA), 5-fold | 0,862 | 0,869 [0,82; 0,89] | 0,868 [0,68; 0,89] |
| Ours (VIP) | 0,903 | 0,909 [0,89; 0,95] | 0,930 [0,89; 0,95] |
| Ours (RF) | 0,938 | 0,933 [0,86; 0,95] | 0,937 [0,91; 0,97] |
| Random init | 0,871 | 0,888 [0,77; 0,92] | 0,912 [0,79; 0,93] |
| Plain CNN | 0,235 | −0,019 [−2,59; 0,21] | 0,005 [−0,53; 0,17] |

**Validação do protocolo.** A coluna 0 reproduz o publicado: PLS teste único
dá 0,919 / 0,296, e PLS em 5-fold dá 0,922 contra os 0,921 do manuscrito. Isso
valida a **partição, o escalonamento, a seleção de coluna e o H** — que é o
que o PLS exercita. Não valida o laço de treino das redes: para elas, o
publicado apenas cai dentro da dispersão entre sementes. No caso da Plain
CNN, na cauda dela: com as 10 réplicas da tabela o R² publicado (0,235)
fica logo acima da maior (0,21); com 50 sementes, fica no percentil 96 —
dentro da faixa, perto do topo (segundo anexo,
`scripts/verificar_divergencia_redes.py`). Uma versão anterior deste
relatório dizia "fora da faixa", conclusão tirada de 10 sementes; a
correção foi apontada pela orientação em 01/10.

### O H do PLS teve de ser refeito

O manuscrito determina, na linha 386, que "*Reported PLS results use H\\*
throughout*", com H\\* pela regra de um erro-padrão sobre LOO no treino. O
**H = 10 é o H\\* da água**. Refazendo a regra para a gordura, com os mesmos
candidatos de 1 a 15:

| coluna | H\\* | R² no teste |
|---|---|---|
| 0, água | 10 | 0,919 |
| 1, gordura | **12** | **0,946** |

A implementação da regra se valida contra a saída do próprio autor: para a
coluna 0 ela reproduz `H_min = 14`, `RMSECV = 0,2093`, `SE = 0,0269`,
`H\\* = 10`, exatamente o que está em `revision_r1/one_se_output.txt`.

Isto corrige um número: com a gordura o PLS dá **0,946**, e não 0,9489 — este
último usa H = 10, que é o H da água.

### A distância entre o PGSG e o PLS

O manuscrito resume como "*a performance gap of approximately 6%*", comparando
o PGSG em 5-fold contra o PLS em teste único. O próprio manuscrito fornece o
número justo na linha 388 — PLS em 5-fold —, e a comparação correta é essa:

| | PLS 5-fold | PGSG 5-fold | lacuna |
|---|---|---|---|
| água | 0,922 | 0,869 | **5,7%** |
| gordura | 0,955 | 0,868 | **9,1%** |

A lacuna cresce cerca de 60%. **Não dobra** — a dispersão entre réplicas é
grande, e a mediana é a medida honesta aqui.

O mecanismo fica claro na comparação das réplicas: o PGSG em 5-fold vai de
0,869 (água) para 0,868 (gordura) — Wilcoxon pareado por semente p = 0,846,
Mann-Whitney p = 0,910. O pareamento aqui é legítimo: com a mesma semente as
camadas partem dos mesmos pesos (a porta vem do prior, sem sorteio) e as
folds são as mesmas; o Mann-Whitney vai junto para a conclusão não depender
disso. **Trocar o alvo não muda o PGSG.** O PLS,
que é determinístico, vai de 0,919 para 0,946. O aumento da distância vem
inteiramente do PLS.

A causa desse contraste não foi medida. Uma leitura plausível é que, com
ρ = −0,988 entre gordura e água, um modelo flexível atinge desempenho
equivalente prevendo qualquer das duas, enquanto o PLS, linear e calibrado
por H\\*, se beneficia do alvo com melhor estrutura linear. **Isto é
interpretação, não resultado**; o que a tabela mostra é o contraste, não a
sua razão.

### O prior ANOVA ganha da inicialização aleatória?

| coluna | ANOVA | aleatório | diferença | Mann-Whitney |
|---|---|---|---|---|
| 0, água | 0,922 | 0,888 | +0,033 | **p = 0,021** |
| 1, gordura | 0,922 | 0,912 | +0,010 | p = 0,307 |

Na coluna publicada a vantagem existe. Na gordura, não se distingue do ruído.
Com duas ressalvas. Os dois braços usam critérios de parada diferentes — o
ANOVA para por paciência, o aleatório roda as 200 épocas —, o que favorece o
primeiro. E são 10 sementes por braço: na gordura, a mediana do ANOVA em
teste único varia de 0,908 a 0,942 entre blocos de 10 sementes (segundo
anexo), então a comparação nessa coluna é frágil. Na água, a mesma mediana
fica entre 0,921 e 0,924.

### Divergência com a reprodução da orientação (01/10)

A orientação refez a reprodução de forma independente. **Bate exatamente**
em tudo o que é determinístico: coluna 0 = água; PLS 0,9191 / 0,2957;
RMSECV 0,2093 ± 0,0269 com H\\* = 10; gordura com H\\* = 12, 0,9462 /
0,2428. **Diverge em três braços de rede:**

| braço | esta reprodução | orientação |
|---|---|---|
| Plain CNN, gordura | 0,005 [−0,53; 0,17] | 0,410 [−0,02; 0,80] |
| PGSG 5-fold, gordura | 0,868 | 0,859 |
| PGSG ANOVA teste único, água | 0,922 | 0,932 |

Os quatro pontos de protocolo que ela pediu para conferir estão iguais aos
dela: `torch.manual_seed(s)` antes de instanciar o modelo, sementes 0 a 9;
`y` em 1-D na perda; a Plain CNN é o `BandSelectNet` do `band_select_net.py`,
com porta e prior; a paciência observa o teste no teste único e a fold no
5-fold.

Para saber se a diferença é só de semente, as mesmas linhas foram rodadas
com mais sementes, olhando a mediana de cada bloco de 10 (segundo anexo):

| braço | mediana por bloco de 10 sementes | orientação |
|---|---|---|
| ANOVA teste único, água (50 sementes) | 0,921 a 0,924 | 0,932 |
| PGSG 5-fold, gordura (30 sementes) | 0,868 a 0,876 | 0,859 |
| Plain CNN, gordura (50 sementes) | −0,001 a 0,071, máximo 0,17 | 0,410 |

Nos dois primeiros a diferença é pequena, mas fica fora da variação entre
blocos: provavelmente não é só a escolha das sementes. Na Plain CNN a
distribuição desta reprodução é **incompatível** com a dela — em 50
sementes nenhum treino passa de 0,17. Além da receita original, nove
variações de protocolo foram testadas nesse braço: 100 épocas, sem parada,
paciência 30, weight decay, a receita do modelo leve, lr 0,001, o prior da
água, o `y` sem padronizar e voltar ao melhor estado no teste. A mais
próxima, voltar ao melhor estado, dá mediana 0,161. Nenhuma chega a 0,41.

**Em aberto.** Sem o script da orientação, não dá para saber de que lado
está a diferença. Ela não afeta o PLS, nem as portas não treinadas, nem a
conclusão sobre a Seção 5.2.

### Ressalvas obrigatórias sobre estes números

1. **Nenhuma linha desta tabela é medida limpa de desempenho.** Os braços de
   teste único param observando o RMSE do próprio conjunto de teste, e o
   modelo final é o da última época. A linha de 5-fold tem o mesmo problema
   contra a fold de validação, e além disso usa um prior calculado sobre os
   172 do treino, que contêm as folds de validação. Reproduzi o protocolo
   como está, sem corrigir: o objetivo é medir o efeito do alvo com todo o
   resto igual.
2. **Duas réplicas colapsam** na coluna da gordura (uma fold cai para ~0). Por
   isso a tabela usa mediana; a média ficaria vários pontos deslocada.
3. **O desvio publicado do PLS em 5-fold não corresponde a nada.** O
   manuscrito registra 0,921 ± 0,018; a saída do próprio autor registra
   0,9218 ± 0,0439 nas mesmas folds. O desvio-padrão das cinco folds é
   0,0439 com ddof = 0 e 0,0491 com ddof = 1, e nenhum dos dois é 0,018 —
   valores a que a orientação chegou de forma independente.
4. **O prior também foi calculado sobre a água.** O `compute_priors.py`
   mapeia `'Fat'` para a coluna 0 (`{'Fat': 0, 'Water': 1, 'Protein': 2}`),
   então o arquivo `tecator_fat_anova.npy` do artigo é o prior da umidade —
   não só os resultados, o prior ANOVA, VIP e RF também. Achado da
   orientação, em 01/10. Nesta reprodução os priors são calculados sobre a
   coluna de cada linha da tabela: a coluna 0 com o prior da água, a coluna
   1 com o da gordura.
5. **A afirmação de semente fixa.** A linha 390 do manuscrito diz que os
   experimentos usam semente fixa 42 e que sementes diferentes produzem
   variação "<0,02 em R²". Nenhum script do pipeline do Tecator chama
   `torch.manual_seed`, e o braço ANOVA em teste único varia de 0,80 a 0,96
   entre as réplicas.
""",
    },
    "5.2": {
        "script": "scripts/verificar_secao52_pgsg.py",
        "extras": ["scripts/verificar_varredura_treino.py",
                   "scripts/verificar_kl_secao34.py"],
        "arquivo": "verificacao_3b_secao_5_2.md",
        "titulo": "Verificação 3, parte B — o que muda na Seção 5.2, na "
                  "Fig. 1 e no argumento de interpretabilidade",
        "pedido": (
            "…E atinge a Seção 5.2, que é o argumento central de "
            "interpretabilidade. […] Isso precisa ser reformulado, não só "
            "corrigido. […] Rode o pipeline completo com a coluna correta — "
            "PGSG inclusive, não só o PLS — para saber a extensão do que "
            "muda antes de escrever para o texto."
        ),
        "resposta": """
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
uma medida.

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
""",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qual", choices=sorted(VERIFICACOES))
    a = ap.parse_args()
    v = VERIFICACOES[a.qual]

    scripts = [v["script"], *v.get("extras", [])]
    anexos = []
    for i, script in enumerate(scripts, 1):
        print(f"rodando {script} ...", flush=True)
        r = subprocess.run(
            [sys.executable, script],
            cwd=RAIZ, capture_output=True, text=True,
            env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr, file=sys.stderr)
            raise SystemExit(f"{script} saiu com codigo {r.returncode}")
        nome = "Anexo" if len(scripts) == 1 else f"Anexo {i}"
        anexos.append(f"""## {nome} — saída de `{script}`

Reproduzível com:

```bash
python {script}
```

```
{r.stdout.rstrip()}
```
""")

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    texto = f"""# {v['titulo']}

*Rodrigo Fernandes — {hoje}*

> **O que foi pedido:** {v['pedido']}

{v['resposta'].strip()}

---

""" + "\n".join(anexos)
    SAIDA.mkdir(exist_ok=True)
    destino = SAIDA / v["arquivo"]
    destino.write_text(texto, encoding="utf-8")
    print(f"escrito: {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
