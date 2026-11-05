"""Confere, rodando, o que o plsVarSel::ga_pls (0.10.0) faz.

Lendo o codigo (plsVarSel:::evaluateX e genalg::rbga.bin) apareceram quatro
pontos. Este script refaz o ga_pls por dentro, com os mesmos defaults
(GA.threshold 10, popSize 100, iters 5), para ver a populacao final e as
avaliacoes, que o ga_pls nao devolve:

1. a selecao final e o cromossomo com MAIS variaveis, nao o de menor PRESS;
2. o PRESS vem de plsr(validation = "CV"), com folds aleatorias do pls;
3. o PRESS e sempre o de 4 componentes (ncomp = min(5, k), indice ncomp - 1);
4. cromossomo com menos de 2 variaveis recebe PRESS fixo 100, que nao
   depende da escala de y.

Dados: Tecator com SNV, todas as amostras (aqui so o metodo esta em teste).

Uso: python verificar_ga_pls_plsvarsel.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rpy2.robjects as ro
from rpy2.robjects import numpy2ri
from rpy2.robjects.packages import importr

from tcc.data import load
from tcc.preprocessing import SNVPreprocessor

importr("pls")
importr("plsVarSel")
importr("genalg")

ds = load("tecator")
X = SNVPreprocessor().fit(ds.X).transform(ds.X)
with (ro.default_converter + numpy2ri.converter).context():
    conv = ro.conversion.get_conversion()
    ro.globalenv["X"] = conv.py2rpy(X)
    ro.globalenv["y"] = conv.py2rpy(ds.y)

out = ro.r("""
set.seed(1)
plsVarSel:::putPLSVarSelEnv("X", X); plsVarSel:::putPLSVarSelEnv("y", y)
res <- genalg::rbga.bin(size = ncol(X), zeroToOneRatio = 10,
                        evalFunc = plsVarSel:::evaluateX, popSize = 100, iters = 5)
pop <- res$population; ev <- res$evaluations
i_mais <- which.max(rowSums(pop))[1]   # o que o ga_pls devolve
i_melhor <- which.min(ev)
list(mais = c(sum(pop[i_mais, ]), ev[i_mais]),
     melhor = c(sum(pop[i_melhor, ]), ev[i_melhor]),
     faixa = range(rowSums(pop)),
     press_1 = plsVarSel:::evaluateX(c(1, rep(0, ncol(X) - 1))),
     press_todas = plsVarSel:::evaluateX(rep(1, ncol(X))))
""")
r = dict(zip(out.names, [np.asarray(v) for v in out]))
print("Tecator, SNV, set.seed(1), defaults do ga_pls")
print(f"  devolvido pelo ga_pls (mais variaveis): {int(r['mais'][0])} bandas, PRESS {r['mais'][1]:.1f}")
print(f"  menor PRESS da populacao final        : {int(r['melhor'][0])} bandas, PRESS {r['melhor'][1]:.1f}")
print(f"  bandas por cromossomo na populacao    : {int(r['faixa'][0])} a {int(r['faixa'][1])}")
print(f"  PRESS com todas as {X.shape[1]} bandas       : {float(r['press_todas'][0]):.1f}")
print(f"  PRESS de cromossomo com 1 banda       : {float(r['press_1'][0]):.1f} (valor fixo)")

rep = ro.r("""
f <- function(s) { set.seed(s); plsVarSel::ga_pls(y, X, iters = 2, popSize = 20)$ga.selection }
a <- f(7); b <- f(7); d <- f(8)
c(identical(a, b), identical(a, d))
""")
print(f"  mesma semente R, mesma selecao: {bool(rep[0])}; sementes 7 e 8, mesma selecao: {bool(rep[1])}")
