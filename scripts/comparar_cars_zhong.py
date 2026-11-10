"""O nosso CARS no protocolo de Zhong et al. (2023), no Gasoline.

Zhong et al. (2023), *Molecules* 28(15):5672, Tabela 3, Gasoline:
PLS completo RMSEP 0,180 (6 componentes); CARS-PLS RMSEP 0,240 (7
variáveis, 4 componentes). O protocolo deles, pela seção de métodos:
- espectros brutos, só centragem;
- 45 de calibração e 15 de validação pelo Kennard-Stone;
- componentes por leave-one-out, no menor RMSECV;
- uma execução do CARS.

Aqui:
- Kennard-Stone começando pela amostra mais perto da média, depois a mais
  distante das já escolhidas; as 45 primeiras são a calibração. Das
  variantes testadas em 06/11 (DIARIO), é a única que reproduz os três
  números do PLS completo da Tabela 3 com 6 componentes: RMSEC 0,150,
  RMSECV 0,252 e RMSEP 0,180. A do `ks.m` do libPLS (começa pelo par mais
  distante) dá RMSEP 0,199.
- Controle: o script imprime esses três números; se não baterem, a
  divisão não é a deles e a comparação não vale.
- CARS (`run_cars`) na calibração, com CV leave-one-out, N = 100 e razão
  0,9 (os códigos dos autores; o artigo não informa), teto 5 e 10, 20
  sementes. Modelo final só centrado com os componentes que o CARS
  escolheu, como o modo `fiel`.

Uso: python -B comparar_cars_zhong.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget
from tcc.arms.cars import run_cars
from tcc.data import load

PUBLICADO_PLS, PUBLICADO_CARS = 0.180, 0.240
SEMENTES = range(20)
TETOS = (5, 10)


def kennard_stone(X):
    """Kennard-Stone começando pela amostra mais perto da média (distância
    euclidiana); depois, a cada passo, a mais distante das já escolhidas."""
    sq = (X**2).sum(axis=1)
    D = np.maximum(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0)
    rank = [int(np.argmin(((X - X.mean(axis=0)) ** 2).sum(axis=1)))]
    out = [k for k in range(len(X)) if k not in rank]
    while out:
        min_d = D[np.ix_(rank, out)].min(axis=0)
        rank.append(out.pop(int(np.argmax(min_d))))
    return np.array(rank)


def rmsep(model, columns, X_val, y_val):
    return float(np.sqrt(np.mean((y_val - np.ravel(model.predict(X_val[:, columns]))) ** 2)))


ds = load("gasoline")
X, y = ds.X, ds.y
rank = kennard_stone(X)
cal, val = np.sort(rank[:45]), np.sort(rank[45:])
Xc, yc, Xv, yv = X[cal], y[cal], X[val], y[val]
loo = [(np.setdiff1d(np.arange(len(yc)), [i]), np.array([i])) for i in range(len(yc))]
todas = np.arange(X.shape[1])
print(f"gasoline {X.shape}: calibração {len(cal)}, validação {len(val)}; "
      f"y de validação {yv.min():.2f} a {yv.max():.2f}")

# Controle: os três números do PLS completo com 6 componentes (Tabela 3)
full6 = PLSRegression(n_components=6, scale=False).fit(Xc, yc)
rmsec6 = float(np.sqrt(np.mean((yc - np.ravel(full6.predict(Xc))) ** 2)))
press6 = 0.0
for tr, va in loo:
    m = PLSRegression(n_components=6, scale=False).fit(Xc[tr], yc[tr])
    press6 += float(((yc[va] - np.ravel(m.predict(Xc[va]))) ** 2).sum())
rmsecv6 = float(np.sqrt(press6 / len(yc)))
print(f"\ncontrole, PLS completo com 6 componentes: RMSEC {rmsec6:.3f}, RMSECV {rmsecv6:.3f}, "
      f"RMSEP {rmsep(full6, todas, Xv, yv):.3f}; publicado 0,150 / 0,252 / {PUBLICADO_PLS:.3f}")

for teto in TETOS:
    resultados = []
    for s in SEMENTES:
        r = run_cars(X=Xc, y=yc, folds=loo, n_runs=100, ratio=0.9, max_ncomp=teto,
                     rng=np.random.default_rng(s), budget=Budget())
        cols = np.sort(r.subsets[r.best])
        a = int(r.n_components[r.best])
        m = PLSRegression(n_components=a, scale=False).fit(Xc[:, cols], yc)
        resultados.append((rmsep(m, cols, Xv, yv), len(cols), a))
    e = np.array([x[0] for x in resultados])
    print(f"\nCARS, teto {teto}, {len(e)} sementes: RMSEP mediano {np.median(e):.3f}, "
          f"faixa [{e.min():.3f}; {e.max():.3f}]; <= {PUBLICADO_CARS} em {int((e <= PUBLICADO_CARS).sum())}"
          f"; variáveis medianas {np.median([x[1] for x in resultados]):.0f}, "
          f"componentes medianos {np.median([x[2] for x in resultados]):.0f}")
print(f"\npublicado: CARS RMSEP {PUBLICADO_CARS:.3f}, 7 variáveis, 4 componentes")
