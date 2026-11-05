"""Confere o vip_scores do projeto contra duas implementacoes em R.

plsVarSel::VIP (Mehmood, Liland et al.) e mdatools::vipscores, os dois
pacotes ja instalados para o iPLS e o GA-PLS (ADR 008). Os tres modelos
sao ajustados com autoescala, que e o que o PLSRegression do projeto faz.

Dados: os quatro conjuntos, com SNV, sem particao (aqui so a formula esta
em teste). No bioprocess usa as 500 primeiras linhas, para o R nao demorar.

Uso: python verificar_vip.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rpy2.robjects as ro
from rpy2.robjects import numpy2ri
from rpy2.robjects.packages import importr
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.vip import vip_scores
from tcc.data import load
from tcc.preprocessing import SNVPreprocessor

pls = importr("pls")
plsvarsel = importr("plsVarSel")
mdatools = importr("mdatools")
H = 5

for nome in ("tecator", "gasoline", "mango", "bioprocess"):
    ds = load(nome)
    X, y = ds.X, ds.y
    if nome == "bioprocess":
        X, y = X[:500], y[:500]
    X = SNVPreprocessor().fit(X).transform(X)

    nosso = vip_scores(PLSRegression(n_components=H).fit(X, y))

    with (ro.default_converter + numpy2ri.converter).context():
        conv = ro.conversion.get_conversion()
        # o mdatools exige y como matriz de uma coluna
        x_r, y_r = conv.py2rpy(X), conv.py2rpy(y.reshape(-1, 1))
    ro.globalenv["X"], ro.globalenv["y"] = x_r, y_r
    m = ro.r(f"pls::plsr(y ~ X, ncomp = {H}, scale = TRUE, method = 'oscorespls')")
    vip_plsvarsel = np.asarray(plsvarsel.VIP(m, H)).ravel()
    m2 = mdatools.pls(x_r, y_r, H, scale=True)
    vip_mdatools = np.asarray(mdatools.vipscores(m2, ncomp=H)).ravel()

    print(f"{nome}: p {X.shape[1]}, n {X.shape[0]}, H {H}")
    print(f"  media dos VIP^2 (deve ser 1): {np.mean(nosso**2):.12f}")
    print(f"  maior |nosso - plsVarSel|: {np.max(np.abs(nosso - vip_plsvarsel)):.2e}")
    print(f"  maior |nosso - mdatools| : {np.max(np.abs(nosso - vip_mdatools)):.2e}")
    for t in (0.8, 1.0, 1.2, 1.5):
        a, b, c = (int(np.sum(v >= t)) for v in (nosso, vip_plsvarsel, vip_mdatools))
        print(f"  bandas com VIP >= {t}: nosso {a}, plsVarSel {b}, mdatools {c}")
