"""B5: does descaling the initial logits actually give the gate mobility back?

The protocol's criterion for the descaling factor c reads: make the initial
top-to-second logit gap "of the order of the displacement training achieves".
That criterion is circular if the achievable displacement itself depends on c,
and it has no solution if the c that permits reordering also flattens the gate
into B3.  Both questions are empirical, so they are measured here.

For each c, two arms at the SAME initial gate, differing only in the gradient:

  B2'(c)  gate frozen at softmax(c * theta_0 / tau)
  B5(c)   same initial gate, trainable, EXEMPT from L2 (as proposed for B4-clean)

c = 1 recovers B4-clean / B2; c = 0 recovers B3 (uniform init).  Note that any
c > 0 preserves the prior's band ORDERING exactly -- scaling logits is monotone.
What c changes is the concentration of gate mass, not which band ranks first.

Reported per c:
  gap_0          initial top-to-second logit gap (= c * 11.6 on Tecator fat)
  top_g_0        initial gate mass on the top band
  max_disp       largest |theta_final - theta_initial| over bands
  top_changed    fraction of seeds where the top band is not the prior's argmax
  top10_kept     how many of the initial top-10 bands are still in the final top-10
  rho_disp       correlation of the displacement vector between seed pairs
                 (the H4 control: high means the movement is reproducible)
  R2 frozen / trainable, and Delta = trainable - frozen (the H8 quantity)

Training recipe is the article's (lr 0.01, 200 epochs, patience 30 on test,
KL 1e-3), so max_disp at c = 1 is comparable to the 0.30 measured on 30/10.

Usage:
    python verify_b5_logit_scale.py --repo /path/to/prior-guided-spectral-gating
"""

from __future__ import annotations

import argparse
import itertools
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

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--seeds", type=int, default=10)
ap.add_argument("--col", type=int, default=1, help="1 = fat (the correct target)")
ap.add_argument("--dataset", default="tecator", choices=["tecator", "gasoline"])
args = ap.parse_args()

REPO = Path(args.repo).resolve()
sys.path.insert(0, str(REPO / "src"))
from models.band_select_net_light import BandSelectNetLight  # noqa: E402

TAU = 5.0
C_GRID = [1.0, 0.5, 0.3, 0.17, 0.10, 0.054, 0.026, 0.0]


def prepare(col):
    X = pd.read_csv(REPO / f"data/raw/{args.dataset}/spectra.csv").values
    y = pd.read_csv(REPO / f"data/raw/{args.dataset}/targets.csv").values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sx, sy = StandardScaler(), StandardScaler()
    return (sx.fit_transform(Xtr), sx.transform(Xte),
            sy.fit_transform(ytr)[:, col], sy.transform(yte)[:, col])


def anova_prior(X, y):
    f, _ = f_regression(X, np.ravel(y))
    return (f - f.min()) / (f.max() - f.min())


def run(prior, c, trainable, Xtr, ytr, Xte, yte, seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    m = BandSelectNetLight(len(prior), 1, prior, 16, 0.5)
    with torch.no_grad():                      # descale the initial logits
        m.gating.gates.mul_(c)
    th0 = m.gating.gates.detach().numpy().copy()

    rest = [p for n, p in m.named_parameters() if n != "gating.gates"]
    if trainable:
        opt = optim.Adam([{"params": rest, "weight_decay": 1e-4},
                          {"params": [m.gating.gates], "weight_decay": 0.0}], lr=0.01)
    else:
        m.gating.gates.requires_grad_(False)
        opt = optim.Adam([{"params": rest, "weight_decay": 1e-4}], lr=0.01)

    Xa, ya = torch.FloatTensor(Xtr), torch.FloatTensor(np.ravel(ytr))
    Xb, yb = torch.FloatTensor(Xte), torch.FloatTensor(np.ravel(yte))
    crit = nn.MSELoss()
    best, bad = float("inf"), 0
    for _ in range(200):
        m.train()
        pred, _ = m(Xa)
        (crit(pred.squeeze(), ya) + 1e-3 * m.get_kl_loss()).backward()
        opt.step()
        opt.zero_grad()
        m.eval()
        with torch.no_grad():
            pv, _ = m(Xb)
            r = torch.sqrt(crit(pv.squeeze(), yb)).item()
        if r < best:
            best, bad = r, 0
        else:
            bad += 1
            if bad >= 30:
                break
    m.eval()
    with torch.no_grad():
        pv, g = m(Xb)
    th1 = m.gating.gates.detach().numpy()
    gp = g.numpy()
    d = th1 - th0
    return dict(
        r2=float(r2_score(np.ravel(yte), pv.squeeze().numpy())),
        disp=d,
        max_disp=float(np.abs(d).max()),
        top_band=int(np.argmax(gp)),
        top10=set(np.argsort(gp)[-10:].tolist()),
        top10_0=set(np.argsort(th0)[-10:].tolist()),
        top_g0=float(torch.softmax(torch.tensor(th0) / TAU, 0).numpy().max()),
    )


def main():
    Xtr, Xte, ytr, yte = prepare(args.col)
    prior = anova_prior(Xtr, ytr)
    lg = np.log(np.clip(prior, 1e-7, 1 - 1e-7) / (1 - np.clip(prior, 1e-7, 1 - 1e-7)))
    srt = np.sort(lg)[::-1]
    gap1 = srt[0] - srt[1]
    prior_top = int(np.argmax(prior))
    raw_top_mass = float(prior.max() / prior.sum())

    name = ({0: "water", 1: "fat"}.get(args.col, f"col {args.col}")
            if args.dataset == "tecator" else "octane")
    print("=" * 94)
    print(f" B5: DESCALING THE INITIAL LOGITS -- {args.dataset}, {name}, light model,"
          f" {args.seeds} seeds")
    print("=" * 94)
    print(f"  initial top-to-second logit gap at c = 1:        {gap1:.2f}")
    print(f"  Adam's budget over 200 steps at lr 0.01:         ~2.0 (ceiling, not a measurement)")
    print(f"  gate-exempt displacement measured on 30/10:      ~0.30")
    print(f"  prior's argmax band:                             {prior_top}")
    print(f"  top mass if the RAW prior were normalised to 1:  {raw_top_mass:.4f}")
    print(f"\n  c for gap = Adam ceiling (~2.0):   {2.0 / gap1:.3f}")
    print(f"  c for gap = measured displacement (~0.30): {0.30 / gap1:.3f}")
    print("\n  NOTE: any c > 0 preserves the prior's band ordering exactly."
          "\n  What c changes is the concentration of gate mass, not the ranking.")

    print("\n" + "=" * 94)
    print(" THE SWEEP")
    print("=" * 94)
    hdr = (f"{'c':>7}{'gap_0':>8}{'top_g_0':>9}{'max_disp':>10}{'disp/gap':>10}"
           f"{'top chg':>9}{'top10 kept':>12}{'rho_disp':>10}"
           f"{'R2 frozen':>11}{'R2 train':>10}{'Delta':>9}")
    print(hdr)
    rows = []
    for c in C_GRID:
        fr = [run(prior, c, False, Xtr, ytr, Xte, yte, s) for s in range(args.seeds)]
        tr = [run(prior, c, True, Xtr, ytr, Xte, yte, s) for s in range(args.seeds)]
        D = np.array([t["disp"] for t in tr])
        rho = [float(np.corrcoef(D[i], D[j])[0, 1])
               for i, j in itertools.combinations(range(len(D)), 2)]
        md = float(np.median([t["max_disp"] for t in tr]))
        chg = float(np.mean([t["top_band"] != prior_top for t in tr]))
        kept = float(np.median([len(t["top10"] & t["top10_0"]) for t in tr]))
        r2f = float(np.median([f["r2"] for f in fr]))
        r2t = float(np.median([t["r2"] for t in tr]))
        g0 = fr[0]["top_g0"]
        gap_c = c * gap1
        ratio = md / gap_c if gap_c > 0 else np.inf
        print(f"{c:>7.3f}{gap_c:>8.2f}{g0:>9.4f}{md:>10.3f}"
              f"{(f'{ratio:.2f}' if np.isfinite(ratio) else '  inf'):>10}"
              f"{chg:>9.0%}{kept:>12.0f}{np.median(rho):>10.3f}"
              f"{r2f:>11.3f}{r2t:>10.3f}{r2t - r2f:>+9.3f}")
        rows.append((c, gap_c, g0, md, ratio, chg, kept, np.median(rho), r2f, r2t))

    print("\n  gap_0      initial top-to-second logit gap")
    print(f"  top_g_0    initial gate mass on the top band (uniform = {1/len(prior):.4f})")
    print("  disp/gap   displacement divided by the gap: > 1 means the top is reachable")
    print("  top chg    share of seeds whose final top band is not the prior's argmax")
    print("  top10 kept median overlap between the initial and final top-10 (of 10)")
    print("  rho_disp   median correlation of the displacement vector between seed pairs")
    print("  Delta      R2(trainable) - R2(frozen): the H8 quantity at this c")

    print("\n" + "=" * 94)
    print(" IS THE CRITERION CIRCULAR?")
    print("=" * 94)
    print("  If max_disp were independent of c, the criterion would have a fixed point")
    print("  computable from the c = 1 measurement alone.  Observed max_disp by c:")
    for c, gap_c, g0, md, ratio, *_ in rows:
        print(f"    c = {c:<6.3f} gap {gap_c:>6.2f}   max_disp {md:.3f}")
    mds = [r[3] for r in rows]
    print(f"\n  max_disp ranges {min(mds):.3f} to {max(mds):.3f} across the grid"
          f" (factor {max(mds) / max(min(mds), 1e-9):.1f}).")


if __name__ == "__main__":
    main()
