"""O reajuste no treino inteiro piora o teste? Três versões do modelo entregue.

Para os quatro braços de rede da decomposição (B1, B2, B3 e B4-limpo), nas
`seed_split` 0–29 do Tecator, do Gasoline e do Mango, com a receita do
artigo:
  (a) parada:  o modelo do treino de parada (80% do treino, melhor época na
               fold de parada), o entregue antes de 17/11;
  (b) reajuste, última época: todas as linhas do treino, `best_epoch`
               épocas, fica a última (o entregue desde 17/11);
  (c) reajuste, menor erro de treino: o mesmo treino de (b), mas fica a
               época de menor RMSE nas próprias linhas do treino, medido sem
               dropout. Proposta, não adotada.
Mede o R² de teste das três. Confere que (b) daqui é igual ao braço.

Piloto: decisão de método, nada daqui entra no texto.

Uso: python -B conferir_reajuste.py [processos]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"

import copy
import csv
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

SAIDA = RAIZ / "results" / "conferencia_reajuste.csv"
CONJUNTOS = ("tecator", "gasoline", "mango")
BRACOS = ("mlp_full", "mlp_weighted", "gate_uniform", "gate_prior")


def r2(y, p):
    import numpy as np
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))


def uma(tarefa):
    sys.path.insert(0, str(RAIZ / "src"))
    import numpy as np
    import torch
    import torch.nn.functional as F
    from tcc.arms import gate
    from tcc.arms.base import Budget
    from tcc.data import load
    from tcc.preprocessing import SNVPreprocessor
    from tcc.protocol import _make_cv_folds, _split_train_test

    torch.set_num_threads(1)
    conjunto, s = tarefa
    ds = load(conjunto)
    sp, cvs = np.random.SeedSequence(s).spawn(2)
    tr, te = _split_train_test(ds.X.shape[0], 0.25, np.random.default_rng(sp), groups=ds.groups)
    pre = SNVPreprocessor().fit(ds.X[tr])
    Xtr, Xte, ytr, yte = pre.transform(ds.X[tr]), pre.transform(ds.X[te]), ds.y[tr], ds.y[te]
    folds = _make_cv_folds(len(tr), 5, np.random.default_rng(cvs),
                           groups=None if ds.groups is None else ds.groups[tr])
    fit_idx, stop_idx = folds[0]

    linhas = []
    for nome in BRACOS:
        arm = getattr(gate, nome)()
        entregue = arm.fit(Xtr, ytr, folds, np.random.default_rng(0), Budget())
        h = entregue.hyperparams
        seed = int(np.random.default_rng(0).integers(2**31 - 1))

        def tensor(a):
            return torch.as_tensor(a, dtype=torch.float32)

        # (a) o treino de parada, refeito como no braço
        m, sd = gate._zscore(Xtr[fit_idx])
        ym, ys = ytr[fit_idx].mean(), ytr[fit_idx].std()
        net, _, _ = arm.initial_net((Xtr[fit_idx] - m) / sd, ytr[fit_idx], seed)
        arm._train(net, tensor((Xtr[fit_idx] - m) / sd), tensor((ytr[fit_idx] - ym) / ys),
                   max_epochs=arm.recipe.max_epochs,
                   stop=(tensor((Xtr[stop_idx] - m) / sd), tensor((ytr[stop_idx] - ym) / ys)))
        with torch.no_grad():
            pa = net(tensor((Xte - m) / sd)).numpy().ravel() * ys + ym

        # (b) e (c): o reajuste, acompanhando o erro de treino a cada época
        m, sd = gate._zscore(Xtr)
        ym, ys = ytr.mean(), ytr.std()
        Xa, ya = tensor((Xtr - m) / sd), tensor((ytr - ym) / ys)
        net, _, _ = arm.initial_net((Xtr - m) / sd, ytr, seed)
        cfg = arm.config
        rest = [p for n, p in net.named_parameters() if n != "gates"]
        groups = [{"params": rest, "weight_decay": gate.WEIGHT_DECAY}]
        if cfg.gated and cfg.trainable:
            groups.append({"params": [net.gates],
                           "weight_decay": gate.WEIGHT_DECAY if cfg.gate_weight_decay else 0.0})
        else:
            net.gates.requires_grad_(False)
        opt = torch.optim.Adam(groups, lr=arm.recipe.lr)
        use_kl = cfg.gated and cfg.kl_ref != "none"
        melhor, estado, epoca_c = float("inf"), None, 0
        for ep in range(h["best_epoch"]):
            net.train()
            loss = F.mse_loss(net(Xa).squeeze(1), ya)
            if use_kl:
                loss = loss + gate.KL_WEIGHT * net.kl()
            opt.zero_grad()
            loss.backward()
            opt.step()
            net.eval()
            with torch.no_grad():
                e = torch.sqrt(F.mse_loss(net(Xa).squeeze(1), ya)).item()
            if e < melhor:
                melhor, estado, epoca_c = e, copy.deepcopy(net.state_dict()), ep + 1
        with torch.no_grad():
            pb = net(tensor((Xte - m) / sd)).numpy().ravel() * ys + ym
            net.load_state_dict(estado)
            pc = net(tensor((Xte - m) / sd)).numpy().ravel() * ys + ym

        igual_b = bool(np.allclose(pb, entregue.predict(Xte), rtol=1e-5, atol=1e-5))
        linhas.append({"conjunto": conjunto, "seed_split": s, "braco": nome,
                       "best_epoch": h["best_epoch"], "epoca_c": epoca_c,
                       "r2_a_parada": f"{r2(yte, pa):.6f}",
                       "r2_b_ultima": f"{r2(yte, pb):.6f}",
                       "r2_c_menor_treino": f"{r2(yte, pc):.6f}",
                       "b_igual_ao_braco": igual_b})
    return linhas


def main():
    import statistics as st
    processos = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    tarefas = [(c, s) for c in CONJUNTOS for s in range(30)]
    with ProcessPoolExecutor(processos, mp_context=mp.get_context("spawn")) as ex:
        linhas = [l for ls in ex.map(uma, tarefas) for l in ls]
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    print("(b) igual ao braço em", sum(l["b_igual_ao_braco"] for l in linhas), "de", len(linhas))
    print(f"\n{'conjunto':9} {'braço':13} {'(b)−(a) med':>11} {'b>a':>6} {'(c)−(a) med':>11} {'c>a':>6} "
          f"{'(c)−(b) med':>11} {'c>b':>6}")
    for c in CONJUNTOS:
        for b in BRACOS:
            ls = [l for l in linhas if l["conjunto"] == c and l["braco"] == b]
            a = [float(l["r2_a_parada"]) for l in ls]
            bb = [float(l["r2_b_ultima"]) for l in ls]
            cc = [float(l["r2_c_menor_treino"]) for l in ls]
            d = lambda x, y: [i - j for i, j in zip(x, y)]  # noqa: E731
            n = lambda x: sum(v > 0 for v in x)  # noqa: E731
            print(f"{c:9} {b:13} {st.median(d(bb, a)):>+11.4f} {n(d(bb, a)):>3}/30 "
                  f"{st.median(d(cc, a)):>+11.4f} {n(d(cc, a)):>3}/30 "
                  f"{st.median(d(cc, bb)):>+11.4f} {n(d(cc, bb)):>3}/30")
    print("gravado em", SAIDA)


if __name__ == "__main__":
    main()
