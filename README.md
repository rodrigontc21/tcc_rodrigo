# 🔬 O que a porta espectral realmente contribui?

### Decomposição da vantagem preditiva de mecanismos de *gating* frente à seleção de variáveis clássica em quimiometria

![Status](https://img.shields.io/badge/status-em%20andamento-yellow)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Área](https://img.shields.io/badge/área-quimiometria%20%7C%20ML-purple)
![Licença](https://img.shields.io/badge/uso-acadêmico-lightgrey)

**🎓 Aluno:** Rodrigo Fernandes  
**👨‍🏫 Orientador:** Prof. Dr. Clarimar José Coelho  
**🏫 Instituição:** Pontifícia Universidade Católica de Goiás — Ciência da Computação

---

## 📖 Sobre o projeto

Modelos de *gating* espectral — redes neurais com uma camada de "porta" que pondera cada banda do espectro — têm sido propostos como alternativa interpretável ao **PLS** em espectroscopia NIR/Raman, reportando ganhos preditivos sobre a linha de base linear.

Esse ganho, porém, **nunca foi decomposto**. Um modelo desses muda três coisas ao mesmo tempo em relação ao PLS:

| | Muda de | Para |
|---|---|---|
| 🔁 | regressor linear | regressor não linear |
| ⚖️ | espectro cru | espectro ponderado |
| 🎯 | todas as bandas | seleção implícita de bandas |

Ninguém isolou qual dessas mudanças produziu o ganho. E a comparação de referência costuma ser feita contra o **PLS puro** — não contra os métodos clássicos de seleção de variáveis (iPLS, CARS, GA-PLS, VIP), que são o estado da prática em quimiometria.

> 💡 **A pergunta do trabalho:** dada a vantagem preditiva observada de um mecanismo de gating espectral sobre a linha de base linear, quanto dela é atribuível ao regressor não linear, quanto à ponderação espectral, quanto ao aprendizado da porta e quanto ao conhecimento prévio injetado — e o que resta quando o competidor é a seleção de variáveis clássica?

---

## 🧪 O experimento, resumido

Cada braço difere do vizinho por **exatamente uma característica**, o que torna cada diferença interpretável isoladamente.

| Braço | Regressor | Ponderação | Porta treinável | Init. da porta |
|:---:|---|:---:|:---:|---|
| **A1** | Linear (PLS) | ❌ | — | — |
| **B1** | Não linear (MLP) | ❌ | — | — |
| **B2** | Não linear (MLP) | ✅ | ❌ | prior |
| **B3** | Não linear (MLP) | ✅ | ✅ | uniforme |
| **B4** | Não linear (MLP) | ✅ | ✅ | prior *(modelo publicado)* |

### A decomposição

```
Δ não-linear    =  B1 − A1     →  contribuição do regressor não linear
Δ ponderação    =  B2 − B1     →  contribuição da ponderação fixa pelo prior
Δ aprendizado   =  B4 − B2     →  contribuição de tornar a porta treinável
Δ prior         =  B4 − B3     →  contribuição do conhecimento prévio injetado
Δ vs. clássico  =  B4 − max(iPLS, CARS, GA-PLS, VIP)
```

A soma dos três primeiros termos reconstitui, por construção, a diferença **B4 − A1** — exatamente o ganho reportado na literatura; o Δ prior é um contraste complementar, fora da soma. O trabalho consiste em mostrar como esse total se reparte.

Depois do parecer da orientação (01/10/2026), o B4 se desdobrou em **B4-fiel** (como no artigo) e **B4-limpo** (porta sem decaimento de peso), e entraram o **B5(c)** (porta inicial sem a saturação, com o fator `c` varrido) e o **B2'(c)** (a mesma porta, congelada). Detalhes em [`docs/PROTOCOLO.md`](docs/PROTOCOLO.md) e no [ADR 017](docs/ADR/017-bracos-neurais-no-protocolo.md).

---

## 🗂️ Estrutura do repositório

```
tcc_rodrigo/
├── 📁 docs/
│   ├── fontes/                       proposta, pipeline e paper de referência
│   ├── ADR/                          decisões de projeto registradas (001 a 021)
│   ├── estudo_rodrigo/               material de estudo pessoal, inclui PERGUNTAS.md
│   ├── DIARIO.md                     progresso dia a dia
│   ├── PROTOCOLO.md                  protocolo pré-registrado (provisório até o congelamento)
│   ├── checklist_reprodutibilidade.md  os dez itens do pipeline e onde está a prova
│   └── janelas_quimicas.md           bandas de atribuição química, com as fontes
├── 📁 src/tcc/                       código do pipeline
│   ├── data.py, protocol.py          dados e protocolo de avaliação (Estágios 0 e 1)
│   ├── arms/                         braços clássicos e neurais (Estágios 2 e 3)
│   ├── selection.py                  camada de seleção (Estágio 4)
│   ├── grid.py                       executor da grade (Estágio 5)
│   ├── metrics.py                    métricas (Estágio 6)
│   └── decomposition.py              decomposição e TOST (Estágio 7)
├── 📁 tests/                         testes automatizados
├── 📁 scripts/                       execuções avulsas (medições, conferências, piloto)
│   └── orientacao/                   scripts do orientador, guardados como chegaram
├── 📁 notebooks/                     exploração livre (não é entregável)
└── 📁 results/                       saída das execuções (só o que é citado fica versionado)
```

---

## 📚 Documentos de referência

| Documento | Papel |
|---|---|
| [`tcc_rodrigo.pdf`](docs/fontes/tcc_rodrigo.pdf) | Proposta de TCC — o **quê** e o **porquê** |
| [`pipeline_tcc_rodrigo.md`](docs/fontes/pipeline_tcc_rodrigo.md) | Guia de implementação — o **como** |
| [`pgsg_0_paper.pdf`](docs/fontes/pgsg_0_paper.pdf) | Paper do grupo — objeto de estudo, vira o braço **B4** |

---

## 📊 Conjuntos de dados

| Conjunto | Modalidade | Regime | Alvo |
|---|---|---|---|
| Gasoline | NIR | *n* muito pequeno | octanagem |
| Tecator | NIR | *n* pequeno | teor de gordura |
| Mango DMC v3 | NIR | *n* grande | matéria seca |
| Bioprocesso | Raman | *n* grande | concentração de glicose |

---

## 🛠️ Stack

`Python 3.12` · `NumPy` · `pandas` · `scikit-learn` · `SciPy` · `PyTorch` (CPU) · `statsmodels` · `R` + `rpy2` (`mdatools` para o iPLS, `GA` para o GA-PLS) · `pytest`

---

## ▶️ Como rodar

O projeto roda no Linux (desenvolvido no Ubuntu do WSL).

```bash
python3.12 -m venv ~/venv-tcc && source ~/venv-tcc/bin/activate
pip install -r requirements.txt
```

O iPLS e o GA-PLS usam o R (desenvolvido com o R 4.6.1), com os pacotes `mdatools` (0.16.0) e `GA` (3.2.5):

```bash
Rscript -e 'install.packages(c("mdatools", "GA"))'
```

Os testes (os dados são baixados na primeira execução):

```bash
python -m pytest
```

Os resultados dependem do número de threads; o protocolo fixa uma por processo (ver o ADR 017).

---

## ✅ Progresso

- [x] 🏗️ Estrutura do projeto
- [x] 0️⃣ Protocolo de avaliação único
- [x] 1️⃣ Camada de dados
- [x] 2️⃣ Braços clássicos *(iPLS, CARS, GA-PLS, VIP)*
- [x] 3️⃣ Braços neurais *(B1–B5, com B2' e os dois B4)*
- [x] 4️⃣ Camada de seleção
- [x] 5️⃣ Executor da grade
- [x] 6️⃣ Métricas
- [x] 7️⃣ Decomposição + TOST
- [ ] 📌 Congelamento do protocolo *(espera decisões da orientação)*
- [ ] 🧮 Grade final
- [ ] 8️⃣ Figuras e manuscrito

Os resultados das partições 0–29 são **piloto** (reservadas a decisões de método); a grade final usa `seed_split` ≥ 100. O que falta para o congelamento está em [`docs/checklist_reprodutibilidade.md`](docs/checklist_reprodutibilidade.md).

📌 Progresso detalhado em [`docs/DIARIO.md`](docs/DIARIO.md)