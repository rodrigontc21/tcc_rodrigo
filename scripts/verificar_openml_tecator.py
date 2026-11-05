"""Confronto do targets.csv contra uma fonte de fato independente: OpenML 505.

A verificacao 2 conferiu o targets.csv contra o fda.usc, e o scikit-fda le
do proprio fda.usc - entao aquilo mostrou que o resultado nao depende do
caminho de leitura, e nada alem. O OpenML 505 e uma distribuicao separada do
Tecator, derivada do arquivo original do StatLib, com as colunas nomeadas
moisture, fat, protein. Se a coluna 0 do targets.csv tambem casa com
'moisture' ali, a identificacao deixa de depender de uma unica fonte.

O OpenML 505 tem 240 amostras: as 215 do conjunto canonico e 25 de
extrapolacao. Este script nao assume quais sao as 215; confere.

Baixa o conjunto via sklearn.datasets.fetch_openml (cache em
~/scikit_learn_data). Nada do repositorio da orientacao e alterado.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.datasets import fetch_openml  # noqa: E402

PGSG = (
    Path.home()
    / "tcc/docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
)
SEP = "=" * 74


def titulo(t):
    print()
    print(SEP)
    print(f" {t}")
    print(SEP)
    print()


titulo("1. A FONTE: OPENML 505")
b = fetch_openml(data_id=505, as_frame=True, parser="auto")
f = b.frame
d = b.details
print(f"  nome {d.get('name')}, versao {d.get('version')}, "
      f"md5 {d.get('md5_checksum')}")
print(f"  formato {f.shape}")
abs_cols = [c for c in f.columns if c.startswith("absorbance_")]
y_cols = ["moisture", "fat", "protein"]
print(f"  colunas de espectro: {len(abs_cols)} ({abs_cols[0]} ... {abs_cols[-1]})")
print(f"  colunas de alvo, na ordem do arquivo: {[c for c in f.columns if c in y_cols]}")
Xo = f[abs_cols].to_numpy(dtype=float)
Yo = f[y_cols].to_numpy(dtype=float)
for i, c in enumerate(y_cols):
    print(f"    {c:<9} min {Yo[:, i].min():6.2f}  max {Yo[:, i].max():6.2f}")

titulo("2. QUAIS LINHAS DO OPENML SAO AS 215 DO targets.csv?")
X = pd.read_csv(PGSG / "data/raw/tecator/spectra.csv").to_numpy(dtype=float)
T = pd.read_csv(PGSG / "data/raw/tecator/targets.csv")
print(f"  targets.csv: {T.shape}, cabecalho {list(T.columns)}")
print(f"  spectra.csv: {X.shape}")
print()
n = len(X)
dif_x = np.abs(Xo[:n] - X).max()
print(f"  espectro: maior |OpenML[0:{n}] - spectra.csv| = {dif_x:.2e}")
# Posicao com posicao. (Buscar "a linha mais parecida" do OpenML para cada
# linha nao serve: o Tecator tem 22 espectros repetidos, e a busca devolve a
# primeira ocorrencia do repetido, nao a da mesma posicao.)
mesma_ordem = bool((np.abs(Xo[:n] - X).max(axis=1) == 0).all())
print(f"  cada linha do spectra.csv casa com a mesma posicao no OpenML: "
      f"{mesma_ordem}")
if mesma_ordem:
    print(f"  -> as {n} sao as {n} primeiras do OpenML, na mesma ordem; as "
          f"{len(Xo) - n} ultimas ficam de fora.")
else:
    raise SystemExit("  -> as linhas NAO estao na mesma ordem; a comparacao "
                     "posicional abaixo nao vale. Parar e investigar.")
Yo = Yo[:n]

titulo("3. CADA COLUNA DO targets.csv CONTRA CADA COLUNA DO OPENML")
print("  O OpenML nomeia as colunas; o targets.csv tambem. Elemento a")
print("  elemento, nas 215 linhas:")
print()
print(f"  {'targets.csv':>16}  {'OpenML':>9}  {'iguais':>8}  {'maior dif':>10}")
for j, rot in enumerate(T.columns):
    for i, c in enumerate(y_cols):
        iguais = int(np.isclose(T.iloc[:, j].to_numpy(float), Yo[:, i],
                                atol=1e-9, rtol=0).sum())
        dif = np.abs(T.iloc[:, j].to_numpy(float) - Yo[:, i]).max()
        marca = "  <==" if iguais == n else ""
        print(f"  {j} {rot:>14}  {c:>9}  {iguais:>4}/{n}  {dif:>10.2e}{marca}")
    print()

titulo("CONCLUSAO")
ok = {
    rot: c
    for j, rot in enumerate(T.columns)
    for i, c in enumerate(y_cols)
    if np.isclose(T.iloc[:, j].to_numpy(float), Yo[:, i], atol=1e-9, rtol=0).all()
}
for rot, c in ok.items():
    print(f"  coluna rotulada {rot!r:<10} no targets.csv = {c!r} no OpenML 505")
print()
ordem_conteudo = [ok.get(r) for r in T.columns]
if ordem_conteudo == y_cols:
    print("  O conteudo do targets.csv esta na ordem do OpenML (moisture,")
    print("  fat, protein), e o cabecalho gravado e "
          f"{', '.join(T.columns)}. A coluna rotulada")
    print(f"  {T.columns[0]!r} e a umidade - confirmado numa fonte independente")
    print("  do fda.usc.")
else:
    print(f"  correspondencia obtida: {dict(zip(T.columns, ordem_conteudo))}")
    print("  -> diferente da ordem moisture, fat, protein: ver a tabela acima.")
