"""As bandas da ponta do eixo do bioprocess se comportam como a 663? (25/11/2026)

A orientação (25/11) mandou tirar a banda 663 e "aplicar a mesma regra
declarada às 3 bandas da ponta do eixo, se se comportarem igual". O DIARIO de
19/11 registra 3 *espectros* com pico na última banda (1.869), e não 3 bandas
com pico fixo. Este script mede, nos dados CRUS (antes do SNV) e sem olhar
nenhum modelo, o que caracteriza a 663 e compara com as bandas das duas pontas
e com uma banda de controle:

  excesso   altura da banda sobre a vizinhança (interior: média das bandas a
            ±2; ponta: extrapolação linear das duas vizinhas de dentro);
  >5ruído   fração dos espectros com excesso acima de 5x o ruído típico da
            banda de controle (pico presente em quase todos = fixo, como a
            663; em poucos = pico solto, como um raio cósmico);
  dif rép.  diferença relativa do excesso entre as duas réplicas da mesma
            mistura, mediana (pequena = constante, de instrumento);
  corr y    correlação do excesso com a glicose.

Piloto: decisão de curadoria, nada daqui entra no texto como resultado.

Uso (de dentro do repositório): python -B scripts/conferir_bandas_ponta_bioprocess.py
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
warnings.simplefilter("ignore")
import numpy as np  # noqa: E402

from tcc.data import load  # noqa: E402

ds = load("bioprocess", drop_artifact_bands=False)
R, y, g, axis = ds.X, ds.y, ds.groups, ds.axis
p = R.shape[1]


def excess(b: int) -> np.ndarray:
    """Altura da banda b sobre a vizinhança, por espectro, em contagens."""
    if 2 <= b <= p - 3:
        return R[:, b] - (R[:, b - 2] + R[:, b + 2]) / 2
    if b >= p - 2:  # ponta de cima: extrapola das duas de dentro
        return R[:, b] - (2 * R[:, b - 1] - R[:, b - 2])
    return R[:, b] - (2 * R[:, b + 1] - R[:, b + 2])  # ponta de baixo


pares = [np.flatnonzero(g == gg) for gg in np.unique(g)]
pares = [idx for idx in pares if len(idx) == 2]
ruido = np.median(np.abs(excess(600)))

print(f"bioprocess: {R.shape[0]} espectros, {p} bandas, eixo {axis[0]:.1f} a {axis[-1]:.1f} cm-1")
print(f"ruído típico (|excesso| mediano da banda 600): {ruido:.1f} contagens\n")
print(f"{'banda':>6}{'cm-1':>9}{'excesso med.':>14}{'>5ruído':>9}{'dif rép.':>10}{'corr y':>8}")
for b in [0, 1, 2, 600, 663, p - 3, p - 2, p - 1]:
    e = excess(b)
    frac = np.mean(e > 5 * ruido)
    dif = [abs(e[i] - e[j]) / max((abs(e[i]) + abs(e[j])) / 2, 1e-9) for i, j in pares]
    corr = np.corrcoef(e, y)[0, 1]
    print(f"{b:>6}{axis[b]:>9.1f}{np.median(e):>14.1f}{frac:>9.1%}{np.median(dif):>10.3f}{corr:>8.3f}")

# Quantos espectros têm pico na última banda, e são réplicas um do outro?
e_ult = excess(p - 1)
altos = np.flatnonzero(e_ult > 5 * ruido)
print(f"\núltima banda ({p - 1}): {len(altos)} espectros acima de 5x o ruído:", altos[:20].tolist())
for i in altos[:10]:
    rep = [j for j in np.flatnonzero(g == g[i]) if j != i]
    print(f"  linha {i}: excesso {e_ult[i]:.0f}; réplica(s) {rep}:",
          [round(float(e_ult[j])) for j in rep])
