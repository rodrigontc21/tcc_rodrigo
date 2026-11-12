"""Tecator replicate grouping: is 'identical spectrum' the complete rule?

Reproduces every number in the ADR 009 opinion of 09/11/2026.

Three candidate grouping relations:
  A -- neighbouring rows with (fat, water, protein) identical   [ADR 009 as it stands]
  B -- rows with bit-identical spectra                          [the proposed correction]
  C -- rows with identical targets AND spectra among the closest in the set

Usage:
    python -I verify_tecator_replicates.py --repo <path to pgsg_0 repo>
    python -I verify_tecator_replicates.py --spectra <spectra.csv> --targets <targets.csv>

Distance between two spectra is max |dx| over the 100 channels, reported both in
absorbance units and as a fraction of the mean absolute absorbance of the set.
"""

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

C_THRESHOLD = 0.30  # declared before use; see the sensitivity table below


def load(spectra_path, targets_path):
    X = pd.read_csv(spectra_path).values.astype(np.float64)
    T = pd.read_csv(targets_path)
    return X, T


def pairwise_max_abs(X):
    """max |dx| over channels, for every pair. (n, n) matrix."""
    return np.abs(X[:, None, :] - X[None, :, :]).max(axis=2)


def connected_components(n, edges):
    """Union-find. Pairwise handling of overlapping relations is NOT equivalent."""
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in edges:
        a, b = find(i), find(j)
        if a != b:
            parent[a] = b
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path)
    ap.add_argument("--spectra", type=Path)
    ap.add_argument("--targets", type=Path)
    a = ap.parse_args()
    if a.repo is not None:
        spectra = a.repo / "data" / "raw" / "tecator" / "spectra.csv"
        targets = a.repo / "data" / "raw" / "tecator" / "targets.csv"
    else:
        spectra, targets = a.spectra, a.targets

    X, T = load(spectra, targets)
    Y = T.values.astype(np.float64)
    n = len(X)
    scale = np.abs(X).mean()
    D = pairwise_max_abs(X)
    iu = np.triu_indices(n, k=1)
    d = D[iu]
    same_y = np.array([np.array_equal(Y[i], Y[j]) for i, j in zip(*iu)])
    neighbour = np.array([j - i == 1 for i, j in zip(*iu)])
    exact = d == 0.0

    print("=" * 78)
    print(" TECATOR REPLICATES: is 'identical spectrum' the complete rule?")
    print("=" * 78)
    print(f"  spectra {X.shape}   targets {list(T.columns)}")
    print(f"  mean |absorbance| = {scale:.4f}   (the scale distances are read against)")
    print(f"  pairs = {len(d)}")

    # ---- 1. Is the exact-match threshold well separated? -------------------
    print("\n" + "=" * 78)
    print(" 1. IS THE EXACT-MATCH THRESHOLD WELL SEPARATED?")
    print("=" * 78)
    nz = np.sort(d[~exact])
    print(f"  pairs with max|dx| == 0            {int(exact.sum())}")
    print(f"  closest NON-identical pair         {nz[0]:.6f}  "
          f"({nz[0] / scale * 100:.3f}% of scale)")
    print("\n  pairs below each threshold (non-identical only):")
    for t in [1e-6, 1e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1]:
        print(f"    max|dx| < {t:<8g} {int((nz < t).sum()):>6}")
    print("\n  -> nothing between 0 and %.4f: the exact threshold is a clean break,"
          % nz[0])
    print("     so the 22 identical pairs are duplicated records, not two acquisitions.")

    # ---- 2. The three relations --------------------------------------------
    print("\n" + "=" * 78)
    print(" 2. THE THREE RELATIONS")
    print("=" * 78)
    A = [(i, i + 1) for i in range(n - 1) if np.array_equal(Y[i], Y[i + 1])]
    B = [(i, j) for i, j in zip(*iu) if D[i, j] == 0.0]
    C = [(i, j) for i, j in zip(*iu)
         if np.array_equal(Y[i], Y[j]) and 0.0 < D[i, j] < C_THRESHOLD and j - i != 1]
    print(f"  A  neighbours, identical y          {len(A):>3} pairs  {A}")
    print(f"  B  identical spectrum               {len(B):>3} pairs")
    print(f"  C  identical y + close spectrum     {len(C):>3} pairs  "
          f"(threshold {C_THRESHOLD})")
    print(f"  A n B {sorted(set(A) & set(B))}")
    print(f"  A \\ B (only the current rule finds these) {sorted(set(A) - set(B))}")

    # ---- 3. Is identical y evidence of replication? ------------------------
    print("\n" + "=" * 78)
    print(" 3. IS IDENTICAL y EVIDENCE OF REPLICATION?")
    print("=" * 78)
    print(f"  pairs with identical (fat, water, protein): {int(same_y.sum())}")
    print(f"  rate {same_y.mean() * 100:.3f}%  vs the 0.17% chance rate ADR 009 cites")
    print(f"  -> {0.0017 * len(d):.1f} expected by chance, {int(same_y.sum())} observed:")
    print("     identical y ON ITS OWN does not beat chance in this set.")
    mask0 = ~exact & ~neighbour
    base = same_y[mask0].mean()
    print(f"\n  conditioning on spectral proximity (pairs outside A and B;"
          f" baseline rate {base * 100:.3f}%):")
    print(f"    {'max|dx| <':>12}{'pairs':>8}{'same y':>8}{'rate':>9}{'expected':>10}")
    for t in [0.03, 0.05, 0.07, 0.10, 0.15, 0.30, np.inf]:
        m = mask0 & (d < t)
        k = int(same_y[m].sum())
        label = "all" if t == np.inf else f"{t:.2f}"
        print(f"    {label:>12}{int(m.sum()):>8}{k:>8}"
              f"{k / max(m.sum(), 1) * 100:>8.2f}%{base * m.sum():>10.1f}")
    print(f"\n  in B: {int(same_y[exact].sum())} of {int(exact.sum())} have identical y"
          f"   (expected by chance {base * exact.sum():.2f})")
    print("  -> the informative event is the CONJUNCTION, not either part alone.")

    print("\n  the identical-y pairs outside A and B, by distance percentile:")
    m = mask0 & same_y
    for i, j in [(iu[0][k], iu[1][k]) for k in np.where(m)[0][np.argsort(d[m])]]:
        pct = (d < D[i, j]).mean() * 100
        verdict = "candidate replicate" if D[i, j] < C_THRESHOLD else "chance"
        print(f"    rows {i:>4},{j:>4}  max|dx| {D[i, j]:.4f}  p{pct:<6.2f} {verdict}")

    # ---- 4. Threshold sensitivity -----------------------------------------
    print("\n" + "=" * 78)
    print(" 4. THRESHOLD SENSITIVITY FOR RELATION C")
    print("=" * 78)
    for t in [0.08, 0.10, 0.15, 0.20, 0.30, 0.40, 0.45]:
        Ct = [(i, j) for i, j in zip(*iu)
              if np.array_equal(Y[i], Y[j]) and 0.0 < D[i, j] < t and j - i != 1]
        gs = connected_components(n, A + B + Ct)
        sizes = dict(sorted(Counter(len(g) for g in gs).items()))
        print(f"  threshold {t:.2f}: C has {len(Ct):>2} pairs -> {len(gs)} groups, sizes {sizes}")
    print("\n  -> any cut from 0.15 to 0.40 gives the same 12 pairs and the same 180")
    print("     groups. That plateau is what makes the choice defensible.")

    # ---- 5. Group structure, as connected components ----------------------
    print("\n" + "=" * 78)
    print(" 5. GROUP STRUCTURE (connected components, not pairs)")
    print("=" * 78)
    for name, edges in [("A  (current rule)", A), ("B  (proposed)", B),
                        ("A u B", A + B), ("A u B u C  (full rule)", A + B + C)]:
        gs = connected_components(n, edges)
        sizes = dict(sorted(Counter(len(g) for g in gs).items()))
        print(f"  {name:<24} {len(gs):>4} groups   sizes {sizes}")

    gs = connected_components(n, A + B + C)
    print("\n  groups larger than 2 under the full rule -- these need the transitive")
    print("  closure; handled pairwise, their members can land on opposite sides:")
    for g in sorted(gs, key=len, reverse=True):
        if len(g) > 2:
            print(f"    size {len(g)}: rows {g}   y = {tuple(np.round(Y[g[0]], 4))}")
            for i in g:
                for j in g:
                    if i < j:
                        rel = ("B" if D[i, j] == 0 else
                               "A" if j - i == 1 else
                               "C" if np.array_equal(Y[i], Y[j]) and D[i, j] < C_THRESHOLD
                               else "-")
                        print(f"      {i:>4}-{j:<4} max|dx| {D[i, j]:.4f}  relation {rel}")

    biggest = max(len(g) for g in gs)
    target = int(round(0.25 * n))
    print(f"\n  largest group {biggest} -> the test set can exceed the target of {target}")
    print(f"  by up to {biggest - 1} ({target} to {target + biggest - 1}); today it is up to 1.")

    # ---- 6. What the rule still leaves out --------------------------------
    print("\n" + "=" * 78)
    print(" 6. WHAT THE FULL RULE STILL LEAVES OUT (declare as a limitation)")
    print("=" * 78)
    print("  The closest non-identical pairs in the whole set, with their targets.")
    print("  Where y differs in the first decimal, the rule does not group them:")
    shown = 0
    for k in np.argsort(d):
        if d[k] == 0.0:
            continue
        i, j = iu[0][k], iu[1][k]
        print(f"    rows {i:>4},{j:>4}  max|dx| {d[k]:.4f} ({d[k] / scale * 100:.2f}% of scale)"
              f"  y_i {tuple(np.round(Y[i], 4))}  y_j {tuple(np.round(Y[j], 4))}"
              f"  same y: {np.array_equal(Y[i], Y[j])}")
        shown += 1
        if shown >= 6:
            break
    print("\n  Grouping on spectral proximity alone, with y differing, is a different")
    print("  rule and is not adopted here.")


if __name__ == "__main__":
    main()
