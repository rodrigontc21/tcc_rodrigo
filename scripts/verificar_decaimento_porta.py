"""Deslocamento da porta no Gasoline: quanto é aprendizado e quanto é decaimento?

O relatório 3b dá, no protocolo do artigo, um deslocamento máximo de logit de
1,22 a 1,79 no Gasoline (`verificar_varredura_treino.py`). Em 04/11 o mesmo
número no Tecator se mostrou, na maior parte, encolhimento L2: o
`train_light.py` passa `model.parameters()` ao Adam com `weight_decay=1e-4`,
o que inclui os logits da porta. A medida da orientação (30/10) só cobria o
Tecator. Este script repete a decomposição no Gasoline.

Receita do `verificar_varredura_treino.py` (a do `train_light.py`): split
80/20 `random_state=42`, StandardScaler em X e y, prior ANOVA do pgsg sobre o
treino, lr 0,01, 200 épocas, paciência 30 sobre o teste, KL 1e-3, sementes 0
a 9. Muda só o decaimento:
  artigo      1e-4 em todos os parâmetros (o do train_light.py)
  nenhum      0 em tudo
  só no MLP   1e-4 no MLP, porta isenta

Medidas por semente (as mesmas da orientação):
  maior deslocamento   max |θ_final − θ_inicial|
  fração encolhida     fração de bandas com |θ| menor no fim
  correlação c/ −θ₀    corr(θ_final − θ_inicial, −θ_inicial)
  distância 1º-2º      diferença entre os dois maiores logits, no fim
  R² de teste

O Tecator (coluna 0, água) entra como controle: com a receita do artigo, ele
tem de reproduzir os números de 04/11.

Uso: python -B verificar_decaimento_porta.py
"""

import sys

sys.dont_write_bytecode = True  # nao criar __pycache__ no repositorio do artigo

from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

PGSG = (
    Path.home()
    / "tcc/docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
)
sys.path.insert(0, str(PGSG / "src"))

from data.compute_priors import compute_anova_scores  # noqa: E402
from models.band_select_net_light import BandSelectNetLight  # noqa: E402

SEMENTES = range(10)
MODOS = (("artigo", "1e-4 em tudo"), ("nenhum", "nenhum"), ("mlp", "só no MLP"))


def preparar(conjunto):
    X = pd.read_csv(PGSG / f"data/raw/{conjunto}/spectra.csv").values
    y = pd.read_csv(PGSG / f"data/raw/{conjunto}/targets.csv").values
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sx, sy = StandardScaler(), StandardScaler()
    Xtr, Xte = sx.fit_transform(Xtr), sx.transform(Xte)
    ytr, yte = sy.fit_transform(ytr), sy.transform(yte)
    return Xtr, Xte, ytr[:, 0], yte[:, 0]


def otimizador(m, modo):
    if modo == "artigo":
        return optim.Adam(m.parameters(), lr=0.01, weight_decay=1e-4)
    if modo == "nenhum":
        return optim.Adam(m.parameters(), lr=0.01, weight_decay=0.0)
    if modo == "mlp":
        resto = [p for n, p in m.named_parameters() if n != "gating.gates"]
        return optim.Adam(
            [{"params": resto, "weight_decay": 1e-4},
             {"params": [m.gating.gates], "weight_decay": 0.0}],
            lr=0.01,
        )
    raise ValueError(modo)


def treinar(prior, Xtr, ytr, Xte, yte, semente, modo):
    torch.manual_seed(semente)
    m = BandSelectNetLight(
        n_bands=Xtr.shape[1], n_outputs=1, prior_scores=prior,
        hidden_dim=16, dropout=0.5,
    )
    th0 = m.gating.gates.detach().clone().numpy()
    opt = otimizador(m, modo)
    Xtr_t, ytr_t = torch.FloatTensor(Xtr), torch.FloatTensor(ytr)
    Xte_t, yte_t = torch.FloatTensor(Xte), torch.FloatTensor(yte)
    crit = nn.MSELoss()
    melhor, sem = float("inf"), 0
    for _ in range(200):
        m.train()
        pred, _ = m(Xtr_t)
        perda = crit(pred.squeeze(), ytr_t) + 1e-3 * m.get_kl_loss()
        opt.zero_grad()
        perda.backward()
        opt.step()
        m.eval()
        with torch.no_grad():
            p, _ = m(Xte_t)
            r = torch.sqrt(crit(p.squeeze(), yte_t))
        if r < melhor:
            melhor, sem = r, 0
        else:
            sem += 1
            if sem >= 30:
                break
    m.eval()
    with torch.no_grad():
        p, _ = m(Xte_t)
    th1 = m.gating.gates.detach().numpy()
    d = th1 - th0
    topo = np.sort(th1)[::-1]
    return dict(
        desl=float(np.abs(d).max()),
        encolhida=float(np.mean(np.abs(th1) < np.abs(th0))),
        rho=float(np.corrcoef(d, -th0)[0, 1]),
        dist=float(topo[0] - topo[1]),
        r2=float(r2_score(yte, p.squeeze().numpy())),
    )


def resumo(linhas, k):
    a = np.array([x[k] for x in linhas])
    return f"{np.median(a):.3f} [{a.min():.3f}; {a.max():.3f}]"


for conjunto in ("tecator", "gasoline"):
    Xtr, Xte, ytr, yte = preparar(conjunto)
    prior = compute_anova_scores(Xtr, ytr)
    th0 = BandSelectNetLight(n_bands=Xtr.shape[1], prior_scores=prior).gating.gates
    o0 = np.sort(th0.detach().numpy())[::-1]
    print(f"\n=== {conjunto} ({Xtr.shape[1]} bandas), 10 sementes, "
          f"mediana [mín; máx]; distância 1º-2º no início: {o0[0] - o0[1]:.2f}")
    for modo, rotulo in MODOS:
        linhas = [treinar(prior, Xtr, ytr, Xte, yte, s, modo) for s in SEMENTES]
        print(f"  decaimento {rotulo}")
        for k, nome in (("desl", "maior deslocamento"),
                        ("encolhida", "fração encolhida"),
                        ("rho", "correlação c/ −θ₀"),
                        ("dist", "distância 1º-2º, fim"),
                        ("r2", "R² de teste")):
            print(f"    {nome:<22} {resumo(linhas, k)}", flush=True)
