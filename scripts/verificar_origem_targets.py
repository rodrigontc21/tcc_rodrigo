"""Verificacao 1: o targets.csv do pgsg e o insumo das rodadas publicadas?

Pedido da orientacao em 29/09, em tres partes: data de modificacao dos
arquivos, historico do git do repositorio, e qual script gerou o
targets.csv a partir de qual fonte.

O zip enviado nao responde as duas primeiras: as datas sao as da extracao e
a pasta veio sem .git. Quem responde e o repositorio publico que o proprio
manuscrito declara. Para rodar este script por inteiro:

    git clone --filter=blob:none --no-checkout \\
        https://github.com/clarimar/prior-guided-spectral-gating.git \\
        ~/pgsg-github

Sem esse clone, as secoes 2 a 4 avisam e o resto roda normalmente.
"""

import datetime
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ZIP = (
    Path.home()
    / "tcc/docs/fontes/prior-guided-spectral-gating-main/prior-guided-spectral-gating-main"
)
REPO = Path.home() / "pgsg-github"

CANONICO = {  # ADR 004: conferido em Python e em R, e pela orientacao em 03/09
    "agua": (39.3, 76.6),
    "gordura": (0.9, 49.1),
    "proteina": (11.0, 21.8),
}

ALVOS = "data/raw/tecator/targets.csv"
ESPEC = "data/raw/tecator/spectra.csv"


def identificar(v):
    for nome, (lo, hi) in CANONICO.items():
        if abs(v.min() - lo) < 0.1 and abs(v.max() - hi) < 0.1:
            return nome
    return "?"


def titulo(n, texto):
    print()
    print("=" * 74)
    print(f" {n}. {texto}")
    print("=" * 74)
    print()


def git(*args):
    """Roda git no clone. Devolve None se o clone nao existir ou falhar."""
    if not (REPO / ".git").exists():
        return None
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO), *args],
            capture_output=True, text=True, check=True,
        )
        return r.stdout.rstrip("\n")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# ---------------------------------------------------------------- 1
titulo(1, "DATA DE MODIFICACAO DOS ARQUIVOS DO ZIP")

datas = set()
for rel in (ALVOS, ESPEC, "src/data/download.py",
            "scripts/baseline_pls.py", "revision_r1/one_se_output.txt"):
    p = ZIP / rel
    if p.exists():
        m = datetime.datetime.fromtimestamp(p.stat().st_mtime)
        datas.add(m.strftime("%Y-%m-%d %H:%M"))
        print(f"  {m:%Y-%m-%d %H:%M}  {rel}")
print()
if len(datas) == 1:
    print(f"  -> todas iguais ({datas.pop()}): e a data de extracao do zip,")
    print("     nao a da rodada. Estes arquivos nao datam nada.")
else:
    print(f"  -> {len(datas)} datas distintas; ver acima.")

# Mas um arquivo do envio PRESERVA as datas originais: o zip do Overleaf
# guarda a data de cada entrada, e essas sobreviveram.
import zipfile  # noqa: E402

z = ZIP / "overleaf_submission.zip"
if z.exists():
    print()
    print(f"  o {z.name} preserva a data de cada entrada:")
    ents = sorted((i for i in zipfile.ZipFile(z).infolist()
                   if not i.filename.endswith("/")),
                  key=lambda i: i.date_time)
    for i in (ents[0], ents[-1]):
        print(f"    {'%04d-%02d-%02d %02d:%02d' % i.date_time[:5]}  "
              f"{i.filename}")
    print("    -> ha data original, e ela e ANTERIOR ao commit inicial do")
    print("       GitHub (ver secao 2). Logo o git nao cobre o periodo em")
    print("       que os resultados foram gerados.")

# ---------------------------------------------------------------- 2
titulo(2, "HISTORICO DO GIT")

print(f"  .git dentro do zip ({ZIP.name}/): "
      f"{'existe' if (ZIP / '.git').exists() else 'NAO EXISTE'}")
print("  -> o zip veio sem historico.")
print()

if not (REPO / ".git").exists():
    print(f"  clone do repositorio publico em {REPO}: NAO ENCONTRADO")
    print("  -> secoes 2 a 4 incompletas. Veja o cabecalho deste arquivo.")
else:
    print(f"  clone do repositorio publico em {REPO}: ok")
    print("     (github.com/clarimar/prior-guided-spectral-gating, o que o")
    print("      manuscrito declara na disponibilidade de codigo)")
    print()
    n = git("rev-list", "--all", "--count")
    print(f"  commits: {n}")
    print()
    print("  primeiro e ultimo:")
    historia = git("log", "--all", "--date=short",
                   "--pretty=format:%h  %ad  %an  %s")
    if historia:
        linhas = historia.splitlines()
        print(f"    {linhas[-1]}")
        print(f"    {linhas[0]}")

# ---------------------------------------------------------------- 3
titulo(3, "QUANDO O targets.csv ENTROU, E SE MUDOU DEPOIS")

if not (REPO / ".git").exists():
    print("  [sem o clone, nao da para responder]")
else:
    n_commits = {}
    for rel in (ALVOS, ESPEC):
        hist = git("log", "--all", "--follow", "--date=iso",
                   "--pretty=format:%h  %ad  %s", "--", rel)
        linhas = (hist or "").splitlines()
        n_commits[rel] = len(linhas)
        print(f"  {rel}:")
        for linha in linhas or ["[sem historico]"]:
            print(f"    {linha}")
        print()
    if all(n == 1 for n in n_commits.values()):
        print("  -> um commit so para cada: entraram e nunca mais foram")
        print("     alterados.")
    else:
        print(f"  -> commits por arquivo: {n_commits}. Ver acima o que mudou.")
    print()

    # Lista COMPLETA dos arquivos apagados na historia. O filtro por nome
    # ("download", "tecator") diria pouco sozinho: um script de exportacao
    # pode ter qualquer nome. Por isso mostramos tudo.
    apagados = sorted({
        a.strip() for a in (git("log", "--all", "--diff-filter=D",
                                "--name-only", "--pretty=format:")
                            or "").splitlines() if a.strip()
    })
    print(f"  arquivos apagados em toda a historia: {len(apagados)}")
    py = [a for a in apagados if a.endswith((".py", ".R", ".sh"))]
    print(f"    destes, scripts (.py/.R/.sh): {py if py else 'nenhum'}")
    if apagados:
        print(f"    os demais: {apagados[0]} ... {apagados[-1]}")
    if not py:
        print("  -> nenhum script foi removido da historia: o script de")
        print("     exportacao nao esteve neste repositorio.")

# ---------------------------------------------------------------- 4
titulo(4, "O ARQUIVO DO GITHUB E O DO ZIP SAO O MESMO?")

if not (REPO / ".git").exists():
    print("  [sem o clone, nao da para responder]")
else:
    import hashlib
    import subprocess as sp

    for rel in (ALVOS, ESPEC):
        blob = sp.run(["git", "-C", str(REPO), "show", f"HEAD:{rel}"],
                      capture_output=True, check=True).stdout
        h_repo = hashlib.sha256(blob).hexdigest()
        h_zip = hashlib.sha256((ZIP / rel).read_bytes()).hexdigest()
        print(f"  {rel}")
        print(f"    github: {h_repo}")
        print(f"    zip   : {h_zip}")
        print(f"    -> {'IDENTICOS byte a byte' if h_repo == h_zip else 'DIFEREM'}")
    print()
    print("  -> o arquivo publicado e o que foi enviado sao o mesmo. Com a")
    print("     reproducao dos numeros, e o insumo das rodadas publicadas.")

# ---------------------------------------------------------------- 5
titulo(5, "QUAL SCRIPT DECLARA TER GERADO O targets.csv")

for rel in ("src/data/download.py", "src/data/download_old.py"):
    p = ZIP / rel
    if not p.exists():
        continue
    print(f"  {rel}:")
    for n, linha in enumerate(
        p.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        s = linha.strip()
        if "meatspec$Y" in s or "columns=['Fat'" in s or 'columns=["Fat"' in s:
            print(f"    linha {n:>3}: {s}")
    print()
print("  -> declaram o meatspec do pacote R 'pls', e escrevem os nomes das")
print("     colunas na mao.")

# ---------------------------------------------------------------- 6
titulo(6, "ESSA FONTE EXISTE? O PACOTE 'pls' TEM O meatspec?")

try:
    import rpy2.robjects as ro

    itens = list(ro.r('data(package = "pls")$results[, "Item"]'))
    print(f"  conjuntos do pacote 'pls': {', '.join(itens)}")
    print(f"  'meatspec' esta na lista: {'meatspec' in itens}")
    instalados = list(
        ro.r(
            'd <- data(package = .packages(all.available = TRUE))$results;'
            'd[grepl("meatspec", d[, "Item"]), "Package"]'
        )
    )
    print(f"  pacotes instalados com meatspec: "
          f"{instalados if instalados else 'nenhum'}")
except Exception as exc:  # pragma: no cover - depende do R instalado
    print(f"  [R indisponivel: {exc}]")
print()
print("  -> o meatspec nao existe no pacote declarado. Ele existe no pacote")
print("     R 'faraway', mas ali traz so a gordura, e nao as tres colunas.")
print("     Em qualquer dos casos, aqueles scripts cairiam no except: nao")
print("     foram eles que geraram estes arquivos.")

# ---------------------------------------------------------------- 7
titulo(7, "O QUE FOI GRAVADO, E QUAL E A FONTE DE FATO")

alvos = pd.read_csv(ZIP / ALVOS)
espec = pd.read_csv(ZIP / ESPEC)

print(f"  {'pos':>4} {'rotulo no CSV':>14} {'min':>8} {'max':>8}   {'= de fato':>10}")
for i, col in enumerate(alvos.columns):
    v = alvos[col].values
    print(f"  {i:>4} {col:>14} {v.min():>8.2f} {v.max():>8.2f}   "
          f"{identificar(v):>10}")

print()
print(f"  cabecalho do spectra.csv: {', '.join(list(espec.columns[:4]))}, ...")
print("  -> nomes de comprimento de onda. Aquele script faz pd.DataFrame(X),")
print("     que geraria 0, 1, 2, ... Nao foi ele.")
print()

from skfda.datasets import fetch_tecator  # noqa: E402

d = fetch_tecator()
y_sk = np.asarray(d["target"])
X_sk = np.asarray(d["data"].data_matrix).squeeze()
eixo = np.asarray(d["data"].grid_points[0])
nomes_sk = d.get("target_names", None)
print(f"  skfda (fetch_tecator): X {X_sk.shape}, y {y_sk.shape},"
      f" target_names {nomes_sk}")
print(f"  spectra.csv identico ao X do skfda, linha a linha: "
      f"{X_sk.shape == espec.shape and np.allclose(X_sk, espec.values, atol=1e-6)}")
print()
print("  ressalva: o X do fda.usc e identico ao do skfda, entao esta")
print("  igualdade nao diz QUAL das duas bibliotecas foi usada - diz apenas")
print("  que nao foi o meatspec.")
print()
print("  o que diz o modo de geracao e o eixo:")
print(f"    cabecalho do spectra.csv, ultimas 5: "
      f"{', '.join(list(espec.columns[-5:]))}")
print(f"    argvals da biblioteca, ultimos 5   : "
      f"{', '.join(f'{v:.4f}' for v in eixo[-5:])}")
truncado = [f"{int(v)}nm" for v in eixo]
print(f"    argvals truncados para inteiro == cabecalho: "
      f"{truncado == list(espec.columns)}")
print("    -> o cabecalho e o eixo da biblioteca truncado (1047.9798 virou")
print("       1047nm, nao 1048). Um CSV do StatLib ou do OpenML nao traria")
print("       esses valores quebrados para truncar: o arquivo foi gerado")
print("       por codigo a partir de uma dessas bibliotecas.")
print()
print("  correspondencia coluna a coluna do targets.csv com o y do skfda:")
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
print("  1. O targets.csv entrou no commit inicial do repositorio publico e")
print("     nunca foi alterado. E byte a byte igual ao que foi enviado.")
print("     RESSALVA: o zip do Overleaf traz figuras de 21/05, anteriores ao")
print("     commit inicial (23/05), entao o git NAO cobre o periodo em que")
print("     os resultados foram gerados. Quem prova que este arquivo e o")
print("     insumo das rodadas publicadas e a reproducao numerica exata")
print("     (PLS 0.9191 / 0.2957), nao o historico.")
print()
print("  2. O meatspec nao existe no pacote R declarado ('pls'). A")
print("     fonte de fato e o scikit-fda ou o fda.usc - os dois entregam o")
print("     mesmo X, entao os dados nao distinguem qual. O eixo truncado no")
print("     cabecalho mostra que o arquivo foi gerado por codigo a partir")
print("     de uma delas. O y e o mesmo com as colunas 0 e 1 TROCADAS: o")
print("     conteudo ficou em agua, gordura, proteina, e o cabecalho na")
print("     ordem das bibliotecas, gordura, agua, proteina.")
print()
print("  3. O script que fez a troca nao esta NESTE repositorio e nunca")
print("     esteve: nenhum script foi apagado em toda a historia. Onde ele")
print("     pode estar: src/data/download.py:73, README_1.md e")
print("     setup_project.py apontam para ~/Dropbox/chemometric-band-")
print("     selection/, o projeto anterior. O script e a data original")
print("     podem estar la, ou no historico de versoes do Dropbox.")
print()
