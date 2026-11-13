"""As sete figuras do Estágio 8 com dados do piloto do Tecator, para olhar.

Lê a grade de `conferir_executor.py` (`results/grade_conferencia/tecator`,
`seed_split` 0–29, `seed_algo` 0) e roda um eixo `seed_algo` pequeno
(`seed_split` 0, `seed_algo` 0–4) nos braços estocásticos. Grava os PNG em
`results/figuras_piloto/`, fora do git.

**Piloto:** nada daqui entra no texto. O δ do TOST e a meia largura das
janelas são ilustrativos (0,01 em R² e 10 nm); os do protocolo não foram
decididos.
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import sys
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np

from tcc import figures as F
from tcc.data import load
from tcc.decomposition import ARMS, decompose, paired_differences, tost
from tcc.grid import ArmSpec, GridSpec, load_results, run_grid
from tcc.metrics import cost_summary, expected_jaccard, reproducibility
from tcc.selection import paired_k, to_selection
from tcc.windows import windows

GRADE = RAIZ / "results" / "grade_conferencia"
SAIDA = RAIZ / "results" / "figuras_piloto"
DELTA = 0.01
SELECAO = ["ipls", "vip_threshold", "ga_pls", "cars", "mlp_weighted", "gate_uniform", "gate_prior"]
REDE = ["mlp_weighted", "gate_uniform", "gate_prior"]
# O B2 (mlp_weighted) também é estocástico: a porta é fixa, mas a rede nasce
# de pesos sorteados. Só o iPLS e o VIP são determinísticos aqui.
ESTOCASTICOS = {"ga_pls": "tcc.arms.gapls:GAPLSArm", "cars": "tcc.arms.cars:CARSArm",
                "mlp_weighted": "tcc.arms.gate:mlp_weighted",
                "gate_uniform": "tcc.arms.gate:gate_uniform", "gate_prior": "tcc.arms.gate:gate_prior"}


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    res = [r for r in load_results(GRADE / "tecator") if r.seed_algo == 0]
    ds = load("tecator")
    k = paired_k(res)

    dec = decompose(res)
    # média, não mediana: só a média é aditiva (A1 + soma das médias = média do B4)
    med = {t: float(np.mean(list(dec[t].values()))) for t in ("nao_lin", "ponderacao", "aprendizado", "prior")}
    a1 = float(np.mean([r.r2 for r in res if r.arm_name == ARMS["A1"]]))
    F.waterfall(a1, med, title="Decomposição de B4 − A1 (R², média; Tecator, piloto)") \
        .savefig(SAIDA / "1_cascata.png", dpi=150, bbox_inches="tight")

    nomes = {"nao_lin": "não-linearidade", "ponderacao": "ponderação",
             "aprendizado": "aprendizado", "prior": "prior (complementar)"}
    F.equivalence_forest({nomes[t]: tost(list(dec[t].values()), DELTA) for t in nomes}, DELTA,
                         title="IC 90% × margem ±δ (δ ilustrativo; Tecator, piloto)") \
        .savefig(SAIDA / "2_equivalencia.png", dpi=150, bbox_inches="tight")

    rep = reproducibility(res, k=k, axis="seed_split")
    pts = {a: (float(np.median(list(paired_differences(res, a, "pls_full").values()))),
               rep[("tecator", a)]) for a in SELECAO}
    F.performance_vs_reproducibility(pts, neural=REDE,
                                     title="Desempenho × reprodutibilidade (Tecator, piloto)") \
        .savefig(SAIDA / "3_desempenho_reprodutibilidade.png", dpi=150, bbox_inches="tight")

    spec = GridSpec(datasets=["tecator"], seed_splits=[0], algo_axis_split=0,
                    algo_axis_seeds=[0, 1, 2, 3, 4],
                    arms=[ArmSpec(n, f) for n, f in ESTOCASTICOS.items()])
    run_grid(spec, GRADE / "tecator_algo", processes=4, log=lambda *_: None)
    eixo_algo = load_results(GRADE / "tecator_algo")
    rep_a = reproducibility(eixo_algo, k=k, axis="seed_algo")
    p = ds.X.shape[1]
    acaso = {}
    for a in SELECAO:
        sels = [to_selection(r, k) for r in res if r.arm_name == a]
        acaso[a] = float(np.mean([expected_jaccard(len(x), len(y), p) for x, y in combinations(sels, 2)]))
    F.jaccard_two_axes({a: rep[("tecator", a)] for a in SELECAO},
                       {a: rep_a[("tecator", a)] for a in ESTOCASTICOS}, acaso,
                       deterministic=[a for a in SELECAO if a not in ESTOCASTICOS],
                       title=f"Jaccard nos dois eixos (k = {k}; traço: acaso; Tecator, piloto)") \
        .savefig(SAIDA / "4_jaccard_dois_eixos.png", dpi=150, bbox_inches="tight")

    sel0 = {a: to_selection(next(r for r in res if r.arm_name == a and r.seed_split == 0), k)
            for a in SELECAO}
    F.bands_over_spectrum(ds.axis, ds.X.mean(axis=0), sel0, windows("tecator", 10),
                          title="Bandas da seed_split 0 e janelas da gordura (±10 nm ilustrativo)") \
        .savefig(SAIDA / "5_bandas_espectro.png", dpi=150, bbox_inches="tight")

    c = cost_summary(res)
    F.cost({a: c[("tecator", a)]["wall_time"] for a in ["pls_full", "ipls", "vip_threshold", "ga_pls",
                                                       "cars", "mlp_full", "gate_prior"]},
           title="Custo por braço (Tecator, piloto)") \
        .savefig(SAIDA / "6_custo.png", dpi=150, bbox_inches="tight")

    F.decomposition_by_regime({"tecator": med}, {"tecator": len(ds.X)},
                              title="Decomposição por regime (R², média; só o Tecator no piloto)") \
        .savefig(SAIDA / "7_por_regime.png", dpi=150, bbox_inches="tight")
    print("figuras em", SAIDA, "| k =", k)


if __name__ == "__main__":
    main()
