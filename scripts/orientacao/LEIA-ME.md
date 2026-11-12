# Scripts da orientação

Scripts enviados pelo orientador, Prof. Clarimar José Coelho, por mensagem.
Fazem parte do registro de reprodução: os relatórios e o DIARIO citam as
saídas deles. Versionados em 12/11/2026, com a autorização dele dada no
mesmo dia.

## Regras

- **Os originais não se alteram.** Cada arquivo aqui é o que chegou, byte a
  byte (o `.gitattributes` desliga a conversão de quebra de linha nesta
  pasta). Se for preciso mudar algo, a mudança vai para um arquivo novo,
  fora desta pasta, e o original fica intacto; senão as saídas citadas
  deixam de corresponder.
- **Os nomes são os originais.**
- O `--repo` desses scripts aponta para o código do artigo
  (`prior-guided-spectral-gating`), que fica fora do git, em
  `docs/fontes/prior-guided-spectral-gating-main/`.

## Os arquivos

| script | chegou em | o que mede | SHA-256 |
|---|---|---|---|
| `verify_plaincnn.py` | 29/10/2026 | a divergência da Plain CNN: erro na assinatura da fábrica ou receita de treino | `ecdcc64338c9dc6c30b58c2af64b6f02735c8625cbb2c5606b4685844ef0bf76` |
| `verify_wd_on_gate.py` | 30/10/2026 | se o deslocamento da porta é aprendizado ou decaimento de peso | `a7bf6f2093c02356b5b3d1304229c25f6ee31a9978b889ccfb174677ed2853b2` |
| `verify_tecator_replicates.py` | 09/11/2026 | as réplicas do Tecator (regra das três relações, ADR 009) | `90a8da2aa75291a5c9c3ad3eec2d6a751aa00fb140c56a17b79814bf8131fe50` |
| `verify_b5_logit_scale.py` | 12/11/2026 | a varredura do fator `c` dos logits iniciais do B5 | `9ba78973b41d12a992e2e7a6fc58351b5e5492f40deab438d952e551575a1bca` |

## Onde e como rodaram aqui

Máquina: Intel Core i5-13450HX, 16 threads, 24 GB de RAM; Ubuntu no WSL,
com o ambiente virtual `~/venv-tcc` (Python 3.12.3).

- **`verify_plaincnn.py` e `verify_wd_on_gate.py`:** rodados em 04/11/2026,
  duas vezes cada, fora do repositório e sem alteração, com resultado
  idêntico entre as rodadas. Ambiente: torch 2.14.1+cpu, numpy 2.5.2,
  scikit-learn 1.9.0 (DIARIO de 04/11). O mesmo script dá medianas
  diferentes nesta máquina e na do orientador num braço da Plain CNN; essa
  divergência é parte do achado e está no relatório
  `results/verificacao_3_pipeline_com_o_alvo_correto.md`. A saída do
  `verify_wd_on_gate.py` está no Anexo 4 de
  `results/verificacao_3b_secao_5_2.md`.
- **`verify_tecator_replicates.py`:** rodado em 10/11/2026, com os mesmos
  números da orientação (ADR 009, adendo de 10/11). As versões dos pacotes
  não foram anotadas no dia; o ambiente em 12/11 tinha torch 2.14.1+cpu,
  numpy 2.5.2, scikit-learn 1.9.0, pandas 3.0.5 e scipy 1.18.0.
- **`verify_b5_logit_scale.py`:** ainda não rodado aqui. Os números dele são
  da máquina do orientador e são piloto (PROTOCOLO, seção do B5).

## O que não está aqui

`scripts/verificar_pipeline_tecator.py` e
`scripts/verificar_varredura_treino.py` não são da orientação: são deste
trabalho e foram enviados a ela em 01/10/2026 (DIARIO de 01/10).
