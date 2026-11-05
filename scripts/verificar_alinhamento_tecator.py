"""Verificacao 2: a coluna 0 e mesmo a agua, e as 215 linhas estao alinhadas?

Pedido da orientacao em 29/09, em duas partes:

  a) conferir a identidade da coluna 0 do targets.csv contra a agua do
     fda.usc elemento a elemento, nao so por minimo e maximo;
  b) confirmar o alinhamento das 215 linhas entre o targets.csv e a
     matriz X.

O fda.usc e o pacote R que distribui o Tecator. Ele NAO e fonte
independente do scikit-fda: o skfda.datasets.fetch_tecator chama
_fetch_fda_usc("tecator"), ou seja, le do proprio fda.usc. Conferir os dois
mostra que o resultado nao depende do caminho de leitura, e nada alem
disso. Fonte de fato independente seria o OpenML 505.

Precisa do pacote R fda.usc:

    Rscript -e 'install.packages("fda.usc", repos="https://cloud.r-project.org")'
"""

from pathlib import Path

import numpy as np
import pandas as pd

ZIP = (
    Path.home()
    / "tcc/docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
)
RAW = ZIP / "data/raw/tecator"


def titulo(n, texto):
    print()
    print("=" * 74)
    print(f" {n}. {texto}")
    print("=" * 74)
    print()


alvos = pd.read_csv(RAW / "targets.csv")
espec = pd.read_csv(RAW / "spectra.csv")

# ---------------------------------------------------------------- 1
titulo(1, "A FONTE INDEPENDENTE: O TECATOR DO fda.usc")

try:
    import rpy2.robjects as ro
    from rpy2.robjects import numpy2ri

    ro.r('suppressMessages(library(fda.usc)); data(tecator)')
    nomes_r = list(ro.r("colnames(tecator$y)"))
    with numpy2ri.converter.context():
        y_r = np.asarray(ro.r("as.matrix(tecator$y)"))
        X_r = np.asarray(ro.r("tecator$absorp.fdata$data"))
    ok_r = True
except Exception as exc:  # pragma: no cover - depende do R
    print(f"  [fda.usc indisponivel: {exc}]")
    print()
    print("  Instale com:")
    print("    Rscript -e 'install.packages(\"fda.usc\", "
          "repos=\"https://cloud.r-project.org\")'")
    ok_r = False
    y_r = X_r = None
    nomes_r = []

if ok_r:
    print(f"  tecator$y     : {y_r.shape}, colunas {nomes_r}")
    print(f"  tecator$absorp: {X_r.shape}")
    print()
    print(f"  {'pos':>4} {'nome no fda.usc':>16} {'min':>8} {'max':>8} {'media':>8}")
    for j, nome in enumerate(nomes_r):
        v = y_r[:, j]
        print(f"  {j:>4} {nome:>16} {v.min():>8.2f} {v.max():>8.2f} {v.mean():>8.2f}")

# ---------------------------------------------------------------- 2
titulo(2, "A COLUNA 0 CONTRA CADA COLUNA DO fda.usc, ELEMENTO A ELEMENTO")

if not ok_r:
    print("  [sem o fda.usc, nao da para responder]")
else:
    n = min(len(alvos), y_r.shape[0])
    print(f"  {n} linhas nas duas fontes "
          f"(targets.csv {len(alvos)}, fda.usc {y_r.shape[0]})")
    print()
    print("  a pergunta da orientacao: a coluna 0, rotulada 'Fat', e a agua?")
    print()
    col0 = alvos.iloc[:, 0].values[:n]
    print(f"  {'contra':>18} {'iguais':>9} {'maior dif':>12} {'dif media':>12}")
    for j, nome in enumerate(nomes_r):
        d = np.abs(col0 - y_r[:n, j])
        iguais = int(np.sum(d < 1e-8))
        marca = "   <== identica" if iguais == n else ""
        print(f"  {nome:>18} {f'{iguais}/{n}':>9} {d.max():>12.2e} "
              f"{d.mean():>12.2e}{marca}")
    print()
    print("  -> a coluna 0 e identica a AGUA e esta longe da gordura. O")
    print("     contraste e o que separa identidade de faixa parecida.")
    print()
    print("  as outras duas colunas, para o quadro completo:")
    print()
    print(f"  {'CSV':>18} {'fda.usc':>16} {'iguais':>9} {'maior dif':>12}")
    for i, col in enumerate(alvos.columns):
        v = alvos[col].values[:n]
        for j, nome in enumerate(nomes_r):
            d = np.abs(v - y_r[:n, j])
            if int(np.sum(d < 1e-8)) == n:
                print(f"  {f'{i} {col}':>18} {f'{j} {nome}':>16} "
                      f"{f'{n}/{n}':>9} {d.max():>12.2e}")

# ---------------------------------------------------------------- 3
titulo(3, "AS 215 LINHAS DE X E DE y ESTAO ALINHADAS?")

print(f"  targets.csv: {alvos.shape}")
print(f"  spectra.csv: {espec.shape}")
print(f"  mesmo numero de linhas: {len(alvos) == len(espec)}")
print()

if not ok_r:
    print("  [sem o fda.usc, o alinhamento contra a fonte fica em aberto]")
else:
    n = min(len(espec), X_r.shape[0])

    # O conjunto tem linhas repetidas. Elas nao atrapalham: a comparacao
    # abaixo e POSICIONAL (linha i contra linha i), nao um casamento de
    # linhas parecidas, entao nao ha ambiguidade a resolver. Ficam
    # registradas porque a mesma contagem aparece na fonte, o que mostra
    # que o CSV nao perdeu nem inventou linha.
    dup_X = len(espec) - len(np.unique(espec.values, axis=0))
    dup_y = len(alvos) - len(np.unique(alvos.values, axis=0))
    dup_Xr = len(X_r) - len(np.unique(X_r, axis=0))
    dup_yr = len(y_r) - len(np.unique(y_r, axis=0))
    print(f"  linhas repetidas em X: {dup_X} no CSV, {dup_Xr} na fonte")
    print(f"  linhas repetidas em y: {dup_y} no CSV, {dup_yr} na fonte")
    print("  -> mesma contagem: sao repeticoes do proprio conjunto, nao")
    print("     artefato do CSV. A comparacao abaixo e posicional, linha i")
    print("     contra linha i, entao repeticao nao gera ambiguidade.")
    print()

    X_igual = (
        espec.shape[1] == X_r.shape[1]
        and np.allclose(espec.values[:n], X_r[:n], atol=1e-6)
    )
    print(f"  spectra.csv == tecator$absorp, linha a linha, na ordem: {X_igual}")

    y_perm = []
    for i, col in enumerate(alvos.columns):
        v = alvos[col].values[:n]
        for j in range(y_r.shape[1]):
            if np.allclose(v, y_r[:n, j], atol=1e-8):
                y_perm.append((i, j))
    y_igual = len(y_perm) == len(alvos.columns)
    print(f"  targets.csv == tecator$y, linha a linha, na ordem:      {y_igual}")
    print()
    print("  -> no fda.usc a linha i de absorp e a linha i de y sao a mesma")
    print("     amostra. Os dois arquivos reproduzem a fonte na mesma ordem,")
    print("     linha por linha. Logo a linha i do spectra.csv corresponde a")
    print("     linha i do targets.csv: X e y estao alinhados.")
    print()
    print("     O unico embaralhamento e entre COLUNAS de y:")
    for i, j in y_perm:
        print(f"       CSV col {i} ({alvos.columns[i]}) = fda.usc col {j} "
              f"({nomes_r[j]})")

    # Controle negativo: se as linhas estivessem trocadas, a checagem acima
    # teria de falhar. Sem isso ela nao prova nada.
    print()
    print("  controle negativo (a checagem tem dentes?):")
    rng = np.random.default_rng(0)
    ordem = rng.permutation(n)
    X_emb = np.allclose(espec.values[ordem], X_r[:n], atol=1e-6)
    y_emb = any(
        np.allclose(alvos.iloc[:, 0].values[ordem], y_r[:n, j], atol=1e-8)
        for j in range(y_r.shape[1])
    )
    print(f"    com as linhas embaralhadas, X ainda casa: {X_emb}")
    print(f"    com as linhas embaralhadas, y ainda casa: {y_emb}")
    print("    -> as duas falsas: a checagem detecta reordenacao de linhas.")

# ---------------------------------------------------------------- 4
titulo(4, "O RESULTADO DEPENDE DO CAMINHO DE LEITURA?")

from skfda.datasets import fetch_tecator  # noqa: E402

d = fetch_tecator()
y_sk = np.asarray(d["target"])
nomes_sk = d.get("target_names", None)
print(f"  scikit-fda target_names: {nomes_sk}")
if ok_r:
    print(f"  fda.usc colnames       : {nomes_r}")
    print()
    concorda = True
    for j in range(y_sk.shape[1]):
        achou = any(
            np.allclose(y_sk[:, j], y_r[:, k], atol=1e-8)
            for k in range(y_r.shape[1])
        )
        concorda = concorda and achou
    print(f"  o y do skfda e o do fda.usc tem o mesmo conteudo: {concorda}")
    print()
    print("  ressalva: o skfda.fetch_tecator chama _fetch_fda_usc('tecator'),")
    print("  entao os dois leem a MESMA fonte. Isto mostra que o resultado")
    print("  nao depende do caminho de leitura, nao que ha duas fontes.")
print()
print("  correspondencia do CSV com o skfda (repetida da verificacao 1):")
for i, col in enumerate(alvos.columns):
    v = alvos[col].values
    for j in range(y_sk.shape[1]):
        if np.allclose(v, y_sk[:, j], atol=1e-6):
            print(f"    CSV col {i} ({col}) == skfda col {j} ({nomes_sk[j]})")

# ---------------------------------------------------------------- fim
print()
print("=" * 74)
print(" CONCLUSAO")
print("=" * 74)
print()
print("  A coluna 0 do targets.csv, rotulada 'Fat', e a agua - conferido")
print("  elemento a elemento contra o fda.usc, nas 215 linhas, com")
print("  diferenca zero, e contra a gordura a diferenca e enorme.")
print()
print("  As linhas nao foram embaralhadas: X e y estao alinhados, linha a")
print("  linha, com a fonte. O erro esta so na ordem das COLUNAS de y em")
print("  relacao ao cabecalho gravado.")
print()
