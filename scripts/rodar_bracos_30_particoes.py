"""Braços clássicos nas `seed_split` 0–29 de um conjunto, com partições em paralelo.

Generaliza `rodar_bracos_tecator_30.py` (Tecator, 10/11/2026) para os outros
conjuntos. Mesmo desenho, fixado antes de rodar: `evaluate()` com SNV e
partição agrupada, `seed_split` 0 a 29, `seed_algo` 0, configurações padrão
de cada braço, comparação pareada com o PLS completo na mesma partição.

Paralelismo: cada partição roda inteira (os seis braços) num processo
próprio, com as mesmas sementes; o processo principal só grava as linhas.
Nenhum número depende de quantos processos rodam ao mesmo tempo.

Threads: uma por processo (OpenBLAS, OpenMP e MKL), fixada antes de
carregar o numpy, como a orientação pediu em 12/11/2026: o paralelismo fica
só entre partições, e o `wall_time`, que é resultado declarado, não é
medido com a CPU superassinada. Sem isso, cada processo abria 16 threads
por biblioteca. O R do iPLS usa o BLAS de referência, que já tem uma só.

Uso:
  python -B rodar_bracos_30_particoes.py rodar <conjunto> [processos] [primeira] [última]
      padrão: 1 processo, sementes 0 a 29. Acrescenta as linhas em
      results/bracos_<conjunto>_30_particoes.csv; partições e braços que já
      estão no CSV são pulados, então dá para interromper e retomar.
  python -B rodar_bracos_30_particoes.py resumo <conjunto>
"""

import os

# Antes de qualquer import que carregue o numpy; os processos filhos herdam.
THREADS = "1"
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = THREADS

import csv
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np

CAMPOS = ["seed_split", "braco", "r2", "rmsep", "rmse_cv", "n_bandas",
          "n_componentes", "n_ajustes", "tempo_s"]
ORDEM = ["pls", "ipls", "vip", "gapls", "cars", "cars_fiel"]


def saida(conjunto):
    return RAIZ / "results" / f"bracos_{conjunto}_30_particoes.csv"


def fabricas():
    from tcc.arms.cars import CARSArm
    from tcc.arms.gapls import GAPLSArm
    from tcc.arms.ipls import IPLSArm
    from tcc.arms.pls import PLSArm
    from tcc.arms.vip import VIPArm
    return {"pls": PLSArm, "ipls": IPLSArm, "vip": VIPArm, "gapls": GAPLSArm,
            "cars": CARSArm, "cars_fiel": lambda: CARSArm(mode="fiel")}


def ler(conjunto):
    p = saida(conjunto)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def uma_particao(conjunto, s, pular):
    """Roda, num processo próprio, os braços que faltam da partição `s`."""
    sys.path.insert(0, str(RAIZ / "src"))
    from tcc.data import load
    from tcc.protocol import evaluate

    ds = load(conjunto)
    linhas = []
    for nome, fabrica in fabricas().items():
        if nome in pular:
            continue
        r = evaluate(fabrica(), ds, seed_split=s, seed_algo=0)
        linhas.append({
            "seed_split": s, "braco": nome, "r2": f"{r.r2:.6f}",
            "rmsep": f"{r.rmsep:.6f}", "rmse_cv": f"{r.rmse_cv:.6f}",
            # `Result.selection` fica None até o Estágio 4; os braços de
            # seleção informam as bandas em `hyperparams["n_bands"]`.
            "n_bandas": r.hyperparams.get("n_bands", ds.X.shape[1]),
            "n_componentes": r.hyperparams.get("n_components", ""),
            "n_ajustes": r.n_fits, "tempo_s": f"{r.wall_time:.2f}",
        })
    return s, linhas


def rodar(conjunto, processos, primeira, ultima):
    feitos = {}
    for r in ler(conjunto):
        feitos.setdefault(int(r["seed_split"]), set()).add(r["braco"])
    tarefas = [s for s in range(primeira, ultima + 1)
               if feitos.get(s, set()) != set(ORDEM)]
    p = saida(conjunto)
    novo = not p.exists()
    print(f"{conjunto}: seed_split {primeira} a {ultima}, {len(tarefas)} partições "
          f"a rodar, {processos} processo(s), {THREADS} thread(s) por processo",
          flush=True)
    t0 = time.time()
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        if novo:
            w.writeheader()
            f.flush()
        with ProcessPoolExecutor(max_workers=processos,
                                 mp_context=mp.get_context("spawn")) as ex:
            futuros = [ex.submit(uma_particao, conjunto, s, feitos.get(s, set()))
                       for s in tarefas]
            for fut in as_completed(futuros):
                s, linhas = fut.result()
                # Grava na ordem fixa dos braços, para o CSV não depender
                # de qual processo terminou primeiro dentro da partição.
                for linha in sorted(linhas, key=lambda x: ORDEM.index(x["braco"])):
                    w.writerow(linha)
                f.flush()
                resumo_linha = "  ".join(f"{x['braco']} {float(x['r2']):.4f}" for x in linhas)
                print(f"[{(time.time() - t0) / 60:6.1f} min] seed {s:>2}: {resumo_linha}",
                      flush=True)


def resumo(conjunto):
    from scipy.stats import wilcoxon

    tab = {}
    for r in ler(conjunto):
        tab.setdefault(r["braco"], {})[int(r["seed_split"])] = r
    sementes = sorted(set.intersection(*(set(v) for v in tab.values())))
    print(f"{conjunto}: sementes completas em todos os braços: {len(sementes)}\n")
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
    if len(sys.argv) >= 3 and sys.argv[1] == "rodar":
        a = sys.argv[3:]
        rodar(sys.argv[2], int(a[0]) if a else 1,
              int(a[1]) if len(a) > 1 else 0, int(a[2]) if len(a) > 2 else 29)
    elif len(sys.argv) >= 3 and sys.argv[1] == "resumo":
        resumo(sys.argv[2])
    else:
        sys.exit(__doc__)
