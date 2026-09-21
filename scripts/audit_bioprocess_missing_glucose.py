"""Distribuição dos 488 espectros sem glicose do bioprocess (ADR 007).

Reproduz a investigação exigida pela orientação antes de aceitar o ADR 007:
a ausência de rótulo de glicose é aleatória ou estruturada? Três checagens,
contando por AMOSTRA física (réplicas não são observações independentes):

1. Concentração por split: qui-quadrado da ausência contra a partição
   treino/validação/teste do cache da fonte.
2. Blocos: sequência mais longa de amostras consecutivas sem glicose, com
   teste de permutação (rótulos embaralhados dentro de cada split).
3. Condição experimental: Mann-Whitney dos outros 7 alvos entre amostras
   com e sem glicose, com correção de Bonferroni para as 7 comparações;
   e a ausência simultânea de cada outro alvo contra a taxa basal.

Agrupamentos:

- `amostra_vizinha` (principal): linhas vizinhas com os 8 alvos idênticos
  são a mesma amostra. É a definição do ADR 007 (5.089 amostras nos 6.960
  espectros).
- `espectro`: cada espectro conta como observação, só para mostrar a
  distorção que o ADR 007 registra.
- `composicao_adr009`: grupos do loader (ADR 009), mesma composição em
  qualquer posição. Só a checagem 3; a 1 não se aplica, porque uma mesma
  composição aparece em mais de um split da fonte.

A ordem das linhas do `raman_data` é treino, teste, validação; o script
confere isso contra os arquivos Arrow do cache antes de atribuir os splits.

Gera em results/:

- bioprocess_missing_glucose_audit.csv  uma linha por alvo e agrupamento
- bioprocess_missing_glucose_audit.md   resumo das três checagens
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyarrow as pa
import raman_data
from scipy.stats import chi2_contingency, mannwhitneyu

from tcc.data import DATA_DIR, _adjacent_replicate_groups, _composition_groups

CACHE_DIR = DATA_DIR / "raman_cache"
SPLITS_IN_ROW_ORDER = ("train", "test", "validation")
SPLITS_REPORTED = ("train", "validation", "test")
N_OTHER_TARGETS = 7
ALPHA = 0.05
PERMUTATION_SEED = 0

COLUMNS = [
    "agrupamento",
    "alvo",
    "n_sem_glicose",
    "n_com_glicose",
    "media_sem_glicose",
    "media_com_glicose",
    "U",
    "p",
    "p_bonferroni",
    "significativo",
]


def _read_split_targets(split: str, names: list[str]) -> np.ndarray:
    (arrow_path,) = CACHE_DIR.glob(
        f"chlange___substrate_mix_raman/default/0.0.0/*/substrate_mix_raman-{split}.arrow"
    )
    with pa.memory_map(str(arrow_path)) as source:
        try:
            table = pa.ipc.open_stream(source).read_all()
        except pa.ArrowInvalid:
            table = pa.ipc.open_file(source).read_all()
    return np.column_stack(
        [np.asarray(table.column(n).to_numpy(zero_copy_only=False), float) for n in names]
    )


def _split_of_each_row(targets: np.ndarray, names: list[str]) -> np.ndarray:
    """Split de cada linha, conferindo que o raman_data concatena os
    arquivos do cache na ordem treino, teste, validação."""
    parts = [_read_split_targets(s, names) for s in SPLITS_IN_ROW_ORDER]
    stacked = np.vstack(parts)
    if not np.array_equal(np.nan_to_num(stacked, nan=-1.0), np.nan_to_num(targets, nan=-1.0)):
        raise RuntimeError("ordem das linhas do raman_data não é treino, teste, validação")
    return np.concatenate([np.full(len(p), s) for p, s in zip(parts, SPLITS_IN_ROW_ORDER)])


def _first_row_of_each_group(groups: np.ndarray) -> np.ndarray:
    _, first = np.unique(groups, return_index=True)
    return np.sort(first)


def _longest_run(flags: np.ndarray) -> int:
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def _max_run_over_splits(missing: np.ndarray, split: np.ndarray) -> int:
    return max(_longest_run(missing[split == s]) for s in SPLITS_IN_ROW_ORDER)


def _mann_whitney_rows(label: str, sample_targets: np.ndarray, names: list[str]) -> list[dict]:
    missing = np.isnan(sample_targets[:, 0])
    rows = []
    for j, name in enumerate(names[1:], start=1):
        without = sample_targets[missing, j]
        with_ = sample_targets[~missing, j]
        without, with_ = without[~np.isnan(without)], with_[~np.isnan(with_)]
        test = mannwhitneyu(without, with_, alternative="two-sided")
        p_bonf = min(1.0, N_OTHER_TARGETS * test.pvalue)
        rows.append(
            {
                "agrupamento": label,
                "alvo": name,
                "n_sem_glicose": len(without),
                "n_com_glicose": len(with_),
                "media_sem_glicose": f"{without.mean():.4f}",
                "media_com_glicose": f"{with_.mean():.4f}",
                "U": f"{test.statistic:.1f}",
                "p": f"{test.pvalue:.3g}",
                "p_bonferroni": f"{p_bonf:.3g}",
                "significativo": p_bonf < ALPHA,
            }
        )
    return rows


def _chi_square_by_split(missing: np.ndarray, split: np.ndarray):
    table = np.array(
        [[np.sum(missing & (split == s)), np.sum(~missing & (split == s))] for s in SPLITS_REPORTED]
    )
    return table, chi2_contingency(table)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n-permutations",
        type=int,
        default=10000,
        help="permutações no teste de blocos (padrão: 10000)",
    )
    args = parser.parse_args()

    dataset = raman_data.raman_data("bioprocess_substrates", cache_dir=str(CACHE_DIR))
    names = list(dataset.target_names)
    targets = np.asarray(dataset.targets, dtype=float)
    split = _split_of_each_row(targets, names)

    neighbor = _first_row_of_each_group(_adjacent_replicate_groups(targets))
    samples, sample_split = targets[neighbor], split[neighbor]
    missing = np.isnan(samples[:, 0])

    # 1. Concentração por split, por amostra e (só para comparação) por espectro
    table, chi = _chi_square_by_split(missing, sample_split)
    _, chi_spectra = _chi_square_by_split(np.isnan(targets[:, 0]), split)

    # 2. Blocos: sequência mais longa, com permutação dentro de cada split
    observed_run = _max_run_over_splits(missing, sample_split)
    rng = np.random.default_rng(PERMUTATION_SEED)
    permuted_runs = np.empty(args.n_permutations, dtype=int)
    for i in range(args.n_permutations):
        shuffled = missing.copy()
        for s in SPLITS_IN_ROW_ORDER:
            in_split = sample_split == s
            shuffled[in_split] = rng.permutation(missing[in_split])
        permuted_runs[i] = _max_run_over_splits(shuffled, sample_split)
    p_run = float(np.mean(permuted_runs >= observed_run))

    # 3. Condição experimental
    co_missing = [
        (
            name,
            100 * np.isnan(samples[missing, j]).mean(),
            100 * np.isnan(samples[:, j]).mean(),
        )
        for j, name in enumerate(names[1:], start=1)
    ]
    composition = _composition_groups(targets)
    composition_first = _first_row_of_each_group(composition)
    straddling = sum(len(set(split[composition == k])) > 1 for k in np.unique(composition))
    mw_rows = (
        _mann_whitney_rows("amostra_vizinha", samples, names)
        + _mann_whitney_rows("espectro", targets, names)
        + _mann_whitney_rows("composicao_adr009", targets[composition_first], names)
    )

    lines = [
        "# Distribuição dos espectros sem glicose do bioprocess (ADR 007)",
        "",
        "Gerado por `scripts/audit_bioprocess_missing_glucose.py`.",
        "",
        f"Espectros: {len(targets)}, sem glicose: {int(np.isnan(targets[:, 0]).sum())}. "
        f"Amostras (linhas vizinhas com os 8 alvos idênticos): {len(samples)}, "
        f"sem glicose: {int(missing.sum())}.",
        "",
        "## 1. Concentração por split (por amostra)",
        "",
        "| split | sem glicose / amostras | % |",
        "|---|---|---|",
    ]
    for s, (k_missing, k_present) in zip(SPLITS_REPORTED, table):
        total = k_missing + k_present
        lines.append(f"| {s} | {k_missing}/{total} | {100 * k_missing / total:.2f}% |")
    lines += [
        "",
        f"Qui-quadrado: χ² = {chi.statistic:.2f}, p = {chi.pvalue:.2f} (gl = {chi.dof}). "
        f"Contando espectros: χ² = {chi_spectra.statistic:.2f}, p = {chi_spectra.pvalue:.2f}.",
        "",
        "## 2. Blocos",
        "",
        f"Sequência mais longa de amostras consecutivas sem glicose: {observed_run}. "
        f"Permutação dentro de cada split ({args.n_permutations} rodadas, semente "
        f"{PERMUTATION_SEED}): mediana {np.median(permuted_runs):.0f}, "
        f"P(sequência ≥ {observed_run}) = {p_run:.2f}.",
        "",
        "## 3. Condição experimental",
        "",
        "Ausência simultânea de cada outro alvo nas amostras sem glicose, contra a "
        "taxa basal em todas as amostras:",
        "",
        "| alvo | sem glicose | basal |",
        "|---|---|---|",
    ]
    lines += [f"| {n} | {a:.1f}% | {b:.1f}% |" for n, a, b in co_missing]
    lines += [
        "",
        f"Mann-Whitney bicaudal, Bonferroni × {N_OTHER_TARGETS}, α = {ALPHA}.",
    ]
    for label in ("amostra_vizinha", "espectro", "composicao_adr009"):
        lines += [
            "",
            f"### {label}",
            "",
            "| alvo | média sem glicose | média com glicose | p | p Bonferroni | significativo |",
            "|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {r['alvo']} | {r['media_sem_glicose']} | {r['media_com_glicose']} "
            f"| {r['p']} | {r['p_bonferroni']} | {'sim' if r['significativo'] else 'não'} |"
            for r in mw_rows
            if r["agrupamento"] == label
        ]
    lines += [
        "",
        f"`composicao_adr009` tem {len(composition_first)} composições, das quais "
        f"{straddling} aparecem em mais de um split da fonte; por isso a checagem 1 "
        "não se aplica a esse agrupamento.",
    ]

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / "bioprocess_missing_glucose_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(mw_rows)
    md_path = out_dir / "bioprocess_missing_glucose_audit.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nSalvo em {csv_path.relative_to(ROOT)} e {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
