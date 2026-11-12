"""O B4 contra o artigo: critério 2 do Estágio 3 do pipeline (ADR 017).

"`gate_prior` deve reproduzir o modelo publicado do grupo dentro da
dispersão entre sementes." O ADR 013 fixou como isso se lê: os R² da
Tabela 1 vêm do modelo **treinado** com a receita do artigo, e a comparação
é como faixa entre sementes, não como ponto.

Aqui a reimplementação do braço (`tcc.arms.gate.GateNet`) é treinada no
**protocolo do próprio artigo**, e não no deste trabalho:
- dados do repositório do artigo, `train_test_split(test_size=0.2,
  random_state=42)`, Z-score de X e de y no treino;
- prior ANOVA sobre o treino inteiro;
- Adam, lr 0,01, `weight_decay` 1e-4 em todos os parâmetros (o B4-fiel),
  KL 0,001, até 200 épocas, paciência 30 **olhando o teste**, modelo final
  da última época, como o `train_light.py`.

É por isso que não passa pelo `evaluate()`: o contrato do protocolo não deixa
um braço ver o teste, e o artigo deixa. Este script é só a reprodução.

Em cada semente roda também o `BandSelectNetLight` original, da cópia local
do código do artigo (fora do git; carregado sem gravar `__pycache__`), com o
mesmo laço, para conferir semente a semente. A referência publicada é a
linha "Ours (ANOVA)" da Tabela 1 (0,941, que é água: ADR 013), e a medida
anterior deste trabalho é a do relatório 3 (0,922 [0,80; 0,96] na água e
0,922 [0,84; 0,94] na gordura, 10 sementes).

Uso: python -B reproduzir_b4_artigo.py [sementes, padrão 10]
"""

import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from tcc.arms.gate import CLIP, GateNet, anova_prior, prior_logits

PGSG = (RAIZ / "docs" / "fontes" / "prior-guided-spectral-gating-main"
        / "prior-guided-spectral-gating-main")
COLUNAS = {0: "água (o que foi publicado)", 1: "gordura"}


def original():
    caminho = PGSG / "src" / "models" / "band_select_net_light.py"
    spec = importlib.util.spec_from_file_location("pgsg_light_original", caminho)
    mod = importlib.util.module_from_spec(spec)
    antes = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = antes
    return mod


def preparar(coluna):
    X = pd.read_csv(PGSG / "data/raw/tecator/spectra.csv").values
    y = pd.read_csv(PGSG / "data/raw/tecator/targets.csv").values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    sx, sy = StandardScaler(), StandardScaler()
    X_tr, X_te = sx.fit_transform(X_tr), sx.transform(X_te)
    y_tr, y_te = sy.fit_transform(y_tr), sy.transform(y_te)
    return X_tr, X_te, y_tr[:, coluna], y_te[:, coluna]


def treinar_como_o_artigo(modelo, saida, X_tr, y_tr, X_te, y_te):
    """O laço do `train_light.py`: paciência no teste, última época."""
    Xtr, ytr = torch.FloatTensor(X_tr), torch.FloatTensor(y_tr)
    Xte, yte = torch.FloatTensor(X_te), torch.FloatTensor(y_te)
    crit = nn.MSELoss()
    kl = modelo.get_kl_loss if hasattr(modelo, "get_kl_loss") else modelo.kl
    opt = torch.optim.Adam(modelo.parameters(), lr=0.01, weight_decay=1e-4)
    melhor, sem = float("inf"), 0
    for _ in range(200):
        modelo.train()
        perda = crit(saida(modelo, Xtr).squeeze(), ytr) + 0.001 * kl()
        opt.zero_grad()
        perda.backward()
        opt.step()
        modelo.eval()
        with torch.no_grad():
            r = torch.sqrt(crit(saida(modelo, Xte).squeeze(), yte))
        if r < melhor:
            melhor, sem = r, 0
        else:
            sem += 1
            if sem >= 30:
                break
    modelo.eval()
    with torch.no_grad():
        return float(r2_score(y_te, saida(modelo, Xte).squeeze().numpy()))


def main():
    sementes = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    orig = original()
    torch.set_num_threads(1)
    for coluna, rotulo in COLUNAS.items():
        X_tr, X_te, y_tr, y_te = preparar(coluna)
        prior = anova_prior(X_tr, y_tr)
        r_orig, r_nosso = [], []
        for s in range(sementes):
            torch.manual_seed(s)
            m = orig.BandSelectNetLight(n_bands=100, n_outputs=1, prior_scores=prior,
                                        hidden_dim=16, dropout=0.5)
            r_orig.append(treinar_como_o_artigo(m, lambda mod, X: mod(X)[0],
                                                X_tr, y_tr, X_te, y_te))
            torch.manual_seed(s)
            n = GateNet(100, draw_gate=False)
            n.set_gate(prior_logits(prior), np.clip(prior, CLIP, 1 - CLIP))
            r_nosso.append(treinar_como_o_artigo(n, lambda mod, X: mod(X),
                                                 X_tr, y_tr, X_te, y_te))
        r_orig, r_nosso = np.array(r_orig), np.array(r_nosso)
        iguais = int(np.sum(r_orig == r_nosso))
        print(f"coluna {coluna}, {rotulo}: {sementes} sementes")
        print(f"  original : mediana {np.median(r_orig):.3f} "
              f"[{r_orig.min():.2f}; {r_orig.max():.2f}]")
        print(f"  nosso    : mediana {np.median(r_nosso):.3f} "
              f"[{r_nosso.min():.2f}; {r_nosso.max():.2f}]")
        print(f"  R² idêntico ao original em {iguais} de {sementes} sementes; "
              f"maior diferença {np.abs(r_orig - r_nosso).max():.2e}")
        print("  por semente:", " ".join(f"{v:.4f}" for v in r_nosso), "\n", flush=True)
    print("referência: Tabela 1, 'Ours (ANOVA)' = 0,941 (água); relatório 3: "
          "0,922 [0,80; 0,96] na água e 0,922 [0,84; 0,94] na gordura")


if __name__ == "__main__":
    main()
