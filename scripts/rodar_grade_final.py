"""Roda a grade final, ou o ensaio dela na partição piloto 0.

A configuração está em `src/tcc/final_grid.py`. O modo "final" se recusa a
rodar enquanto houver valor a decidir pela orientação.

O ensaio roda a grade inteira (6 braços clássicos, 23 de rede, eixo
`seed_algo`) no Tecator, no Gasoline e no Mango, na `seed_split` 0, e
confere:
1. nenhuma execução falhou, e todas as tarefas têm arquivo;
2. os clássicos são iguais aos CSVs das 30 partições, na partição 0;
3. as redes da varredura de `c` (B3, B2' e B5) são iguais a
   `results/varredura_c.csv`, inclusive no Mango, com a receita "ensaio",
   que tem os valores da do artigo e só muda o nome;
4. no Tecator, todas as redes que a grade de conferência tem são iguais a
   ela, pelo hash das predições;
5. nenhuma réplica idêntica onde não deveria haver;
6. a decomposição fecha (identidade aditiva) em cada conjunto, com os nomes
   dos braços daquele conjunto;
7. o `k` pareado e o Jaccard nos dois eixos saem sem erro.

Piloto: nada daqui entra no texto.

Uso:
  python -B rodar_grade_final.py ensaio [processos]
  python -B rodar_grade_final.py final [processos]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import csv
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from tcc import final_grid as G
from tcc.decomposition import additive_identity_gap, decompose
from tcc.grid import identical_replicas, load_results, result_hash, run_grid
from tcc.metrics import reproducibility
from tcc.selection import paired_k

PASTA = {"ensaio": RAIZ / "results" / "grade_ensaio", "final": RAIZ / "results" / "grade_final"}
CSV_NOME = {"pls": "pls_full", "ipls": "ipls", "vip": "vip_threshold", "gapls": "ga_pls",
            "cars": "cars", "cars_fiel": "cars_fiel"}
TOL = 5e-7  # os CSVs guardam seis casas


def rodar(modo, processos):
    specs = G.specs(modo)
    t0 = time.time()
    for spec in specs:
        print(spec.datasets[0], run_grid(spec, PASTA[modo], processes=processos), flush=True)
    print(f"{(time.time() - t0) / 60:.1f} min")
    return specs


def conferir(specs):
    pasta = PASTA["ensaio"]
    res = load_results(pasta)
    por = {(r.dataset_name, r.arm_name, r.seed_split, r.seed_algo): r for r in res}
    problemas = []

    # 1. tudo rodou
    erros = sorted(p.name for p in pasta.glob("*.erro.txt"))
    esperadas = {t.run_id for s in specs for t in s.tasks()}
    gravadas = {p.stem for p in pasta.glob("*.json")}
    print(f"1. {len(gravadas & esperadas)} de {len(esperadas)} execuções gravadas, "
          f"{len(erros)} com erro")
    problemas += [f"erro: {e}" for e in erros]
    problemas += [f"faltou: {i}" for i in sorted(esperadas - gravadas)]

    for spec in specs:
        ds = spec.datasets[0]
        receita = G.TRIAL["recipe"].get(ds, G.RECIPE[ds])

        # 2. clássicos contra os CSVs das 30 partições
        n = 0
        with open(RAIZ / f"results/bracos_{ds}_30_particoes.csv", encoding="utf-8") as f:
            for linha in csv.DictReader(f):
                if linha["seed_split"] != "0":
                    continue
                r = por[(ds, CSV_NOME[linha["braco"]], 0, 0)]
                n += 1
                for campo, valor in (("r2", r.r2), ("rmsep", r.rmsep)):
                    if abs(float(linha[campo]) - valor) > TOL:
                        problemas.append(f"{ds} {linha['braco']} {campo}: CSV {linha[campo]}, "
                                         f"grade {valor:.6f}")
                if r.n_fits != int(linha["n_ajustes"]):
                    problemas.append(f"{ds} {linha['braco']} n_ajustes difere")
        print(f"2. {ds}: {n} clássicos comparados com o CSV")

        # 3. redes contra a varredura de c
        n = 0
        with open(RAIZ / "results/varredura_c.csv", encoding="utf-8") as f:
            for linha in csv.DictReader(f):
                if linha["conjunto"] != ds or linha["seed_split"] != "0":
                    continue
                base = {"B3": "gate_uniform",
                        "B2'": f"mlp_weighted(c={float(linha['c'] or 0):g})",
                        "B5": f"gate_prior(c={float(linha['c'] or 0):g})"}[linha["braco"]]
                r = por[(ds, G.arm_name(base, receita), 0, 0)]
                n += 1
                if abs(float(linha["r2"]) - r.r2) > TOL:
                    problemas.append(f"{ds} {base} r2: varredura {linha['r2']}, grade {r.r2:.6f}")
        print(f"3. {ds}: {n} redes comparadas com a varredura de c")

        # 6. decomposição com os nomes do conjunto
        papeis = G.roles(ds, receita)
        dec = decompose([r for r in res if r.dataset_name == ds and r.seed_algo == 0],
                        arms=papeis)
        gap = additive_identity_gap(dec)
        print(f"6. {ds}: decomposição em {len(dec['total'])} partição, "
              f"excluídas {dec['excluidas']}, maior desvio da soma {gap:.1e}")
        if dec["excluidas"] or not dec["total"] or gap > 1e-12:
            problemas.append(f"{ds}: decomposição não fecha")

    # 4. Tecator contra a grade de conferência, pelo hash
    conf = {(r.arm_name, r.seed_split): r for r in load_results(RAIZ / "results/grade_conferencia/tecator")
            if r.seed_split == 0 and r.seed_algo == 0}
    n = 0
    for (arm, s), r in conf.items():
        if ("tecator", arm, 0, 0) in por:
            n += 1
            if result_hash(r) != result_hash(por[("tecator", arm, 0, 0)]):
                problemas.append(f"tecator {arm}: hash difere da grade de conferência")
    print(f"4. tecator: {n} braços iguais à grade de conferência, pelo hash")

    # 5. réplicas
    det = {a.name for s in specs for a in s.arms if a.deterministic}
    rep = identical_replicas(res, deterministic=det)
    print(f"5. réplicas idênticas: {len(rep)}")
    problemas += [f"réplica idêntica: {x}" for x in rep]

    # 7. seleção e reprodutibilidade
    for spec in specs:
        ds = spec.datasets[0]
        sub = [r for r in res if r.dataset_name == ds]
        k = paired_k([r for r in sub if r.seed_algo == 0])
        j_algo = reproducibility(sub, k=k, axis="seed_algo")
        fora = [a for a, v in j_algo.items() if not 0 <= v <= 1]
        print(f"7. {ds}: k = {k}, Jaccard no eixo seed_algo para {len(j_algo)} braços")
        problemas += [f"Jaccard fora de [0, 1]: {a}" for a in fora]

    print("\nPROBLEMAS:" if problemas else "\nnenhum problema")
    for p in problemas:
        print("  ", p)
    return not problemas


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in PASTA:
        sys.exit(__doc__)
    modo = sys.argv[1]
    processos = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    specs = rodar(modo, processos)
    if modo == "ensaio":
        sys.exit(0 if conferir(specs) else 1)


if __name__ == "__main__":
    main()
