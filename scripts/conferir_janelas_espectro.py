"""As bandas das fontes aparecem nos nossos espectros? (docs/janelas_quimicas.md)

Para cada conjunto, o espectro médio de todas as amostras (sem o alvo: só
X), e a segunda derivada dele (Savitzky-Golay, polinômio 2), em que cada
banda de absorção vira um vale. Para cada banda de `src/tcc/windows.py`,
procura o vale mais próximo a até 30 unidades do eixo (nm ou cm⁻¹) e mede o
deslocamento.

Não muda as janelas, que continuam vindo das fontes: confere se as bandas
citadas aparecem nos nossos dados e quanto se deslocam, para pesar a
largura da janela.

Uso: python -B conferir_janelas_espectro.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
from scipy.signal import argrelextrema, savgol_filter

from tcc.data import load
from tcc.windows import BANDS

ALCANCE = 30.0  # nm ou cm⁻¹
JANELA_SG = {"tecator": 11, "gasoline": 11, "mango": 9, "bioprocess": 9}


def main():
    for nome in ("tecator", "gasoline", "mango", "bioprocess"):
        ds = load(nome)
        axis = np.asarray(ds.axis, dtype=float)
        media = ds.X.mean(axis=0)
        d2 = savgol_filter(media, JANELA_SG[nome], 2, deriv=2)
        vales = argrelextrema(d2, np.less, order=2)[0]
        unid = "cm⁻¹" if nome == "bioprocess" else "nm"
        print(f"\n{nome} ({len(ds.X)} espectros, {axis.min():.0f}–{axis.max():.0f} {unid}, "
              f"segunda derivada com janela de {JANELA_SG[nome]} pontos)")
        for b in BANDS[nome]:
            perto = [v for v in vales if abs(axis[v] - b.position) <= ALCANCE]
            if not perto:
                print(f"  {b.position:>6.0f} {b.role:<9} sem vale a até {ALCANCE:.0f} {unid}"
                      f"   ({b.assignment})")
                continue
            v = min(perto, key=lambda i: abs(axis[i] - b.position))
            print(f"  {b.position:>6.0f} {b.role:<9} vale em {axis[v]:7.1f}  "
                  f"desvio {axis[v] - b.position:+6.1f} {unid}   ({b.assignment})")


if __name__ == "__main__":
    main()
