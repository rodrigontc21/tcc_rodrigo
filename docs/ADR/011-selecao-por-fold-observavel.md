# ADR 011 — Seleção por fold observável

**Data:** 2026-09-28
**Status:** proposto

## Contexto

O pipeline é categórico sobre a armadilha central do Estágio 2: *"seleção
de variáveis dentro da validação cruzada, nunca antes dela. Selecionar
bandas usando todo o conjunto de treino e depois validar é vazamento, e é
o erro mais comum na literatura de seleção em quimiometria. Escreva um
teste que falhe se a seleção enxergar a partição de validação."* O mesmo
item está no checklist de reprodutibilidade.

Esse teste não é implementável com o contrato atual. Do lado de fora, um
braço honesto e um trapaceiro são indistinguíveis:

- ambos recebem `X_train` inteiro, e isso é correto — as folds servem à
  CV interna do braço, e o modelo final é legitimamente ajustado em todo
  o treino;
- a diferença está em qual subconjunto de linhas cada um usa para
  **escolher as bandas dentro de cada fold**, e isso não aparece em lugar
  nenhum: o `Result` carrega `selection` (reservado ao Estágio 4) e
  `band_scores`, ambos do ajuste final;
- qualquer perturbação aplicada de fora atinge os dois igualmente, porque
  as linhas de validação de um fold são linhas de treino dos outros.

É o mesmo buraco que o [ADR 001](001-folds-da-cv-interna-derivam-de-seed-split.md)
registrou e adiou explicitamente: *"nada no contrato obriga o braço a de
fato usar as folds injetadas — um braço que chame `cross_val_score(cv=5)`
do sklearn usaria splits próprios sem detecção, porque as folds não
aparecem no `Result`. Achado registrado, a resolver no Estágio 2."* O
`PROTOCOLO.md` repete o item em "Validação cruzada interna / Em aberto".

Há uma segunda motivação, independente do vazamento. O paper de
referência (pgsg_0, Seção 5.2) reporta que *"8 das 10 bandas do top-10
apareceram consistentemente no top-10 das seleções das 5 folds"*. O braço
B4 tem que reproduzir o modelo publicado dentro da dispersão entre
sementes (Estágio 3), e essa afirmação específica só é reproduzível se a
seleção por fold for observável. Ou seja, o campo é necessário de
qualquer forma; o teste anti-vazamento apenas o torna necessário mais
cedo.

## Decisão

`FittedArm` ganha a propriedade `cv_selections`:

```python
@property
def cv_selections(self) -> list[set[int]] | None:
    """Bandas escolhidas DENTRO de cada fold da CV interna, na ordem de
    `cv_folds`. `None` para braços sem seleção de variáveis."""
```

Segue a convenção já estabelecida pelo [ADR 002](002-rmse-cv-e-propriedade-de-fittedarm.md)
para `rmse_cv` e por `band_scores`: é propriedade do braço, não cálculo
de `evaluate`, porque só o braço sabe o que fez internamente. Braços sem
seleção (`pls_full`, `mlp_full`) devolvem `None` — o mesmo recorte que o
Estágio 4 do pipeline já faz ao excluí-los das métricas de seleção.

**`evaluate` não lê esse campo, e ele não entra no `Result`.** O Estágio
6 exige que as métricas sejam funções puras sobre `results/`, e auditoria
de fold não é métrica: é verificação de contrato, e vive nos testes. O
campo `selection` do `Result` continua reservado ao ajuste final, como o
Estágio 4 define.

**Verificador de localidade.** Um braço é honesto quando, para todo fold
`i`, `cv_selections[i]` depende apenas das linhas de `fold_train[i]`.
Isso é verificável por perturbação: corrompem-se as linhas de
`fold_val[i]`, reajusta-se, e a seleção do fold `i` tem que sair
idêntica. As seleções dos outros folds mudam, e devem mudar — aquelas
linhas são treino deles.

**O hiperparâmetro é fixado durante a verificação.** Com busca ativa, o
candidato escolhido depende de *todas* as folds (é isso que a CV faz), e
perturbar `fold_val[i]` poderia trocar o candidato e, por tabela, a
seleção do fold `i` — um falso positivo. Fixar o hiperparâmetro isola a
localidade da seleção da agregação da CV, que são coisas diferentes. O
`PLSArm` já tem esse modo (`n_components` fixo), usado pelo portão de
validação; os braços seletores seguem o mesmo padrão.

## Consequências

`src/tcc/arms/base.py` declara a propriedade; `MeanArm` e `PLSArm`
devolvem `None`, sem mudança de comportamento. Nenhum código de produção
lê o campo hoje, e `FittedArm` é um `Protocol` estrutural sem
`isinstance` em lugar nenhum, então a adição não quebra braço existente.

O verificador e os braços-sonda ficam em `tests/test_selection_leakage.py`,
no padrão já usado pelo projeto para invariantes de protocolo
(`RandomArm`, `SpyArm`, `FirstYArm`): uma sonda honesta e uma trapaceira,
com um teste afirmando que o verificador aprova a primeira e outro
afirmando que ele reprova a segunda. A segunda é a prova de que o teste
tem dentes — sem ela seria mais um invariante testado com braço
insensível ao mecanismo, que é o padrão de falha registrado em 25/08 e
28/08.

Todo braço com seleção (`ipls`, `cars`, `ga_pls`, `vip_threshold`) passa
a ter duas obrigações: preencher `cv_selections` e passar pelo
verificador. Fazer isso agora, antes dos braços existirem, é mais barato
que adaptar três braços em R a um contrato novo depois.

Limitação declarada: o campo é autodeclarado, como `n_fits` e `rmse_cv`.
Um braço que reporte `cv_selections` diferente do que de fato usou não é
detectável pelo protocolo. O verificador prova localidade do que foi
reportado, não que o relatado seja o executado. Reduzir isso exigiria
`evaluate` conduzir a CV interna no lugar do braço, o que quebraria o
ADR 002 e a diversidade de buscas entre métodos.

Fica fora do escopo deste ADR o outro lado do achado do ADR 001 — um
braço que ignore `cv_folds` e construa as próprias. O verificador confere
apenas a **contagem** — `cv_selections` com comprimento diferente de
`len(cv_folds)` denuncia o caso grosseiro. Ele não tem como conferir
correspondência entre as folds reportadas e as injetadas, porque
`cv_selections` carrega bandas, não índices de linha. Um braço que
construa as próprias folds no mesmo número continua indetectável.
