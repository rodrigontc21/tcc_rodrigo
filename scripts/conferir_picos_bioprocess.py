"""Quantos espectros do bioprocess têm um pico estreito como o da linha 3208? (19/11/2026)

A linha 3208 derrubou o CARS fiel em duas partições: um pico de duas bandas,
cinco vezes mais alto que o normal, numa réplica só. Aqui conto quantos
espectros têm um pico parecido, comparando cada espectro com a réplica
(a outra medida da mesma mistura, mesmo valor de referência):

- diferença entre o espectro e a mediana das outras réplicas do grupo,
  depois do SNV;
- pico = banda em que essa diferença passa de um limiar, num trecho
  estreito (no máximo 5 bandas seguidas acima da metade do limiar), e
  positivo (raio cósmico soma luz; não tira).

Limiares em unidades de SNV: 3, 5 e 10. Para comparar, a diferença típica
entre réplicas é dada pela mediana do máximo de |diferença| por espectro.

Piloto: decisão de método, nada daqui entra no texto.

Uso: python -B conferir_picos_bioprocess.py
"""

import sys
import warnings
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

LIMIARES = (3.0, 5.0, 10.0)
LARGURA_MAX = 5


def trechos(acima: np.ndarray) -> list[tuple[int, int]]:
    """Trechos contíguos de True, como (início, fim inclusive)."""
    out, ini = [], None
    for j, v in enumerate(acima):
        if v and ini is None:
            ini = j
        if not v and ini is not None:
            out.append((ini, j - 1))
            ini = None
    if ini is not None:
        out.append((ini, len(acima) - 1))
    return out


def main():
    from tcc.data import load
    from tcc.preprocessing import SNVPreprocessor

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ds = load("bioprocess")
    X = SNVPreprocessor().fit(ds.X).transform(ds.X)

    linhas = []  # (linha, altura, largura, banda, grupo)
    maximos = []
    sem_replica = 0
    for g in np.unique(ds.groups):
        idx = np.flatnonzero(ds.groups == g)
        if len(idx) < 2:
            sem_replica += len(idx)
            continue
        for i in idx:
            outros = idx[idx != i]
            d = X[i] - np.median(X[outros], axis=0)
            maximos.append(np.abs(d).max())
            j = int(np.argmax(d))
            altura = float(d[j])
            if altura < min(LIMIARES):
                continue
            meio = d > altura / 2
            (ini, fim), = [t for t in trechos(meio) if t[0] <= j <= t[1]]
            linhas.append((int(i), altura, fim - ini + 1, j, int(g)))

    maximos = np.asarray(maximos)
    print(f"{len(X)} espectros; {sem_replica} sem réplica (fora da conta)")
    print(f"diferença típica entre réplicas (mediana do máximo de |dif|): "
          f"{np.median(maximos):.2f}; percentil 99: {np.percentile(maximos, 99):.2f}")
    for t in LIMIARES:
        estreitos = [l for l in linhas if l[1] >= t and l[2] <= LARGURA_MAX]
        largos = [l for l in linhas if l[1] >= t and l[2] > LARGURA_MAX]
        print(f"pico acima de {t:>4}: {len(estreitos)} estreitos (≤ {LARGURA_MAX} bandas), "
              f"{len(largos)} largos")
    print("\nos estreitos acima de 3, do maior para o menor:")
    print("linha  altura  largura  banda  grupo")
    for i, a, w, j, g in sorted([l for l in linhas if l[2] <= LARGURA_MAX], key=lambda l: -l[1]):
        print(f"{i:5d}  {a:6.2f}  {w:7d}  {j:5d}  {g:5d}")


if __name__ == "__main__":
    main()
