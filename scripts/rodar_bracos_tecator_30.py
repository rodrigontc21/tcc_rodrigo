"""Braços clássicos no Tecator nas `seed_split` 0–29, com a regra de réplicas de 09/11.

Pedido da orientação em 09/11/2026 (ADR 009): regenerar "o que já rodou do
Estágio 2, nas mesmas seed_split 0–29". Até 10/11 os braços tinham sido
refeitos só na `seed_split` 0 (iPLS, VIP e GA-PLS) e nas 0 a 9 (CARS).

Desenho, fixado antes de rodar: `evaluate()` com SNV e partição agrupada,
`seed_split` 0 a 29, `seed_algo` 0, configurações padrão de cada braço. Todos
os braços usam a mesma partição em cada semente, então a comparação com o
PLS completo é pareada: ΔR² = R²(braço) − R²(PLS) por semente, com o
Wilcoxon pareado como descrição.

Uso:
  python -B rodar_bracos_tecator_30.py rodar [primeira] [última]
      roda as sementes pedidas (padrão 0 a 29) e acrescenta as linhas no CSV;
      sementes e braços que já estão no CSV são pulados.
  python -B rodar_bracos_tecator_30.py resumo
      lê o CSV e imprime a comparação com o PLS.
"""

import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np

SAIDA = RAIZ / "results" / "bracos_tecator_30_particoes.csv"
CAMPOS = ["seed_split", "braco", "r2", "rmsep", "rmse_cv", "n_bandas",
          "n_componentes", "n_ajustes", "tempo_s"]
ORDEM = ["pls", "ipls", "vip", "gapls", "cars", "cars_fiel"]


def fabricas():
    from tcc.arms.cars import CARSArm
    from tcc.arms.gapls import GAPLSArm
    from tcc.arms.ipls import IPLSArm
    from tcc.arms.pls import PLSArm
    from tcc.arms.vip import VIPArm
    return {"pls": PLSArm, "ipls": IPLSArm, "vip": VIPArm, "gapls": GAPLSArm,
            "cars": CARSArm, "cars_fiel": lambda: CARSArm(mode="fiel")}


def ler():
    if not SAIDA.exists():
        return []
    with open(SAIDA, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rodar(primeira, ultima):
    from tcc.data import load
    from tcc.protocol import evaluate

    ds = load("tecator")
    feitos = {(int(r["seed_split"]), r["braco"]) for r in ler()}
    novo = not SAIDA.exists()
    print(f"tecator: X {ds.X.shape}, {len(np.unique(ds.groups))} grupos, "
          f"seed_split {primeira} a {ultima}, seed_algo 0", flush=True)
    with open(SAIDA, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        if novo:
            w.writeheader()
        for s in range(primeira, ultima + 1):
            for nome, fabrica in fabricas().items():
                if (s, nome) in feitos:
                    continue
                r = evaluate(fabrica(), ds, seed_split=s, seed_algo=0)
                # `Result.selection` fica None até o Estágio 4; os braços
                # de seleção informam as bandas em `hyperparams["n_bands"]`.
                n_bandas = r.hyperparams.get("n_bands", ds.X.shape[1])
                w.writerow({
                    "seed_split": s, "braco": nome, "r2": f"{r.r2:.6f}",
                    "rmsep": f"{r.rmsep:.6f}", "rmse_cv": f"{r.rmse_cv:.6f}",
                    "n_bandas": n_bandas,
                    "n_componentes": r.hyperparams.get("n_components", ""),
                    "n_ajustes": r.n_fits, "tempo_s": f"{r.wall_time:.2f}",
                })
                f.flush()
                print(f"{s:>3} {nome:<9} R² {r.r2:.4f}  RMSEP {r.rmsep:.4f}  "
                      f"bandas {n_bandas:>3}  {r.wall_time:7.1f} s", flush=True)


def resumo():
    from scipy.stats import wilcoxon

    linhas = ler()
    tab = {}
    for r in linhas:
        tab.setdefault(r["braco"], {})[int(r["seed_split"])] = r
    sementes = sorted(set.intersection(*(set(v) for v in tab.values())))
    print(f"sementes completas em todos os braços: {len(sementes)} "
          f"({sementes[0]} a {sementes[-1]})\n")
    pls = np.array([float(tab["pls"][s]["r2"]) for s in sementes])
    print(f"{'braço':<9} {'R² med':>7} {'RMSEP med':>9} {'ΔR² med':>8} "
          f"{'faixa ΔR²':>19} {'≥ PLS':>6} {'Wilcoxon':>8} {'bandas':>6} "
          f"{'ajustes':>8} {'tempo med':>9}")
    for b in ORDEM:
        if b not in tab:
            continue
        g = lambda k: np.array([float(tab[b][s][k]) for s in sementes])
        r2 = g("r2")
        d = r2 - pls
        p = f"{wilcoxon(d).pvalue:.3f}" if np.any(d != 0) else "—"
        print(f"{b:<9} {np.median(r2):>7.4f} {np.median(g('rmsep')):>9.4f} "
              f"{np.median(d):>+8.4f} [{d.min():+.4f}; {d.max():+.4f}] "
              f"{int(np.sum(d >= 0)):>3}/{len(d):<2} {p:>8} "
              f"{np.median(g('n_bandas')):>6.0f} {np.median(g('n_ajustes')):>8.0f} "
              f"{np.median(g('tempo_s')):>8.1f}s")
    if "cars" in tab and "cars_fiel" in tab:
        d = (np.array([float(tab["cars"][s]["r2"]) for s in sementes])
             - np.array([float(tab["cars_fiel"][s]["r2"]) for s in sementes]))
        print(f"\nCARS protocolo − fiel: ΔR² mediano {np.median(d):+.4f}, "
              f"faixa [{d.min():+.4f}; {d.max():+.4f}]")


if __name__ == "__main__":
    if sys.argv[1] == "rodar":
        a = sys.argv[2:]
        rodar(int(a[0]) if a else 0, int(a[1]) if len(a) > 1 else 29)
    elif sys.argv[1] == "resumo":
        resumo()
    else:
        sys.exit(__doc__)
