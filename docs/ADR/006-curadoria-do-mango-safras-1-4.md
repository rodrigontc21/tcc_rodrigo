# ADR 006 — Curadoria do Mango: safras 1–4

**Data:** 2026-09-14
**Status:** proposto

## Contexto

O conjunto Mango DMC v3 (Anderson et al., 2020) é distribuído no Mendeley
Data sob o identificador 46htwnp833. O arquivo em uso é
`MangoDMC_NIR_Data_v3.csv`, obtido da versão 6 do repositório (a mais
recente), com SHA-256 conferido contra o metadado publicado pelo Mendeley.

O CSV distribuído hoje tem **12.011 amostras**; os papers originais, que
cobrem as safras 1–4, reportam **11.691**. A diferença de 320 amostras é
uma quinta safra acrescentada numa atualização de 2024, posterior às
publicações.

Investigação local no CSV (14/09/2026) para fixar o critério de corte sem
adivinhação:

- A coluna de metadado que marca a safra é `Season`, com valores 1 a 5.
  A distribuição é: safra 1 = 3.914, safra 2 = 1.363, safra 3 = 4.966,
  safra 4 = 1.448, safra 5 = 320.
- A safra 5 corresponde exatamente ao rótulo `Set == "Val Ext 2"`. A
  correspondência entre `Season == 5` e `Set == "Val Ext 2"` foi
  verificada como bijetiva linha a linha (nenhuma amostra satisfaz um
  critério sem satisfazer o outro), então os dois critérios são
  intercambiáveis. As datas confirmam a leitura: a safra 5 é de setembro
  de 2019, posterior às safras 1–4 (2015 a 2018).
- Excluir a safra 5 deixa **exatamente 11.691 amostras**, batendo com o
  número reportado nos papers originais. Os três critérios testados
  (`Season != 5`, `Set != "Val Ext 2"`, `Season <= 4`) produzem o mesmo
  conjunto, sem discrepância a documentar.

## Decisão

Cortar o Mango para as amostras das safras 1–4, excluindo a safra 5, pelo
critério `Season != 5` (equivalente a `Set != "Val Ext 2"`, verificado),
restando 11.691 amostras. O corte é aplicado na camada de dados, antes de
qualquer avaliação.

Justificativa (orientação, 14/09/2026): alinhar com os papers originais
facilita a comparação externa no Estágio 2, que é onde valores publicados
serão necessários; ficar com as 12.011 dá mais dados, mas quebra a
comparabilidade.

## Consequências

O loader `_load_mango()` em `src/tcc/data.py` passa a aplicar o filtro —
hoje ele carrega o CSV como distribuído, com comentário explícito nesse
sentido. O pino `EXPECTED["mango"]` em `tests/test_data.py` muda de
12.011 para 11.691 amostras; o número de canais (306) e a unidade (nm)
não mudam. A faixa do alvo também não muda: DM vai de 9,46 a 24,58 tanto
antes quanto depois do corte (a safra 5 está contida nessa faixa, de
13,41 a 20,50), então só a contagem de amostras precisa ser atualizada.
O `sha256` do `Dataset` muda, por depender do conteúdo carregado.

Descartam-se 320 amostras válidas — perda deliberada de dado em troca de
comparabilidade com a literatura. Como o corte é por safra inteira, e não
por amostra, ele não introduz viés de seleção dentro das safras retidas.

O filtro **não** foi implementado nesta data: este ADR documenta o que
muda, pendente da aprovação da orientação sobre a redação exata. Enquanto
o status for "proposto", o código continua carregando as 12.011 amostras.
