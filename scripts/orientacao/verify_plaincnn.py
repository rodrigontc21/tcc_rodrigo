"""Isolate the Plain CNN divergence: factory-signature bug vs. training recipe.

Background. Two independent reproductions of Table 1 of
Chemom. Intell. Lab. Syst. 277 (2026) 105833 agreed on everything
deterministic but disagreed on the Plain CNN row: median R2 = 0.005 in the
audit (Rodrigo, 50 seeds, never above 0.17) against 0.410 in the second
reproduction. Nine protocol variations failed to close the gap.

The cause is not the recipe. The two model factories do not have the same
signature:

    create_model_light(n_bands, n_outputs=1, prior_path=None)
    create_model(n_bands, n_outputs=1, prior_type='anova', prior_path=None)

The second reproduction called both with the prior path as the third
positional argument. For the light model that is correct. For the heavy
model it lands in prior_type, leaving prior_path=None, so the gate is
initialised as randn(p)*0.01 -- no prior at all -- and the KL term is taken
against a uniform reference instead of the ANOVA prior.

This script crosses the two factors (gate initialisation x training recipe)
so the contribution of each is visible, and prints the gate statistics that
make the mechanism legible.

Usage:
    python verify_plaincnn.py --repo /path/to/prior-guided-spectral-gating
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
from models.band_select_net import BandSelectNet, create_model  # noqa: E402


def prepare(col):
    X = pd.read_csv(REPO / "data/raw/tecator/spectra.csv").values
    y = pd.read_csv(REPO / "data/raw/tecator/targets.csv").values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sx, sy = StandardScaler(), StandardScaler()
    Xtr, Xte = sx.fit_transform(Xtr), sx.transform(Xte)
    ytr, yte = sy.fit_transform(ytr), sy.transform(yte)
    return Xtr, Xte, ytr[:, col], yte[:, col]


def anova_prior(X, y):
    f, _ = f_regression(X, np.ravel(y))
    return (f - f.min()) / (f.max() - f.min())


def train(model, Xtr, ytr, Xte, yte, epochs, lr, klw, wd, patience):
    """The training loop of the published scripts: final model is last epoch."""
    Xa = torch.FloatTensor(Xtr); ya = torch.FloatTensor(np.ravel(ytr))
    Xb = torch.FloatTensor(Xte); yb = torch.FloatTensor(np.ravel(yte))
    crit = nn.MSELoss()
    opt = optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    best, bad = float("inf"), 0
    for _ in range(epochs):
        model.train()
        pred, _ = model(Xa)
        (crit(pred.squeeze(), ya) + klw * model.get_kl_loss()).backward()
        opt.step(); opt.zero_grad()
        model.eval()
        with torch.no_grad():
            pv, _ = model(Xb)
            r = torch.sqrt(crit(pv.squeeze(), yb)).item()
        if r < best:
            best, bad = r, 0
        else:
            bad += 1
            if bad >= patience:
                break
    model.eval()
    with torch.no_grad():
        pv, _ = model(Xb)
    return r2_score(np.ravel(yte), pv.squeeze().numpy())


# the two recipes
LIGHT_RECIPE = dict(epochs=200, lr=0.01, klw=1e-3, wd=1e-4, patience=30)   # train_light.py
HEAVY_RECIPE = dict(epochs=200, lr=0.01, klw=1e-4, wd=0.0, patience=20)    # train_proper.py


def with_prior(prior, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    return BandSelectNet(n_bands=100, n_outputs=1, prior_scores=prior)


def no_prior(prior, seed):
    """What create_model(100, 1, <path>) actually builds: prior_path stays None."""
    torch.manual_seed(seed); np.random.seed(seed)
    return create_model(100, 1, str(prior))  # path lands in prior_type


def band(v):
    a = np.array(v)
    return f"{np.median(a):>7.3f}  [{a.min():.2f}; {a.max():.2f}]"


print("=" * 78)
print(" PLAIN CNN (heavy BandSelectNet), Tecator -- gate init x training recipe")
print("=" * 78)
print(f"  {args.seeds} seeds per cell.  Published Table 1 value: 0.235\n")

for col, name in ((0, "column 0 = water (what was published)"),
                  (1, "column 1 = fat (the correct target)")):
    Xtr, Xte, ytr, yte = prepare(col)
    pr = anova_prior(Xtr, ytr)
    pth = Path("/tmp/_prior_col%d.npy" % col)
    np.save(pth, pr)

    print(f"  --- {name} ---")
    print(f"  {'gate init':<22}{'recipe':<16}{'median R2':>12}  {'range':<20}")
    for gate_label, mk in (("ANOVA prior", lambda s: with_prior(pr, s)),
                           ("randn*0.01 (no prior)", lambda s: no_prior(pth, s))):
        for rec_label, rec in (("train_proper", HEAVY_RECIPE),
                               ("train_light", LIGHT_RECIPE)):
            vals = [train(mk(s), Xtr, ytr, Xte, yte, **rec) for s in range(args.seeds)]
            print(f"  {gate_label:<22}{rec_label:<16}{band(vals)}")
    print()

# gate statistics behind the effect
print("=" * 78)
print(" WHY: the gate the heavy CNN starts from")
print("=" * 78)
Xtr, _, ytr, _ = prepare(1)
pr = anova_prior(Xtr, ytr)
for label, g in (("ANOVA prior", with_prior(pr, 0)),
                 ("randn*0.01", no_prior(Path("/tmp/_prior_col1.npy"), 0))):
    th = g.gating.gates.detach().numpy()
    gate = torch.softmax(torch.tensor(th) / 5.0, dim=0).numpy()
    print(f"  {label:<14} logits [{th.min():>7.2f}; {th.max():>6.2f}]"
          f"   top gate {gate.max():.4f}   on the top band {100*gate.max():.1f}% of the weight")
    print(f"  {'':<14} bands with |logit| > 10: {100*np.mean(np.abs(th) > 10):.1f}%"
          f"   gate entropy {-(gate*np.log(gate+1e-12)).sum():.3f} (max {np.log(100):.3f})")
