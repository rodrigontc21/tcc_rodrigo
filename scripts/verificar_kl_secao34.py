"""Confere a busca em grade do peso do KL descrita na Secao 3.4 do artigo.

manuscript_R2.tex:267 (e o PDF publicado) afirma:

  "The weight lambda=0.001 was selected via a coarse grid search over
   {1e-4, 1e-3, 1e-2, 1e-1} on a held-out validation fold of the Tecator
   dataset. At lambda=0.001, the trained gates exhibit moderate correlation
   with the prior (r ~ 0.35-0.51) [...]. Larger values (lambda >= 0.01)
   caused the learned gates to collapse toward the prior (r > 0.85) with
   negligible data-driven adjustment; smaller values (lambda <= 1e-4)
   produced gates indistinguishable from random initialization in terms of
   chemical interpretability."

Nao ha script dessa busca no repositorio. Refeita aqui com a grade do
artigo, e o protocolo que o texto descreve: Tecator, coluna 0 (a publicada),
treino em 4 folds e validacao na quinta, com as folds do cross_validate.py
(KFold(5, shuffle=True, random_state=42) sobre os 172 do treino); a receita
de treino e a do train_light.py (lr 0.01, 200 epocas, paciencia 30 sobre a
fold de validacao, weight decay 1e-4). Cada uma das 5 folds faz o papel de
"held-out" uma vez, em 10 sementes: 50 treinos por lambda.

Medidas: correlacao das portas treinadas com o prior ANOVA, e - para a
afirmacao sobre lambda <= 1e-4 - a mesma correlacao num modelo de
inicializacao aleatoria (train_random.py: sem prior, KL contra a uniforme),
treinado na mesma fold.

Este script foi escrito DEPOIS da varredura de verificar_varredura_treino.py,
para conferir uma afirmacao especifica do texto; por isso fica separado e
nao altera o desenho daquela.

Nada do repositorio da orientacao e alterado.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.optim as optim  # noqa: E402
from sklearn.model_selection import KFold, train_test_split  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

PGSG = (
    Path.home()
    / "tcc/docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
)
sys.path.insert(0, str(PGSG / "src"))

from data.compute_priors import compute_anova_scores  # noqa: E402
from models.band_select_net_light import BandSelectNetLight  # noqa: E402

SEP = "=" * 74
GRADE = [1e-4, 1e-3, 1e-2, 1e-1]
SEMENTES = range(10)

X = pd.read_csv(PGSG / "data/raw/tecator/spectra.csv").values
Y = pd.read_csv(PGSG / "data/raw/tecator/targets.csv").values
Xtr, _, ytr, _ = train_test_split(X, Y, test_size=0.2, random_state=42)
Xtr = StandardScaler().fit_transform(Xtr)
ytr = StandardScaler().fit_transform(ytr)[:, 0]
prior = compute_anova_scores(Xtr, ytr)
folds = list(KFold(n_splits=5, shuffle=True, random_state=42).split(Xtr))


def treinar(pri, kl, semente, tr, va):
    torch.manual_seed(semente)
    m = BandSelectNetLight(100, 1, pri, 16, 0.5)
    Xa, ya = torch.FloatTensor(Xtr[tr]), torch.FloatTensor(ytr[tr])
    Xv, yv = torch.FloatTensor(Xtr[va]), torch.FloatTensor(ytr[va])
    crit = nn.MSELoss()
    opt = optim.Adam(m.parameters(), lr=0.01, weight_decay=1e-4)
    melhor, sem = float("inf"), 0
    for _ in range(200):
        m.train()
        pred, _ = m(Xa)
        perda = crit(pred.squeeze(), ya) + kl * m.get_kl_loss()
        opt.zero_grad()
        perda.backward()
        opt.step()
        m.eval()
        with torch.no_grad():
            p, _ = m(Xv)
            r = torch.sqrt(crit(p.squeeze(), yv))
        if r < melhor:
            melhor, sem = r, 0
        else:
            sem += 1
            if sem >= 30:
                break
    m.eval()
    with torch.no_grad():
        _, g = m(Xv)
    return float(np.corrcoef(g.numpy(), prior)[0, 1])


def resumo(v):
    v = np.asarray(v)
    return (f"mediana {np.median(v):.3f}  faixa [{v.min():.3f}; {v.max():.3f}]"
            f"  r > 0.85 em {int((v > 0.85).sum())}/{len(v)}")


print()
print(SEP)
print(" SECAO 3.4 - A BUSCA EM GRADE DO PESO DO KL (manuscript_R2.tex:267)")
print(SEP)
print()
print("  correlacao das portas treinadas com o prior ANOVA,")
print(f"  {len(folds)} folds x {len(SEMENTES)} sementes = "
      f"{len(folds) * len(SEMENTES)} treinos por linha")
print()
for kl in GRADE:
    v = [treinar(prior, kl, s, tr, va) for s in SEMENTES for tr, va in folds]
    print(f"  lambda {kl:<7g} {resumo(v)}")
print()
v = [treinar(None, 0.001, s, tr, va) for s in SEMENTES for tr, va in folds]
print(f"  inicializacao aleatoria (sem prior, KL 0.001, como train_random.py):")
print(f"  {'':<14} {resumo(v)}")
print()
print("  o artigo afirma: lambda 0.001 -> r ~ 0.35-0.51; lambda >= 0.01 ->")
print("  r > 0.85; lambda <= 1e-4 -> indistinguivel da inicializacao aleatoria.")
print()
