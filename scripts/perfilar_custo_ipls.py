"""Onde está o custo do iPLS no bioprocess: número de ajustes ou custo por ajuste?

Pedido da orientação em 30/10: "perfile antes de otimizar". O iPLS levou
9.059 s numa partição do bioprocess (DIARIO, 28/10). Este script decompõe esse
tempo sem rodar a busca inteira de novo.

Partição de `evaluate()` com `seed_split` 0 e SNV. `glob_ncomp` = 7, o
escolhido pela regra de um erro-padrão nessa mesma partição (DIARIO, 28/10).

Partes:
  1. Uma chamada do `mdatools::ipls` por candidato de `int_num`, no fold
     externo 0, como a busca faz: tempo, ajustes estimados e tempo por ajuste.
     Extrapolação para a busca inteira, a conferir contra os 9.059 s.
  2. Um ajuste PLS isolado na largura de cada candidato: mdatools contra
     `PLSRegression`, no mesmo bloco de linhas.
  3. Rprof de uma chamada (int_num 10, num Rscript à parte): em que
     funções do R o tempo vai.
  4. Paralelismo: K processos independentes ao mesmo tempo, cada um com a
     mesma chamada; tempo de parede contra K = 1.

Uso: python perfilar_custo_ipls.py [partes]   (padrão: 1234)
     python perfilar_custo_ipls.py --sonda INT_NUM   (uso interno da parte 4)
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.ipls import (
    DEFAULT_INT_NUM_CANDIDATES,
    _inner_folds,
    _r,
    _segments_from_folds,
    _select_intervals,
)
from tcc.data import load
from tcc.preprocessing import SNVPreprocessor
from tcc.protocol import DEFAULT_N_SPLITS, DEFAULT_TEST_SIZE, _make_cv_folds, _split_train_test

GLOB_NCOMP = 7
FOLD = 0


def fold_zero():
    """X, y do fold_train 0 e os segmentos internos, como `_fold_selections`."""
    ds = load("bioprocess")
    split_seed, cv_seed = np.random.SeedSequence(0).spawn(2)
    train_idx, _ = _split_train_test(
        n=ds.X.shape[0], test_size=DEFAULT_TEST_SIZE,
        rng=np.random.default_rng(split_seed), groups=ds.groups,
    )
    snv = SNVPreprocessor().fit(ds.X[train_idx])
    X_train, y_train = snv.transform(ds.X[train_idx]), ds.y[train_idx]
    cv_folds = _make_cv_folds(
        n_train=len(train_idx), n_splits=DEFAULT_N_SPLITS,
        rng=np.random.default_rng(cv_seed), groups=ds.groups[train_idx],
    )
    fold_train = cv_folds[FOLD][0]
    segments = _segments_from_folds(len(fold_train), _inner_folds(cv_folds, FOLD))
    return ds, X_train[fold_train], y_train[fold_train], segments


def one_call(X, y, segments, int_num):
    t0 = time.perf_counter()
    bands, n_fits, executed = _select_intervals(X, y, segments, int_num, GLOB_NCOMP)
    return time.perf_counter() - t0, n_fits, executed, len(bands)


if len(sys.argv) == 3 and sys.argv[1] == "--sonda":
    _, X, y, segments = fold_zero()
    seconds, *_ = one_call(X, y, segments, int(sys.argv[2]))
    print(f"{seconds:.1f}", flush=True)
    sys.exit(0)

parts = sys.argv[1] if len(sys.argv) > 1 else "1234"
ds, X, y, segments = fold_zero()
ro, numpy2ri, mdatools = _r()
print(f"bioprocess: X {ds.X.shape}, {len(np.unique(ds.groups))} grupos (ADR 009)")
print(f"fold_train {FOLD}: {X.shape[0]} linhas, {int(segments.max())} segmentos internos, "
      f"glob_ncomp {GLOB_NCOMP}")
print(f"R BLAS: {ro.r('extSoftVersion()[[\"BLAS\"]]')[0]}")
print(f"R LAPACK: {ro.r('La_library()')[0]}")
print(f"numpy threads: OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS')}, "
      f"CPUs visíveis {os.cpu_count()}\n", flush=True)

if "1" in parts:
    print("1. Uma chamada do mdatools::ipls por candidato (fold 0)")
    print(f"  {'int_num':>7} {'executado':>9} {'bandas sel.':>11} {'tempo (s)':>10} "
          f"{'ajustes est.':>12} {'ms/ajuste':>10}")
    per_call = {}
    for int_num in DEFAULT_INT_NUM_CANDIDATES:
        seconds, n_fits, executed, n_bands = one_call(X, y, segments, int_num)
        per_call[int_num] = seconds
        print(f"  {int_num:>7} {executed:>9} {n_bands:>11} {seconds:>10.1f} "
              f"{n_fits:>12} {1000 * seconds / n_fits:>10.1f}", flush=True)
    total = DEFAULT_N_SPLITS * sum(per_call.values())
    print(f"  extrapolação da busca (5 folds x 5 candidatos, supondo os folds "
          f"iguais ao 0): {total:.0f} s, sem a chamada final; medido em 28/10: "
          f"9.059 s no total\n", flush=True)

if "2" in parts:
    print("2. Um ajuste PLS isolado na largura de cada candidato (mesmas linhas)")
    print(f"  {'largura':>7} {'mdatools (ms)':>13} {'PLSRegression (ms)':>18}")
    with (ro.default_converter + numpy2ri.converter).context():
        y_r = ro.conversion.get_conversion().py2rpy(y.reshape(-1, 1))
    for int_num in DEFAULT_INT_NUM_CANDIDATES:
        width = X.shape[1] // int_num
        Xw = np.ascontiguousarray(X[:, :width])
        with (ro.default_converter + numpy2ri.converter).context():
            x_r = ro.conversion.get_conversion().py2rpy(Xw)
        reps = 20
        t0 = time.perf_counter()
        for _ in range(reps):
            mdatools.pls(x_r, y_r, ncomp=min(GLOB_NCOMP, width), scale=False)
        t_md = (time.perf_counter() - t0) / reps
        t0 = time.perf_counter()
        for _ in range(reps):
            PLSRegression(n_components=min(GLOB_NCOMP, width), scale=False).fit(Xw, y)
        t_sk = (time.perf_counter() - t0) / reps
        print(f"  {width:>7} {1000 * t_md:>13.1f} {1000 * t_sk:>18.1f}", flush=True)
    print()

RPROF_R = """
D <- commandArgs(trailingOnly = TRUE)[1]
X <- as.matrix(read.csv(file.path(D, "X.csv"), header = FALSE))
y <- matrix(scan(file.path(D, "y.csv"), quiet = TRUE), ncol = 1)
seg <- scan(file.path(D, "seg.csv"), quiet = TRUE)
suppressMessages(library(mdatools))
int_num <- 10
Rprof(file.path(D, "rprof.out"), interval = 0.02)
t <- system.time(ipls(X, y, glob.ncomp = %d, int.ncomp = min(%d, ncol(X) %%/%% int_num),
                      int.num = int_num, method = "forward", cv = seg,
                      silent = TRUE, scale = FALSE))
Rprof(NULL)
print(t)
s <- summaryRprof(file.path(D, "rprof.out"))
print(head(s$by.self, 15))
print(head(s$by.total, 25))
""" % (GLOB_NCOMP, GLOB_NCOMP)

if "3" in parts:
    # O Rprof chamado de dentro do rpy2 não amostra nada (medido em 04/11:
    # tabelas vazias), então esta parte roda num Rscript à parte, sobre o
    # mesmo fold gravado em CSV. int_num 10, o candidato mais rápido.
    import tempfile
    print("3. Rprof de uma chamada (int_num 10), num Rscript à parte")
    with tempfile.TemporaryDirectory() as tmp:
        np.savetxt(Path(tmp) / "X.csv", X, delimiter=",")
        np.savetxt(Path(tmp) / "y.csv", y, delimiter=",")
        np.savetxt(Path(tmp) / "seg.csv", segments, delimiter=",", fmt="%d")
        (Path(tmp) / "rprof.R").write_text(RPROF_R, encoding="utf-8")
        out = subprocess.run(["Rscript", str(Path(tmp) / "rprof.R"), tmp],
                             capture_output=True, text=True)
        print(out.stdout, out.stderr, flush=True)

if "4" in parts:
    print("4. Paralelismo: K processos ao mesmo tempo, cada um com a chamada int_num 30")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    base = None
    for k in (1, 2, 4, 8):
        t0 = time.perf_counter()
        procs = [
            subprocess.Popen([sys.executable, "-B", __file__, "--sonda", "30"],
                             stdout=subprocess.PIPE, text=True, env=env)
            for _ in range(k)
        ]
        inner = [float(p.communicate()[0].strip().splitlines()[-1]) for p in procs]
        wall = time.perf_counter() - t0
        base = base or wall
        print(f"  K={k}: parede {wall:7.1f} s, chamada em cada processo "
              f"{min(inner):.1f}-{max(inner):.1f} s, vazão {k * base / wall:.2f}x "
              f"a de K=1", flush=True)
