"""O nosso CARS reproduz o artigo nos dados do artigo?

Li et al. (2009), Seção 4.3: nos espectros de milho do instrumento m5
(80 amostras, 1100–2498 nm de 2 em 2 nm) com a umidade como y, o CARS
escolheu 1908 nm e 2108 nm em todas as 500 execuções ("the frequencies of
both are selected 500"), com RMSECV de 10 segmentos muito abaixo do PLS de
espectro completo (Tabela 2).

Os dados são o `corn_m51.mat` que os autores distribuem com o código
(libPLS 1.95 e `CARS.rar` do projeto `carspls`), fora do repositório. O
caminho vai como argumento.

Receita do artigo e do `carspls.m`: X e y só centrados, sem SNV; RMSECV de
10 segmentos, divididos como o `plscvfold.m` faz quando o `carspls.m` o
chama (amostras ordenadas por y e distribuídas em rodízio,
`groups = 1+rem(0:Mx-1,K)`); N = 100 execuções; razão 0,9 (a dos códigos).
O teto de componentes, que o artigo não informa, é varrido.

Uso: python -B verificar_cars_milho.py <corn_m51.mat> [<outro corn_m51.mat>]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from scipy.io import loadmat

from tcc.arms.base import Budget
from tcc.arms.cars import run_cars, subset_rmsecv

REPETICOES = 30
N_RUNS = 100
RATIO = 0.9
TETOS = (2, 5, 10)
COL_1908 = (1908 - 1100) // 2
COL_2108 = (2108 - 1100) // 2

caminhos = sys.argv[1:]
dados = [loadmat(c) for c in caminhos]
X = np.asarray(dados[0]["X"], dtype=float)
y = np.asarray(dados[0]["y"], dtype=float).ravel()
print(f"X {X.shape}, y {y.shape}, y de {y.min():.3f} a {y.max():.3f}")
for c, d in zip(caminhos[1:], dados[1:]):
    iguais = np.array_equal(d["X"], dados[0]["X"]) and np.array_equal(d["y"], dados[0]["y"])
    print(f"mesmos números em {Path(c).parent.name}/{Path(c).name}: {iguais}")

n = len(y)
ordem = np.argsort(y, kind="stable")  # o `sort` do MATLAB é estável
folds = []
for k in range(10):
    val = np.sort(ordem[k::10])  # posições k, k+10, ... na ordem de y
    folds.append((np.setdiff1d(np.arange(n), val), val))
cols = np.arange(X.shape[1])
for teto in TETOS:
    full, a_full = subset_rmsecv(X=X, y=y, columns=cols, max_ncomp=teto, folds=folds, budget=Budget())
    print(f"\nteto {teto}: PLS de espectro completo, RMSECV {full:.4f} com {a_full} componentes")
    ambas, rmsecvs, n_bandas, n_comp = 0, [], [], []
    for semente in range(REPETICOES):
        r = run_cars(
            X=X, y=y, folds=folds, n_runs=N_RUNS, ratio=RATIO, max_ncomp=teto,
            rng=np.random.default_rng(semente), budget=Budget(),
        )
        sel = r.selection
        ambas += COL_1908 in sel and COL_2108 in sel
        rmsecvs.append(r.rmsecv[r.best])
        n_bandas.append(len(sel))
        n_comp.append(r.n_components[r.best])
    print(f"  1908 e 2108 nm escolhidas juntas: {ambas} de {REPETICOES}")
    print(f"  RMSECV {np.mean(rmsecvs):.4f} ± {np.std(rmsecvs, ddof=1):.4f}, "
          f"bandas {np.mean(n_bandas):.1f} ± {np.std(n_bandas, ddof=1):.1f}, "
          f"componentes {np.mean(n_comp):.1f} ± {np.std(n_comp, ddof=1):.1f}")
    print(f"  bandas da repetição 0 (nm): {sorted(1100 + 2 * j for j in run_cars(X=X, y=y, folds=folds, n_runs=N_RUNS, ratio=RATIO, max_ncomp=teto, rng=np.random.default_rng(0), budget=Budget()).selection)}")

# Referência do artigo: Tabela 2 (corn moisture), RMSECV de 10 segmentos:
# PLS de espectro completo 0,0229 com 10 componentes; CARS-PLS 0,0006
# (média de 500 execuções). A coluna de desvios saiu embaralhada na
# extração do PDF, então só a média é comparada.
print("\nartigo, Tabela 2: PLS completo 0,0229 (10 componentes); CARS-PLS 0,0006")
