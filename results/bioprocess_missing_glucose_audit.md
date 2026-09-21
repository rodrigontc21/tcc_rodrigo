# Distribuição dos espectros sem glicose do bioprocess (ADR 007)

Gerado por `scripts/audit_bioprocess_missing_glucose.py`.

Espectros: 6960, sem glicose: 488. Amostras (linhas vizinhas com os 8 alvos idênticos): 5089, sem glicose: 355.

## 1. Concentração por split (por amostra)

| split | sem glicose / amostras | % |
|---|---|---|
| train | 217/3155 | 6.88% |
| validation | 97/1269 | 7.64% |
| test | 41/665 | 6.17% |

Qui-quadrado: χ² = 1.59, p = 0.45 (gl = 2). Contando espectros: χ² = 3.24, p = 0.20.

## 2. Blocos

Sequência mais longa de amostras consecutivas sem glicose: 3. Permutação dentro de cada split (10000 rodadas, semente 0): mediana 3, P(sequência ≥ 3) = 0.80.

## 3. Condição experimental

Ausência simultânea de cada outro alvo nas amostras sem glicose, contra a taxa basal em todas as amostras:

| alvo | sem glicose | basal |
|---|---|---|
| Glycerol | 6.2% | 3.8% |
| Acetate | 5.9% | 7.1% |
| EnPump | 0.3% | 1.1% |
| Nitrate | 1.4% | 1.8% |
| Yeast_Extract | 1.4% | 1.2% |
| total_phosphate | 0.0% | 0.0% |
| total_sulfate | 0.0% | 0.0% |

Mann-Whitney bicaudal, Bonferroni × 7, α = 0.05.

### amostra_vizinha

| alvo | média sem glicose | média com glicose | p | p Bonferroni | significativo |
|---|---|---|---|---|---|
| Glycerol | 5.1320 | 5.5259 | 0.504 | 1 | não |
| Acetate | 0.8320 | 0.8679 | 0.38 | 1 | não |
| EnPump | 1.3936 | 0.7618 | 7.24e-05 | 0.000506 | sim |
| Nitrate | 0.1130 | 0.0932 | 0.205 | 1 | não |
| Yeast_Extract | 0.5061 | 0.4376 | 0.018 | 0.126 | não |
| total_phosphate | 4.5968 | 3.9138 | 1.78e-06 | 1.25e-05 | sim |
| total_sulfate | 2.0555 | 2.0594 | 0.51 | 1 | não |

### espectro

| alvo | média sem glicose | média com glicose | p | p Bonferroni | significativo |
|---|---|---|---|---|---|
| Glycerol | 4.8918 | 5.5810 | 0.0884 | 0.619 | não |
| Acetate | 0.8349 | 0.8704 | 0.317 | 1 | não |
| EnPump | 1.4169 | 0.7605 | 1.14e-06 | 7.97e-06 | sim |
| Nitrate | 0.1135 | 0.0930 | 0.121 | 0.85 | não |
| Yeast_Extract | 0.5524 | 0.4414 | 0.00024 | 0.00168 | sim |
| total_phosphate | 4.6722 | 3.8996 | 2.95e-10 | 2.06e-09 | sim |
| total_sulfate | 2.0906 | 2.0578 | 0.26 | 1 | não |

### composicao_adr009

| alvo | média sem glicose | média com glicose | p | p Bonferroni | significativo |
|---|---|---|---|---|---|
| Glycerol | 4.9350 | 5.6628 | 0.194 | 1 | não |
| Acetate | 0.8342 | 0.8687 | 0.484 | 1 | não |
| EnPump | 1.4287 | 0.7713 | 0.000659 | 0.00462 | sim |
| Nitrate | 0.1144 | 0.0943 | 0.292 | 1 | não |
| Yeast_Extract | 0.5570 | 0.4477 | 0.0107 | 0.0751 | não |
| total_phosphate | 4.7108 | 3.9545 | 1.03e-05 | 7.18e-05 | sim |
| total_sulfate | 2.0981 | 2.0601 | 0.377 | 1 | não |

`composicao_adr009` tem 3433 composições, das quais 1599 aparecem em mais de um split da fonte; por isso a checagem 1 não se aplica a esse agrupamento.
