"""Por que a rede falha no Mango? Diagnóstico só no treino (ADR 017, item 7).

Na varredura de `c` (12/11/2026), os braços de rede no Mango deram R² de
teste perto de 0,5, contra 0,86 do PLS completo, e muitos pararam nas
primeiras épocas. Este script procura a causa **sem olhar o teste**: a
partição e as folds são as do `evaluate()`, mas só se usam as linhas que
ajustam a rede e a fold de parada. O teste externo nem é separado em X/y.

Medidas, em unidades de y padronizado (RMSE 1 é prever a média do ajuste):
- RMSE de treino e RMSE na fold de parada, época a época;
- referência: o PLS completo (A1, regra de um erro-padrão nas folds do
  protocolo), ajustado nas mesmas linhas e medido na mesma fold de parada.

Variações da receita, uma de cada vez, no B4-limpo (e o B1 sem porta):
  receita     a do artigo (o braço como está)
  b1          sem porta
  sem_drop    dropout 0
  longo       até 2.000 épocas, paciência 2.000 (a curva inteira)

Uso: python -B diagnosticar_rede_mango.py [conjunto] [sementes, padrão 0,1,2,3,4]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import torch
import torch.nn.functional as F

from tcc.arms import gate as G
from tcc.arms.pls import PLSArm
from tcc.data import load
from tcc.preprocessing import SNVPreprocessor
from tcc.protocol import DEFAULT_N_SPLITS, DEFAULT_TEST_SIZE, _make_cv_folds, _split_train_test


def treino_e_parada(ds, s):
    """As linhas de ajuste e a fold de parada da `seed_split` s, como no `evaluate()`."""
    split_seed, cv_seed = np.random.SeedSequence(s).spawn(2)
    train_idx, _ = _split_train_test(ds.X.shape[0], DEFAULT_TEST_SIZE,
                                     np.random.default_rng(split_seed), groups=ds.groups)
    X = SNVPreprocessor().fit(ds.X[train_idx]).transform(ds.X[train_idx])
    y = ds.y[train_idx]
    groups = None if ds.groups is None else ds.groups[train_idx]
    folds = _make_cv_folds(len(train_idx), DEFAULT_N_SPLITS,
                           np.random.default_rng(cv_seed), groups=groups)
    return X, y, folds


def treinar(X, y, folds, variante, seed=0):
    fit_idx, stop_idx = folds[0]
    mx, sx = X[fit_idx].mean(0), X[fit_idx].std(0)
    sx = np.where(sx == 0, 1.0, sx)
    my, sy = y[fit_idx].mean(), y[fit_idx].std()
    T = lambda a: torch.as_tensor(a, dtype=torch.float32)
    Xf, Xs = T((X[fit_idx] - mx) / sx), T((X[stop_idx] - mx) / sx)
    yf, ys = T((y[fit_idx] - my) / sy), T((y[stop_idx] - my) / sy)

    arm = G.mlp_full() if variante == "b1" else G.gate_prior()
    torch.set_num_threads(1)
    net, _, _ = arm.initial_net((X[fit_idx] - mx) / sx, y[fit_idx], seed)
    if variante == "sem_drop":
        net.dropout.p = 0.0
    epocas, paciencia = (2000, 2000) if variante == "longo" else (G.MAX_EPOCHS, G.PATIENCE)
    rest = [p for n, p in net.named_parameters() if n != "gates"]
    grupos = [{"params": rest, "weight_decay": G.WEIGHT_DECAY}]
    if net.gated:
        grupos.append({"params": [net.gates], "weight_decay": 0.0})
    opt = torch.optim.Adam(grupos, lr=G.LR)

    hist_tr, hist_st = [], []
    best, best_ep, bad = float("inf"), 0, 0
    for ep in range(epocas):
        net.train()
        loss = F.mse_loss(net(Xf).squeeze(1), yf)
        if net.gated:
            loss = loss + G.KL_WEIGHT * net.kl()
        opt.zero_grad()
        loss.backward()
        opt.step()
        net.eval()
        with torch.no_grad():
            tr = torch.sqrt(F.mse_loss(net(Xf).squeeze(1), yf)).item()
            st = torch.sqrt(F.mse_loss(net(Xs).squeeze(1), ys)).item()
        hist_tr.append(tr)
        hist_st.append(st)
        if st < best:
            best, best_ep, bad = st, ep + 1, 0
        else:
            bad += 1
            if bad >= paciencia:
                break
    return best, best_ep, hist_tr, hist_st, (my, sy)


def pls_parada(X, y, folds):
    """O A1 nas mesmas linhas de ajuste, medido na mesma fold de parada."""
    from tcc.arms.base import Budget
    fit_idx, stop_idx = folds[0]
    # as folds internas do PLS vêm das outras quatro folds do protocolo
    pos = {int(i): k for k, i in enumerate(fit_idx)}
    inner = []
    for _, v in folds[1:]:
        val = np.array([pos[int(i)] for i in v])
        inner.append((np.setdiff1d(np.arange(len(fit_idx)), val), val))
    f = PLSArm().fit(X[fit_idx], y[fit_idx], inner, np.random.default_rng(0), Budget())
    sy = y[fit_idx].std()
    return float(np.sqrt(np.mean((f.predict(X[stop_idx]) - y[stop_idx]) ** 2)) / sy)


if __name__ == "__main__":
    conjunto = sys.argv[1] if len(sys.argv) > 1 else "mango"
    sementes = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0, 1, 2, 3, 4]
    ds = load(conjunto)
    print(f"{conjunto}: RMSE em y padronizado (1 = prever a média). Teste não usado.\n")
    for s in sementes:
        X, y, folds = treino_e_parada(ds, s)
        print(f"seed_split {s}: {len(folds[0][0])} linhas de ajuste, "
              f"{len(folds[0][1])} na fold de parada, {X.shape[1]} bandas; "
              f"PLS completo na parada: {pls_parada(X, y, folds):.3f}")
        for v in ("receita", "b1", "sem_drop", "longo"):
            best, ep, tr, st, _ = treinar(X, y, folds, v)
            marcos = [e for e in (1, 10, 50, 200, 500, 1000, 2000) if e <= len(tr)]
            curva = "  ".join(f"ép{e}: {tr[e-1]:.2f}/{st[e-1]:.2f}" for e in marcos)
            print(f"  {v:<9} melhor parada {best:.3f} na época {ep:>4} de {len(tr):>4}"
                  f"  | treino/parada  {curva}")
        print(flush=True)
