"""Is the measured gate displacement learning, or is it weight decay?

train_light.py passes model.parameters() to Adam with weight_decay=1e-4, and
model.parameters() includes the gate logits. L2 on a logit pulls it toward
zero, and for a softmax gate theta -> 0 means the gate -> uniform. So part
of the 1.45-1.92 logit displacement measured under the article's protocol
may be shrinkage rather than anything learned from the spectra.

(train_proper.py, the heavy-CNN arm, uses Adam without weight decay, so the
two arms are not comparable on this axis either.)

The discriminating statistics, per seed:

  shrink_frac   fraction of bands whose |theta| decreased. Pure shrinkage
                drives this to 1; data-driven movement has no reason to
                prefer one direction, so it sits near 0.5.
  rho_shrink    correlation between the displacement and -theta_initial.
                Pure shrinkage is displacement = -c*theta, giving rho -> 1.

Three conditions: weight decay as published, none at all, and on the MLP
only (the surgical version, which is what the article presumably intended).

Usage:
    python verify_wd_on_gate.py --repo /path/to/prior-guided-spectral-gating
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

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--seeds", type=int, default=10)
args = ap.parse_args()

REPO = Path(args.repo).resolve()
sys.path.insert(0, str(REPO / "src"))
from models.band_select_net_light import BandSelectNetLight  # noqa: E402


def prepare(col):
    X = pd.read_csv(REPO / "data/raw/tecator/spectra.csv").values
    y = pd.read_csv(REPO / "data/raw/tecator/targets.csv").values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sx, sy = StandardScaler(), StandardScaler()
    return (sx.fit_transform(Xtr), sx.transform(Xte),
            sy.fit_transform(ytr)[:, col], sy.transform(yte)[:, col])


def anova_prior(X, y):
    f, _ = f_regression(X, np.ravel(y))
    return (f - f.min()) / (f.max() - f.min())


def run(prior, Xtr, ytr, Xte, yte, seed, wd_mode):
    """Article protocol: lr 0.01, 200 epochs, patience 30 on test, KL 1e-3."""
    torch.manual_seed(seed); np.random.seed(seed)
    m = BandSelectNetLight(100, 1, prior, 16, 0.5)
    th0 = m.gating.gates.detach().numpy().copy()

    if wd_mode == "published":          # what train_light.py does
        opt = optim.Adam(m.parameters(), lr=0.01, weight_decay=1e-4)
    elif wd_mode == "none":
        opt = optim.Adam(m.parameters(), lr=0.01, weight_decay=0.0)
    elif wd_mode == "mlp_only":         # gate exempt from L2
        gate = [m.gating.gates]
        rest = [p for n, p in m.named_parameters() if n != "gating.gates"]
        opt = optim.Adam([{"params": rest, "weight_decay": 1e-4},
                          {"params": gate, "weight_decay": 0.0}], lr=0.01)
    else:
        raise ValueError(wd_mode)

    Xa = torch.FloatTensor(Xtr); ya = torch.FloatTensor(np.ravel(ytr))
    Xb = torch.FloatTensor(Xte); yb = torch.FloatTensor(np.ravel(yte))
    crit = nn.MSELoss()
    best, bad = float("inf"), 0
    for _ in range(200):
        m.train()
        pred, _ = m(Xa)
        (crit(pred.squeeze(), ya) + 1e-3 * m.get_kl_loss()).backward()
        opt.step(); opt.zero_grad()
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

    d = th1 - th0
    shrink_frac = float(np.mean(np.abs(th1) < np.abs(th0)))
    rho_shrink = float(np.corrcoef(d, -th0)[0, 1])
    return dict(
        max_disp=float(np.abs(d).max()),
        med_disp=float(np.median(np.abs(d))),
        shrink_frac=shrink_frac,
        rho_shrink=rho_shrink,
        top_gate=float(g.numpy().max()),
        r2=r2_score(np.ravel(yte), pv.squeeze().numpy()),
    )


def agg(rows, k):
    a = np.array([r[k] for r in rows])
    return f"{np.median(a):>6.3f} [{a.min():.3f}; {a.max():.3f}]"


print("=" * 86)
print(" GATE DISPLACEMENT UNDER THE ARTICLE'S PROTOCOL: learning or weight decay?")
print("=" * 86)
print(f"  Light model, Tecator, {args.seeds} seeds.  median [min; max]")
print("  shrink_frac = fraction of bands whose |logit| decreased "
      "(1.0 = pure shrinkage, ~0.5 = no preferred direction)")
print("  rho_shrink  = corr(displacement, -theta_initial)  "
      "(1.0 = displacement is exactly proportional shrinkage)\n")

for col, name in ((0, "column 0 = water (as published)"),
                  (1, "column 1 = fat")):
    Xtr, Xte, ytr, yte = prepare(col)
    pr = anova_prior(Xtr, ytr)
    print(f"  --- {name} ---")
    print(f"  {'weight decay':<14}{'max |disp|':>16}{'median |disp|':>18}"
          f"{'shrink_frac':>18}{'rho_shrink':>18}{'test R2':>18}")
    for mode, label in (("published", "1e-4 (all)"),
                        ("none", "0"),
                        ("mlp_only", "1e-4, MLP only")):
        rows = [run(pr, Xtr, ytr, Xte, yte, s, mode) for s in range(args.seeds)]
        print(f"  {label:<14}{agg(rows,'max_disp'):>16}{agg(rows,'med_disp'):>18}"
              f"{agg(rows,'shrink_frac'):>18}{agg(rows,'rho_shrink'):>18}"
              f"{agg(rows,'r2'):>18}")
    print()
