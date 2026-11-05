"""Divergencia com a reproducao da orientacao (01/10) nos bracos de rede.

1. os oito valores da Tabela 2, um a um, no protocolo declarado (10 sementes)
2. quanto a mediana de 10 replicas depende de quais sementes se usam
3. variacoes de protocolo da Plain CNN na gordura

Usa as mesmas funcoes do verificar_pipeline_tecator.py.

Uso: python verificar_divergencia_redes.py
"""

import copy
import sys

sys.dont_write_bytecode = True  # nao criar __pycache__ no repositorio do artigo

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.preprocessing import StandardScaler

import verificar_pipeline_tecator as v

SEP = "=" * 78


def titulo(t):
    print()
    print(SEP)
    print(f" {t}")
    print(SEP)
    print()


def faixa(x):
    x = np.asarray(x)
    return f"mediana {np.median(x):7.3f}  faixa [{x.min():.2f}; {x.max():.2f}]"


# ---------------------------------------------------------------- 1
titulo("1. OS OITO VALORES DA TABELA 2, UM A UM, NO PROTOCOLO DECLARADO")
print("  train_light.py: lr 0.01, 200 epocas, paciencia 30 no teste, KL 0.001.")
print("  10 sementes. 'reproduz' = igual ao publicado na precisao publicada.")


def preparar_conjunto(nome):
    X = pd.read_csv(v.PGSG / f"data/raw/{nome}/spectra.csv").values
    y = pd.read_csv(v.PGSG / f"data/raw/{nome}/targets.csv").values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sx, sy = StandardScaler(), StandardScaler()
    return (sx.fit_transform(Xtr), sx.transform(Xte),
            sy.fit_transform(ytr)[:, 0], sy.transform(yte)[:, 0])


eixo = np.linspace(850, 1050, 100)  # o eixo do analyze_gates.py
compat = excl = 0
for nome in ("tecator", "gasoline"):
    Xtr, Xte, ytr, yte = preparar_conjunto(nome)
    prior = v.compute_anova_scores(Xtr, ytr)
    p = Xtr.shape[1]
    medidas = {}
    for s in range(10):
        torch.manual_seed(s)
        m = v.BandSelectNetLight(n_bands=p, n_outputs=1, prior_scores=prior,
                                 hidden_dim=16, dropout=0.5)
        _, g = v.treinar(m, Xtr, ytr, Xte, yte, 200, 0.01, 0.001, 1e-4, 30)
        topo = int(np.argmax(g))
        corr = float(np.corrcoef(g, prior)[0, 1])
        if nome == "tecator":
            ch = 100 * g[(eixo >= 920) & (eixo <= 930)].sum()
            oh = 100 * g[(eixo >= 965) & (eixo <= 975)].sum()
            linha = {"banda do topo (nm)": (int(round(eixo[topo])), 931),
                     "peso da banda do topo": (round(float(g[topo]), 3), 0.215),
                     "correlacao com o prior": (round(corr, 3), 0.348),
                     "regiao C-H (%)": (round(float(ch), 1), 7.4),
                     "regiao O-H (%)": (round(float(oh), 1), 3.5)}
        else:
            linha = {"banda do topo (indice)": (topo, 154),
                     "peso da banda do topo": (round(float(g[topo]), 3), 0.130),
                     "correlacao com o prior": (round(corr, 3), 0.507)}
        for k, (med, pub) in linha.items():
            medidas.setdefault(k, (pub, []))[1].append(med)
    print()
    print(f"  {nome.upper()}")
    for k, (pub, vals) in medidas.items():
        n = sum(x == pub for x in vals)
        compat += n > 0
        excl += n == 0
        print(f"    {k:<26} publicado {pub:>7}   reproduz em {n:>2}/10   "
              f"medido {min(vals)} a {max(vals)}")
print()
print(f"  -> {compat} compativeis (reproduzem em ao menos uma semente), "
      f"{excl} excluidos (em nenhuma)")

# ---------------------------------------------------------------- 2
titulo("2. QUANTO A MEDIANA DE 10 REPLICAS DEPENDE DAS SEMENTES")
print("  Mesmo protocolo do verificar_pipeline_tecator.py, mais sementes.")
print("  Se as medianas por bloco de 10 variam pouco, uma diferenca maior que")
print("  essa variacao nao se explica so pela escolha das sementes.")

N = 50
for coluna, nome in ((0, "agua"), (1, "gordura")):
    Xtr, Xte, ytr, yte = v.preparar(coluna)
    P = v.priors(Xtr, ytr)
    print()
    print(f"  coluna {coluna} ({nome})")
    for rot, fab, kl, wd, pac in (("Plain CNN, teste unico", v.pesada, 1e-4, 0.0, 20),
                                  ("ANOVA, teste unico", v.leve, 1e-3, 1e-4, 30)):
        r2 = np.array([v.treinar(fab(P["anova"], s), Xtr, ytr, Xte, yte,
                                 200, 0.01, kl, wd, pac)[0][1] for s in range(N)])
        blocos = [np.median(r2[i:i + 10]) for i in range(0, N, 10)]
        print(f"    {rot:<24} {N} sementes: {faixa(r2)}")
        print(f"    {'':<24} medianas por bloco de 10: "
              f"{', '.join(f'{b:.3f}' for b in blocos)}")
        if rot.startswith("Plain"):
            print(f"    {'':<24} 0.235 publicado: percentil "
                  f"{100 * (r2 < 0.235).mean():.0f} das {N}")
    if coluna == 1:
        cv = []
        for s in range(30):
            f = [v.treinar(v.leve(P["anova"], s), Xtr[a], ytr[a], Xtr[b], ytr[b],
                           200, 0.01, 1e-3, 1e-4, 30)[0][1]
                 for a, b in KFold(5, shuffle=True, random_state=42).split(Xtr)]
            cv.append(np.mean(f))
        cv = np.array(cv)
        blocos = [np.median(cv[i:i + 10]) for i in range(0, 30, 10)]
        print(f"    {'PGSG 5-fold':<24} 30 sementes: {faixa(cv)}")
        print(f"    {'':<24} medianas por bloco de 10: "
              f"{', '.join(f'{b:.3f}' for b in blocos)}")
print()
print("  a orientacao obteve: ANOVA teste unico na agua 0.932, PGSG 5-fold na")
print("  gordura 0.859, Plain CNN na gordura 0.410 [-0.02; 0.80]")

# ---------------------------------------------------------------- 3
titulo("3. PLAIN CNN NA GORDURA - VARIACOES DE PROTOCOLO, 10 SEMENTES")
print("  train_proper.py: 200 epocas, paciencia 20 no teste, KL 1e-4, sem")
print("  weight decay, modelo da ultima epoca. Cada linha muda uma coisa.")
print()

Xtr, Xte, ytr, yte = v.preparar(1)
P = v.priors(Xtr, ytr)
variantes = [
    ("train_proper como esta", 200, 0.01, 1e-4, 0.0, 20),
    ("100 epocas (default do train_model)", 100, 0.01, 1e-4, 0.0, 20),
    ("sem parada antecipada", 200, 0.01, 1e-4, 0.0, 200),
    ("paciencia 30", 200, 0.01, 1e-4, 0.0, 30),
    ("weight decay 1e-4", 200, 0.01, 1e-4, 1e-4, 20),
    ("receita do modelo leve", 200, 0.01, 1e-3, 1e-4, 30),
    ("lr 0.001", 200, 0.001, 1e-4, 0.0, 20),
]
for rot, ep, lr, kl, wd, pac in variantes:
    r2 = [v.treinar(v.pesada(P["anova"], s), Xtr, ytr, Xte, yte,
                    ep, lr, kl, wd, pac)[0][1] for s in range(10)]
    print(f"  {rot:<40} {faixa(r2)}")

# prior da agua (o tecator_fat_anova.npy do artigo) com alvo gordura
Xa, _, ya, _ = v.preparar(0)
prior_agua = v.priors(Xa, ya)["anova"]
r2 = [v.treinar(v.pesada(prior_agua, s), Xtr, ytr, Xte, yte,
                200, 0.01, 1e-4, 0.0, 20)[0][1] for s in range(10)]
print(f"  {'prior da agua, alvo gordura':<40} {faixa(r2)}")


def cnn_melhor_ou_cru(ytr_, yte_, melhor_epoca, semente):
    # receita do train_proper, com opcao de voltar ao melhor estado no teste
    m = v.pesada(P["anova"], semente)
    Xa_t, ya_t = torch.FloatTensor(Xtr), torch.FloatTensor(ytr_)
    Xv_t, yv_t = torch.FloatTensor(Xte), torch.FloatTensor(yte_)
    opt = optim.Adam(m.parameters(), lr=0.01)
    crit = nn.MSELoss()
    melhor, sem, estado = float("inf"), 0, None
    for _ in range(200):
        m.train()
        pred, _ = m(Xa_t)
        perda = crit(pred.squeeze(), ya_t) + 1e-4 * m.get_kl_loss()
        opt.zero_grad()
        perda.backward()
        opt.step()
        m.eval()
        with torch.no_grad():
            r = torch.sqrt(crit(m(Xv_t)[0].squeeze(), yv_t))
        if r < melhor:
            melhor, sem, estado = r, 0, copy.deepcopy(m.state_dict())
        else:
            sem += 1
            if sem >= 20:
                break
    if melhor_epoca:
        m.load_state_dict(estado)
    m.eval()
    with torch.no_grad():
        return r2_score(yte_, m(Xv_t)[0].squeeze().numpy())


r2 = [cnn_melhor_ou_cru(ytr, yte, True, s) for s in range(10)]
print(f"  {'voltar ao melhor estado no teste':<40} {faixa(r2)}")

# y sem padronizar, como o preprocessing.py (sem "fixed") deixaria
X = pd.read_csv(v.PGSG / "data/raw/tecator/spectra.csv").values
Y = pd.read_csv(v.PGSG / "data/raw/tecator/targets.csv").values
_, _, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=42)
r2 = [cnn_melhor_ou_cru(Ytr[:, 1], Yte[:, 1], False, s) for s in range(10)]
print(f"  {'y sem padronizar (preprocessing.py)':<40} {faixa(r2)}")
print()
print("  a orientacao obteve mediana 0.410, faixa [-0.02; 0.80]")
print()
