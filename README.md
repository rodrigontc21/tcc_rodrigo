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

A soma dos quatro primeiros termos reconstitui, por construção, a diferença **B4 − A1** — exatamente o ganho reportado na literatura. O trabalho consiste em mostrar como esse total se reparte.

---

## 🗂️ Estrutura do repositório

```
tcc_rodrigo/
├── 📁 docs/
│   ├── fontes/          proposta, pipeline e paper de referência
│   ├── ADR/             decisões de projeto registradas
│   ├── DIARIO.md        progresso dia a dia
│   ├── PERGUNTAS.md     fila de dúvidas para a orientação
│   └── PROTOCOLO.md     protocolo pré-registrado (congela na semana 11)
├── 📁 src/tcc/          código do pipeline, um módulo por estágio
├── 📁 tests/            testes automatizados
├── 📁 notebooks/        exploração livre (não é entregável)
└── 📁 results/          saída das execuções (não versionado)
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

`Python` · `NumPy` · `pandas` · `scikit-learn` · `matplotlib` · `Jupyter` · `pytest`

---

## ✅ Progresso

- [x] 🏗️ Estrutura do projeto
- [ ] 0️⃣ Protocolo de avaliação único
- [ ] 1️⃣ Camada de dados
- [ ] 2️⃣ Braços clássicos *(iPLS, CARS, GA-PLS, VIP)*
- [ ] 3️⃣ Braços neurais *(B1–B4)*
- [ ] 4️⃣ Camada de seleção
- [ ] 5️⃣ Executor da grade
- [ ] 6️⃣ Métricas
- [ ] 7️⃣ Decomposição + TOST
- [ ] 8️⃣ Figuras e manuscrito

📌 Progresso detalhado em [`docs/DIARIO.md`](docs/DIARIO.md)