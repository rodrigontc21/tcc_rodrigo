"""Is the early-training plateau caused by the gate's concentration?

Rodrigo reports that on Mango the article's recipe stalls: "with the gate, the
start is a plateau in which the patience of 30 runs out", and 114 of 570
trainings stopped by epoch 20.  If the plateau is a consequence of the
SATURATED gate -- at init one band carries ~22% of the mass, so fc1 sees a
nearly one-dimensional input until W1 moves -- then the plateau length depends
on the gate's concentration, and the stopping rule is NOT neutral across arms:
B4/B2 (saturated) would stall where B3 (uniform) does not.  That would make the
patience part of what Delta measures.

Measured here on the datasets at hand, by sweeping the logit scale c, which is
exactly a knob on gate concentration (c = 1 saturated, c = 0 uniform):

  best_epoch     epoch of the best stopping-fold RMSE (median over seeds)
  stopped_early  share of seeds whose best epoch <= patience (i.e. the run
                 never improved past the initial phase before patience expired)
  train_r2       fit on the rows that trained the network, at the best epoch
  plateau        stopping-fold RMSE at epochs 1/5/10/20, to see the shape

Design follows Rodrigo's protocol rather than the article's: the stopping set is
a held-out 20% of the training rows, never the test set, and the model kept is
the best epoch.  Gate exempt from L2, as agreed on 12/11.

Usage:
    python verify_plateau_vs_gate.py --repo <pgsg_0 repo> --dataset tecator --col 1
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.feature_selection import f_regression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--dataset", default="tecator", choices=["tecator", "gasoline"])
ap.add_argument("--col", type=int, default=1)
ap.add_argument("--seeds", type=int, default=10)
ap.add_argument("--epochs", type=int, default=200)
ap.add_argument("--patience", type=int, default=30)
ap.add_argument("--lr", type=float, default=0.01)
args = ap.parse_args()

REPO = Path(args.repo).resolve()
sys.path.insert(0, str(REPO / "src"))
from models.band_select_net_light import BandSelectNetLight  # noqa: E402

C_GRID = [1.0, 0.5, 0.3, 0.17, 0.10, 0.054, 0.026, 0.0]
PROBE = [1, 5, 10, 20]


def prepare():
    X = pd.read_csv(REPO / f"data/raw/{args.dataset}/spectra.csv").values
    y = pd.read_csv(REPO / f"data/raw/{args.dataset}/targets.csv").values
    Xtr, _, ytr, _ = train_test_split(X, y, test_size=0.2, random_state=42)
    # Rodrigo's design: a stopping fold carved out of the training rows
    Xf, Xs, yf, ys = train_test_split(Xtr, ytr, test_size=0.2, random_state=7)
    sx, sy = StandardScaler(), StandardScaler()
    return (sx.fit_transform(Xf), sx.transform(Xs),
            sy.fit_transform(yf)[:, args.col], sy.transform(ys)[:, args.col])


def anova_prior(X, y):
    f, _ = f_regression(X, np.ravel(y))
    return (f - f.min()) / (f.max() - f.min())


def run(prior, c, Xf, yf, Xs, ys, seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    m = BandSelectNetLight(len(prior), 1, prior, 16, 0.5)
    with torch.no_grad():
        m.gating.gates.mul_(c)

    rest = [p for n, p in m.named_parameters() if n != "gating.gates"]
    opt = optim.Adam([{"params": rest, "weight_decay": 1e-4},
                      {"params": [m.gating.gates], "weight_decay": 0.0}], lr=args.lr)

    Xa, ya = torch.FloatTensor(Xf), torch.FloatTensor(np.ravel(yf))
    Xb, yb = torch.FloatTensor(Xs), torch.FloatTensor(np.ravel(ys))
    crit = nn.MSELoss()
    best, best_ep, bad = float("inf"), 0, 0
    probe, best_state = {}, None
    for ep in range(1, args.epochs + 1):
        m.train()
        pred, _ = m(Xa)
        (crit(pred.squeeze(), ya) + 1e-3 * m.get_kl_loss()).backward()
        opt.step()
        opt.zero_grad()
        m.eval()
        with torch.no_grad():
            pv, _ = m(Xb)
            r = torch.sqrt(crit(pv.squeeze(), yb)).item()
        if ep in PROBE:
            probe[ep] = r
        if r < best:
            best, best_ep, bad = r, ep, 0
            best_state = {k: v.clone() for k, v in m.state_dict().items()}
        else:
            bad += 1
            if bad >= args.patience:
                break
    m.load_state_dict(best_state)
    m.eval()
    with torch.no_grad():
        pf, _ = m(Xa)
    return dict(best_ep=best_ep, best_rmse=best,
                train_r2=float(r2_score(np.ravel(yf), pf.squeeze().numpy())),
                probe=probe, last_ep=ep)


def main():
    Xf, Xs, yf, ys = prepare()
    prior = anova_prior(Xf, yf)
    name = ({0: "water", 1: "fat"}.get(args.col) if args.dataset == "tecator"
            else "octane")
    print("=" * 96)
    print(f" PLATEAU vs GATE CONCENTRATION -- {args.dataset}, {name},"
          f" {args.seeds} seeds, 1 thread")
    print("=" * 96)
    print(f"  fit rows {Xf.shape[0]}   stopping rows {Xs.shape[0]}   bands {Xf.shape[1]}")
    print(f"  recipe: lr {args.lr}, full batch, <= {args.epochs} epochs,"
          f" patience {args.patience}, best epoch kept")
    print(f"\n{'c':>7}{'top_g_0':>9}{'best_epoch':>12}{'<=patience':>12}"
          f"{'ran_to_end':>12}{'train_R2':>10}{'stop_RMSE':>11}"
          f"{'  stopping-fold RMSE at epoch 1/5/10/20':>40}")
    for c in C_GRID:
        rs = [run(prior, c, Xf, yf, Xs, ys, s) for s in range(args.seeds)]
        torch.manual_seed(0)
        m0 = BandSelectNetLight(len(prior), 1, prior, 16, 0.5)
        with torch.no_grad():
            m0.gating.gates.mul_(c)
            g0 = torch.softmax(m0.gating.gates / 5.0, 0).max().item()
        be = [r["best_ep"] for r in rs]
        early = float(np.mean([e <= args.patience for e in be]))
        full = float(np.mean([r["last_ep"] >= args.epochs for r in rs]))
        tr2 = float(np.median([r["train_r2"] for r in rs]))
        srm = float(np.median([r["best_rmse"] for r in rs]))
        pr = [np.median([r["probe"].get(p, np.nan) for r in rs]) for p in PROBE]
        print(f"{c:>7.3f}{g0:>9.4f}{int(np.median(be)):>12}{early:>12.0%}"
              f"{full:>12.0%}{tr2:>10.3f}{srm:>11.3f}"
              f"{'   ' + ' / '.join(f'{v:.3f}' for v in pr):>40}")

    print("\n  top_g_0     initial gate mass on the top band")
    print("  best_epoch  median epoch of the best stopping-fold RMSE")
    print("  <=patience  share of seeds whose best epoch never got past the patience window")
    print("  ran_to_end  share of seeds that used the whole epoch budget")
    print("  train_R2    fit on the rows that trained the network, at the best epoch")
    print("\n  If best_epoch and train_R2 fall as c rises, the saturated gate is what")
    print("  delays fitting, and the patience is then not neutral across arms.")


if __name__ == "__main__":
    main()
