"""Confere, uma a uma, as afirmacoes numericas da Secao 5.2 e da Fig. 1.

A Secao 5.2 e o argumento de interpretabilidade do artigo, e foi a que a
orientacao apontou, em 29/09, como a que "precisa ser reformulada, nao so
corrigida". Este script mede cada numero que ela publica.

Afirmacoes conferidas (revision_r1/manuscript_R2.tex):

  linha 473 (legenda da Fig. 1)
    "concentrates 7.4% of total gate weight in the C-H region"
    "highest individual gate weight (0.215) at 931 nm"
    "secondary O-H region receives 3.5% total weight"
    "The moderate correlation with the ANOVA prior (r=0.35) confirms
     genuine data-driven refinement rather than mere reproduction of
     initialization"
  linha 477
    "top ten selected bands span the region from 921 nm to 935 nm,
     collectively accounting for 7.4% of the total gate weight"
  linha 481
    "The correlation between learned gates and the ANOVA prior was 0.348"
  linha 483 (Gasoline)
    "highest gate weight (0.130) ... band 154"
    "top 20 selected bands forming a contiguous spectral window spanning
     bands 150-168"
    "The correlation with the ANOVA prior was 0.507"
  linha 485
    "Removing the top gate-selected bands caused R2 to drop from 0.862 to
     0.431 ... removing random bands caused a substantially smaller
     average drop to 0.794"
    "8 of the top-10 bands appeared consistently in the top-10 selections
     of all 5 folds"

Cada uma e medida em duas condicoes: gates SEM TREINAR (a inicializacao) e
gates DEPOIS DE TREINAR. Nada do repositorio da orientacao e alterado.
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
from sklearn.metrics import r2_score  # noqa: E402
from sklearn.model_selection import KFold, train_test_split  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

PGSG = (
    Path.home()
    / "tcc/docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
)
sys.path.insert(0, str(PGSG / "src"))

from data.compute_priors import compute_anova_scores  # noqa: E402
from models.band_select_net_light import BandSelectNetLight  # noqa: E402

SEP = "=" * 78


def titulo(t):
    print()
    print(SEP)
    print(f" {t}")
    print(SEP)
    print()


def preparar(conjunto, coluna=0):
    X = pd.read_csv(PGSG / f"data/raw/{conjunto}/spectra.csv").values
    y = pd.read_csv(PGSG / f"data/raw/{conjunto}/targets.csv").values
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    sx, sy = StandardScaler(), StandardScaler()
    Xtr, Xte = sx.fit_transform(Xtr), sx.transform(Xte)
    ytr, yte = sy.fit_transform(ytr), sy.transform(yte)
    return Xtr, Xte, ytr[:, coluna], yte[:, coluna]


def modelo(prior, p, semente=0):
    torch.manual_seed(semente)
    return BandSelectNetLight(n_bands=p, n_outputs=1, prior_scores=prior,
                              hidden_dim=16, dropout=0.5)


def treinar(m, Xtr, ytr, Xav, yav, epocas=200, lr=0.01, kl=0.001,
            wd=1e-4, paciencia=30):
    Xtr_t, ytr_t = torch.FloatTensor(Xtr), torch.FloatTensor(ytr)
    Xav_t, yav_t = torch.FloatTensor(Xav), torch.FloatTensor(yav)
    crit = nn.MSELoss()
    opt = optim.Adam(m.parameters(), lr=lr, weight_decay=wd)
    melhor, sem = float("inf"), 0
    for _ in range(epocas):
        m.train()
        pred, _ = m(Xtr_t)
        (crit(pred.squeeze(), ytr_t) + kl * m.get_kl_loss()).backward()
        opt.step()
        opt.zero_grad()
        m.eval()
        with torch.no_grad():
            p_av, _ = m(Xav_t)
            r = torch.sqrt(crit(p_av.squeeze(), yav_t))
        if r < melhor:
            melhor, sem = r, 0
        else:
            sem += 1
            if sem >= paciencia:
                break
    m.eval()
    with torch.no_grad():
        _, g = m(Xav_t)
    return m, g.numpy()


def gates_sem_treinar(m, X):
    m.eval()
    with torch.no_grad():
        _, g = m(torch.FloatTensor(X))
    return g.numpy()


def confere(rotulo, medido, publicado, casas):
    # compara na precisao publicada: arredonda o medido para as mesmas casas
    marca = "ok" if round(medido, casas) == round(publicado, casas) else "DIFERE"
    return f"  {rotulo:<44} medido {medido:>8.3f}   publicado {publicado:>7.3f}   {marca}"


# ---------------------------------------------------------------- TECATOR
titulo("TECATOR - FIG. 1 E SECAO 5.2, NAS DUAS CONDICOES")

Xtr, Xte, ytr, yte = preparar("tecator", 0)  # coluna 0: a que foi publicada
prior = compute_anova_scores(Xtr, ytr)
eixo = np.linspace(850, 1050, 100)  # o eixo que o analyze_gates.py usa

m0 = modelo(prior, 100)
g0 = gates_sem_treinar(m0, Xte)
m1 = modelo(prior, 100)
_, g1 = treinar(m1, Xtr, ytr, Xte, yte)

for etiqueta, g in (("SEM TREINAR (a inicializacao)", g0),
                    ("DEPOIS DE TREINAR", g1)):
    print(f"  {etiqueta}")
    topo = int(np.argmax(g))
    ch = g[(eixo >= 920) & (eixo <= 930)].sum() * 100
    oh = g[(eixo >= 965) & (eixo <= 975)].sum() * 100
    top10 = np.argsort(g)[-10:]
    print(confere("banda de maior peso (nm)", eixo[topo], 931.0, 0))
    print(confere("peso dessa banda", float(g[topo]), 0.215, 3))
    print(confere("correlacao com o prior ANOVA",
                  float(np.corrcoef(g, prior)[0, 1]), 0.348, 3))
    print(confere("peso na regiao C-H, 920-930 nm (%)", ch, 7.4, 1))
    print(confere("peso na regiao O-H, 965-975 nm (%)", oh, 3.5, 1))
    print(f"  {'faixa das 10 maiores (nm)':<44} medido "
          f"{eixo[top10].min():.0f}-{eixo[top10].max():.0f}"
          f"     publicado 921-935")
    print(f"  {'peso somado das 10 maiores (%)':<44} medido "
          f"{g[top10].sum() * 100:>8.3f}   publicado    7.4")
    print()

# o pico: prior, logit e porta nas bandas vizinhas de 931 nm, sem treinar
l0 = m0.gating.gates.detach().numpy()
print("  O PICO, SEM TREINAR: prior, logit e porta em volta de 931 nm")
for b in (39, 40, 41):
    print(f"    banda {b} ({eixo[b]:.0f} nm)   prior {prior[b]:.6f}   "
          f"logit {l0[b]:6.2f}   porta {g0[b]:.4f}")
bmin = int(np.argmin(prior))
print(f"    prior minimo: banda {bmin} ({eixo[bmin]:.0f} nm), logit {l0[bmin]:.2f}")
print(f"    maior peso: porta inicial {g0.max():.3f}; prior bruto normalizado "
      f"para somar 1 {(prior / prior.sum()).max():.3f}")
print()

# O "depois de treinar" acima e uma semente so. A conclusao de que o treinado
# nao chega ao publicado nao pode depender dela: o pipeline original nao fixa
# semente. Mesma medida em N_GATES sementes.
N_GATES = 10
peso_t, corr_t = [], []
for s in range(N_GATES):
    _, g = treinar(modelo(prior, 100, s), Xtr, ytr, Xte, yte)
    peso_t.append(float(g.max()))
    corr_t.append(float(np.corrcoef(g, prior)[0, 1]))
print(f"  DEPOIS DE TREINAR, {N_GATES} sementes")
print(f"  {'peso da banda de maior peso':<44} faixa "
      f"[{min(peso_t):.3f}; {max(peso_t):.3f}]   publicado 0.215")
print(f"  {'correlacao com o prior ANOVA':<44} faixa "
      f"[{min(corr_t):.3f}; {max(corr_t):.3f}]   publicado 0.348")
print()

# ---------------------------------------------------------------- GASOLINE
titulo("GASOLINE - SECAO 5.2, LINHA 483")

Xtr_g, Xte_g, ytr_g, yte_g = preparar("gasoline")
prior_g = compute_anova_scores(Xtr_g, ytr_g)
p_g = Xtr_g.shape[1]
mg0 = modelo(prior_g, p_g)
gg0 = gates_sem_treinar(mg0, Xte_g)
mg1 = modelo(prior_g, p_g)
_, gg1 = treinar(mg1, Xtr_g, ytr_g, Xte_g, yte_g)

for etiqueta, g in (("SEM TREINAR (a inicializacao)", gg0),
                    ("DEPOIS DE TREINAR", gg1)):
    print(f"  {etiqueta}")
    topo = int(np.argmax(g))
    top20 = np.sort(np.argsort(g)[-20:])
    print(confere("indice da banda de maior peso", float(topo), 154, 0))
    print(confere("peso dessa banda", float(g[topo]), 0.130, 3))
    print(confere("correlacao com o prior ANOVA",
                  float(np.corrcoef(g, prior_g)[0, 1]), 0.507, 3))
    dentro = int(((top20 >= 150) & (top20 <= 168)).sum())
    fora = sorted(set(top20.tolist()) - set(range(150, 169)))
    print(f"  {'janela das 20 maiores':<44} medido "
          f"{top20.min()}-{top20.max()}"
          f"      publicado 150-168")
    print(f"  {'  quantas caem em 150-168':<44} {dentro} de 20")
    print(f"  {'  as que ficam fora':<44} {fora if fora else 'nenhuma'}")
    print(f"  {'  as 19 de dentro sao contiguas?':<44} "
          f"{'sim' if dentro == 19 else 'ver acima'}")
    print()

peso_t, corr_t = [], []
for s in range(N_GATES):
    _, g = treinar(modelo(prior_g, p_g, s), Xtr_g, ytr_g, Xte_g, yte_g)
    peso_t.append(float(g.max()))
    corr_t.append(float(np.corrcoef(g, prior_g)[0, 1]))
print(f"  DEPOIS DE TREINAR, {N_GATES} sementes")
print(f"  {'peso da banda de maior peso':<44} faixa "
      f"[{min(peso_t):.3f}; {max(peso_t):.3f}]   publicado 0.130")
print(f"  {'correlacao com o prior ANOVA':<44} faixa "
      f"[{min(corr_t):.3f}; {max(corr_t):.3f}]   publicado 0.507")
print()

# ---------------------------------------------------------------- ABLACAO
titulo("ABLACAO DE BANDAS E ESTABILIDADE ENTRE FOLDS - LINHA 485")

print("  O artigo diz: 5-fold R2 0.862; zerando as 10 bandas de maior")
print("  peso cai para 0.431; zerando 10 bandas ao acaso (20 sorteios)")
print("  cai para 0.794. E 8 das 10 maiores aparecem nas 10 maiores das")
print("  cinco folds.")
print()
print("  Nao existe script para isso no repositorio; refeito aqui sobre o")
print("  mesmo protocolo do cross_validate.py.")
print()

print("  A descricao e ambigua: 'zeroing out' pode ser zerar a entrada na")
print("  avaliacao, ou retreinar sem aquelas bandas. As DUAS leituras sao")
print("  medidas abaixo, em varias sementes.")
print()
print("  E a leitura (ii) tem uma escolha que o texto nao fixa: o prior das")
print("  bandas removidas. Mantido, a porta continua pondo ~21% do peso na")
print("  banda 931, cuja entrada agora e zero, e o treino nao consegue")
print("  redistribuir esse peso (o topo e imovel). Zerado, a porta ja nasce")
print("  sem essas bandas. As duas variantes sao medidas, com os mesmos")
print("  sorteios de bandas.")
print()

N_SEM = 10


def avaliar_modelo(m, Xv, yv):
    m.eval()
    with torch.no_grad():
        pred, _ = m(torch.FloatTensor(Xv))
    return r2_score(yv, pred.squeeze().numpy())


res = {"base": [], "zera_top": [], "zera_aleat": [],
       "retreina_top": [], "retreina_aleat": [],
       "retreina_top_p0": [], "retreina_aleat_p0": [], "estab": []}


def retreinar_sem(cols, Xa, ya, Xv, yv, s, zerar_prior):
    """Leitura (ii): retreina com as colunas `cols` zeradas no treino e na
    validacao. `zerar_prior` decide se o prior dessas bandas tambem vai a
    zero (a porta nasce sem elas) ou fica como estava."""
    Xa2, Xv2 = Xa.copy(), Xv.copy()
    Xa2[:, cols] = 0.0
    Xv2[:, cols] = 0.0
    pr = prior.copy()
    if zerar_prior:
        pr[cols] = 0.0
    m2, _ = treinar(modelo(pr, 100, s), Xa2, ya, Xv2, yv)
    return avaliar_modelo(m2, Xv2, yv)


for s in range(N_SEM):
    rng = np.random.default_rng(s)
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    b, zt, za, rt, ra, rt0, ra0, tops = [], [], [], [], [], [], [], []

    for tr_i, va_i in kf.split(Xtr):
        Xa, ya = Xtr[tr_i], ytr[tr_i]
        Xv, yv = Xtr[va_i], ytr[va_i]

        m, g = treinar(modelo(prior, 100, s), Xa, ya, Xv, yv)
        top10 = np.argsort(g)[-10:]
        tops.append(set(top10.tolist()))
        b.append(avaliar_modelo(m, Xv, yv))

        # leitura (i): zerar a entrada so na avaliacao
        Xz = Xv.copy(); Xz[:, top10] = 0.0
        zt.append(avaliar_modelo(m, Xz, yv))
        sorteios = []
        for _ in range(20):
            Xr = Xv.copy()
            Xr[:, rng.choice(100, size=10, replace=False)] = 0.0
            sorteios.append(avaliar_modelo(m, Xr, yv))
        za.append(float(np.mean(sorteios)))

        # leitura (ii): retreinar com aquelas bandas zeradas, nas duas
        # variantes do prior; os mesmos sorteios servem as duas
        rt.append(retreinar_sem(top10, Xa, ya, Xv, yv, s, False))
        rt0.append(retreinar_sem(top10, Xa, ya, Xv, yv, s, True))

        s_mant, s_zero = [], []
        for _ in range(5):  # retreino e caro; 5 sorteios por fold
            idx = rng.choice(100, size=10, replace=False)
            s_mant.append(retreinar_sem(idx, Xa, ya, Xv, yv, s, False))
            s_zero.append(retreinar_sem(idx, Xa, ya, Xv, yv, s, True))
        ra.append(float(np.mean(s_mant)))
        ra0.append(float(np.mean(s_zero)))

    res["base"].append(float(np.mean(b)))
    res["zera_top"].append(float(np.mean(zt)))
    res["zera_aleat"].append(float(np.mean(za)))
    res["retreina_top"].append(float(np.mean(rt)))
    res["retreina_aleat"].append(float(np.mean(ra)))
    res["retreina_top_p0"].append(float(np.mean(rt0)))
    res["retreina_aleat_p0"].append(float(np.mean(ra0)))
    res["estab"].append(len(set.intersection(*tops)))
    print(f"    semente {s} ok")

print()


def faixa(v, pub):
    v = np.asarray(v)
    return (f"  {'':<4} mediana {np.median(v):>8.3f}  "
            f"faixa [{v.min():.3f}; {v.max():.3f}]   publicado {pub}")


print(f"  R2 5-fold sem ablacao, {N_SEM} sementes:")
print(faixa(res["base"], "0.862"))
print()
print("  leitura (i) - zerar a entrada so na avaliacao:")
print("    as 10 de maior peso:")
print(faixa(res["zera_top"], "0.431"))
print("    10 ao acaso:")
print(faixa(res["zera_aleat"], "0.794"))
print()
print("  leitura (ii-a) - retreinar com aquelas bandas zeradas, MESMO prior:")
print("    as 10 de maior peso:")
print(faixa(res["retreina_top"], "0.431"))
print("    10 ao acaso:")
print(faixa(res["retreina_aleat"], "0.794"))
print()
print("  leitura (ii-b) - retreinar com aquelas bandas zeradas, prior")
print("                   delas tambem zerado:")
print("    as 10 de maior peso:")
print(faixa(res["retreina_top_p0"], "0.431"))
print("    10 ao acaso:")
print(faixa(res["retreina_aleat_p0"], "0.794"))
print()
print("  -> a leitura (i) fica longe do publicado; as duas variantes da (ii)")
print("     ficam na vizinhanca, e a escolha do prior move o resultado das")
print("     10 de maior peso. Sem codigo no repositorio nao da para decidir")
print("     qual foi a do artigo. Em todas, a conclusao qualitativa se")
print("     mantem: tirar as bandas de maior peso derruba mais do que tirar")
print("     10 ao acaso.")
print()

e = np.asarray(res["estab"])
print(f"  bandas presentes nas 10 maiores das CINCO folds, por semente:")
print(f"    {e.tolist()}   publicado 8")
print(f"    mediana {np.median(e):g}, faixa [{e.min()}; {e.max()}]")
print(f"    o 8 publicado aparece em {int((e == 8).sum())} de {N_SEM}")
print(f"    com as {N_SEM // 2} primeiras sementes a mediana seria "
      f"{np.median(e[:N_SEM // 2]):g}: o numero depende de quantas se rodam,")
print("    e o que a medida sustenta e a faixa, nao um valor tipico.")
print()
print("  nota: o prior e calculado uma vez sobre os 172 do treino e serve")
print("  de inicializacao nas cinco folds, entao as cinco partem do mesmo")
print("  ponto. A medida acima mostra que o treino AINDA ASSIM reordena o")
print("  fim da lista - as 10 maiores nao sao identicas nas cinco folds.")
print("  Ou seja: o topo e imovel, mas as posicoes de baixo, onde os")
print("  logits estao proximos, se mexem. A estabilidade publicada nao e")
print("  evidencia de aprendizado; e o que se espera de cinco modelos que")
print("  partem da mesma inicializacao.")
print()
