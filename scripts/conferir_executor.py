"""Conferência do executor da grade (ADR 021) contra resultados já medidos.

Três etapas, todas no Tecator, `seed_split` 0–29, `seed_algo` 0, piloto:

  grade      roda pelo executor os seis braços clássicos e os braços de rede
             da varredura de `c`, e compara com o que já foi medido por
             outros scripts: `results/bracos_tecator_30_particoes.csv` (R²,
             RMSEP, bandas, componentes, ajustes) e `results/varredura_c.csv`
             (R², RMSEP, deslocamento da porta, melhor época).
  interromper roda os braços de rede numa pasta nova, mata o processo no meio,
             confere que nenhum arquivo ficou corrompido, retoma até o fim e
             compara os hashes com a etapa "grade".
  cadeia     lê a grade de volta e passa pelas métricas e pela decomposição,
             comparando com os números tirados por fora do executor em 13/11
             (`conferir_metricas_tecator.py` e `conferir_decomposicao_tecator.py`).

Uso: python -B conferir_executor.py grade|interromper|cadeia
"""

import csv
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np

from tcc.grid import ArmSpec, GridSpec, load_results, result_hash, run_grid

PASTA = RAIZ / "results" / "grade_conferencia"
GRADE = [1.0, 0.5, 0.3, 0.17, 0.10, 0.054, 0.026, 0.0]
C_TOST = 0.0306

CLASSICOS = {  # nome do braço -> (fábrica, kwargs, determinístico, nome no CSV antigo)
    "pls_full": ("tcc.arms.pls:PLSArm", (), True, "pls"),
    "ipls": ("tcc.arms.ipls:IPLSArm", (), True, "ipls"),
    "vip_threshold": ("tcc.arms.vip:VIPArm", (), True, "vip"),
    "ga_pls": ("tcc.arms.gapls:GAPLSArm", (), False, "gapls"),
    "cars": ("tcc.arms.cars:CARSArm", (), False, "cars"),
    "cars_fiel": ("tcc.arms.cars:CARSArm", (("mode", "fiel"),), False, "cars_fiel"),
}


def bracos_rede():
    arms = [ArmSpec("mlp_full", "tcc.arms.gate:mlp_full"),
            ArmSpec("mlp_weighted", "tcc.arms.gate:mlp_weighted"),
            ArmSpec("gate_uniform", "tcc.arms.gate:gate_uniform"),
            ArmSpec("gate_prior", "tcc.arms.gate:gate_prior")]
    for c in sorted(set(GRADE) | {C_TOST}, reverse=True):
        arms.append(ArmSpec(f"mlp_weighted(c={c:g})", "tcc.arms.gate:mlp_weighted_scaled",
                            kwargs=(("c", c),)))
        arms.append(ArmSpec(f"gate_prior(c={c:g})", "tcc.arms.gate:gate_prior_scaled",
                            kwargs=(("c", c),)))
    return arms


def spec(arms):
    return GridSpec(datasets=["tecator"], arms=arms, seed_splits=list(range(30)))


def grade():
    classicos = [ArmSpec(n, f, kwargs=kw, deterministic=det)
                 for n, (f, kw, det, _) in CLASSICOS.items()]
    t0 = time.time()
    print(run_grid(spec(classicos + bracos_rede()), PASTA / "tecator", processes=4))
    print(f"{(time.time() - t0) / 60:.1f} min")
    res = {(r.arm_name, r.seed_split): r for r in load_results(PASTA / "tecator")}

    # 1a. braços clássicos contra o CSV das 30 partições
    with open(RAIZ / "results/bracos_tecator_30_particoes.csv", encoding="utf-8") as f:
        antigo = {(r["braco"], int(r["seed_split"])): r for r in csv.DictReader(f)}
    difs, n = [], 0
    for nome, (_, _, _, csvnome) in CLASSICOS.items():
        for s in range(30):
            r, a = res[(nome, s)], antigo[(csvnome, s)]
            n += 1
            novo = {"r2": f"{r.r2:.6f}", "rmsep": f"{r.rmsep:.6f}",
                    "n_bandas": str(r.hyperparams.get("n_bands", 100)),
                    "n_componentes": str(r.hyperparams.get("n_components", "")),
                    "n_ajustes": str(r.n_fits)}
            for k, v in novo.items():
                if v != a[k]:
                    difs.append((nome, s, k, a[k], v))
    print(f"\nclássicos contra bracos_tecator_30_particoes.csv: {n} execuções, "
          f"{len(difs)} campos diferentes")
    for d in difs[:10]:
        print("   ", d)

    # 1b. braços de rede contra a varredura de c
    with open(RAIZ / "results/varredura_c.csv", encoding="utf-8") as f:
        varr = {(r["braco"], r["c"], int(r["seed_split"])): r
                for r in csv.DictReader(f) if r["conjunto"] == "tecator"}
    mapa = {"B3": ("gate_uniform", "")}
    for c in sorted(set(GRADE) | {C_TOST}):
        mapa[f"B2'|{c:g}"] = (f"mlp_weighted(c={c:g})", f"{c:g}")
        mapa[f"B5|{c:g}"] = (f"gate_prior(c={c:g})", f"{c:g}")
    difs, n = [], 0
    for (braco, c, s), a in varr.items():
        nome = mapa["B3"][0] if braco == "B3" else mapa[f"{braco}|{c}"][0]
        r = res[(nome, s)]
        n += 1
        novo = {"r2": f"{r.r2:.6f}", "rmsep": f"{r.rmsep:.6f}",
                "d": f"{r.hyperparams['gate_max_disp']:.6f}",
                "melhor_epoca": str(r.hyperparams["best_epoch"])}
        for k, v in novo.items():
            if v != a[k]:
                difs.append((braco, c, s, k, a[k], v))
    print(f"rede contra varredura_c.csv (Tecator): {n} execuções, {len(difs)} campos diferentes")
    for d in difs[:10]:
        print("   ", d)


def interromper():
    destino = PASTA / "interrompida"
    destino.mkdir(parents=True, exist_ok=True)
    if any(destino.glob("*.json")):
        sys.exit(f"{destino} já tem resultados; use uma pasta vazia")
    total = len(spec(bracos_rede()).tasks())
    proc = subprocess.Popen([sys.executable, "-B", __file__, "_rodar_rede", str(destino)],
                            start_new_session=True, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    while len(list(destino.glob("*.json"))) < total // 3:
        time.sleep(0.2)
        if proc.poll() is not None:
            sys.exit("a grade terminou antes de ser interrompida")
    os.killpg(proc.pid, signal.SIGKILL)  # mata o processo e os filhos, sem aviso
    proc.wait()
    time.sleep(1)
    feitos = list(destino.glob("*.json"))
    tmps = list(destino.glob("*.tmp"))
    quebrados = []
    for p in feitos:
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            quebrados.append(p.name)
    print(f"interrompida com {len(feitos)} de {total} execuções gravadas; "
          f"{len(quebrados)} arquivos corrompidos; {len(tmps)} temporários sobrando")
    print("retomando:", run_grid(spec(bracos_rede()), destino, processes=4, log=lambda *_: None))
    a = {(r.arm_name, r.seed_split): result_hash(r) for r in load_results(destino)}
    b = {(r.arm_name, r.seed_split): result_hash(r) for r in load_results(PASTA / "tecator")
         if (r.arm_name, r.seed_split) in a}
    iguais = sum(a[k] == b.get(k) for k in a)
    print(f"depois de retomar: {len(a)} execuções; idênticas à grade sem interrupção: {iguais}")


def cadeia():
    from tcc.decomposition import additive_identity_gap, decompose
    from tcc.metrics import reproducibility
    from tcc.selection import paired_k

    res = [r for r in load_results(PASTA / "tecator") if r.seed_split < 10]
    k = paired_k(res)
    rep = reproducibility(res, k=k, axis="seed_split")
    print(f"k pareado nas seed_split 0–9: {k} (em 13/11, por fora do executor: 14)")
    esperado = {"vip_threshold": 0.837, "ipls": 0.353, "ga_pls": 0.193, "cars": 0.227,
                "mlp_weighted": 0.835, "gate_uniform": 0.630, "gate_prior": 0.867}
    for nome, v in esperado.items():
        print(f"  Jaccard {nome:<15} executor {rep[('tecator', nome)]:.3f}   antes {v:.3f}")
    dec = decompose(res)
    print(f"decomposição: {len(dec['total'])} partições, identidade aditiva "
          f"{additive_identity_gap(dec):.1e}")
    for termo, antes in (("nao_lin", 0.0013), ("ponderacao", 0.0075),
                         ("aprendizado", 0.0001), ("prior", 0.0025)):
        print(f"  {termo:<12} mediana executor {np.median(list(dec[termo].values())):+.4f}"
              f"   antes {antes:+.4f}")


if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else ""
    if etapa == "grade":
        grade()
    elif etapa == "interromper":
        interromper()
    elif etapa == "cadeia":
        cadeia()
    elif etapa == "_rodar_rede":
        run_grid(spec(bracos_rede()), Path(sys.argv[2]), processes=4, log=lambda *_: None)
    else:
        sys.exit(__doc__)
