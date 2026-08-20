# Diário de bordo

## 2026-08-20

**Feito**
- Estrutura do repositório criada (docs/src/tests/notebooks/results)
- Ambiente virtual configurado + bibliotecas básicas instaladas
- Git local + repositório remoto no GitHub conectados, primeiro commit e push
- Notebook exploratório: primeiro contato com o Tecator

**Problema resolvido**
Python 3.14 quebrava o scikit-fda: o módulo `distutils` foi removido a partir
do 3.12 e a dependência `skdatasets` ainda o utiliza. Migrado o venv para
Python 3.12.10. As duas versões convivem no sistema.

**Observações do dado (Tecator via scikit-fda)**
- X: (215, 100) — 215 amostras, 100 bandas
- Eixo espectral: 850 a 1050 nm
- Alvos disponíveis: fat, water, protein
- fat: 0.9 a 49.1% | water: 39.3 a 76.6% | protein: 11.0 a 21.8%
- Espectros têm formato muito parecido entre si, com pico dominante em ~975 nm
  (O–H, água) e um ombro discreto em ~930 nm (C–H, gordura — a região que o
  modelo do grupo prioriza)
- Distribuição do alvo é irregular, concentrada em 5–15% com cauda até 50%.
  Reforça a necessidade de múltiplas partições (10 seed_split do protocolo)

**Pendência aberta**
O paper (pgsg_0) descreve a gordura variando de 7% a 76%, mas a fonte que
carreguei dá 0.9% a 49.1%. Provável variante diferente do dataset (o Tecator
circula em versões com 215 e 240 amostras). Investigar no Estágio 1 —
candidato a ADR sobre proveniência dos dados.

**Próximo**
Estágio 0 — protocolo de avaliação único, interface `Arm`, contrato `Result`,
dois eixos de semente.