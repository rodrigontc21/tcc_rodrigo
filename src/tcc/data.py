from __future__ import annotations

import hashlib
import io
import tarfile
import urllib.request
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

Unit = Literal["nm", "cm-1"]

# Downloads brutos ficam em data/ (não versionado); cada loader baixa na
# primeira chamada e reutiliza o arquivo local depois.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True, eq=False)
class Dataset:
    """Um conjunto espectral no formato comum a todos os braços.

    `eq=False`: a comparação elemento-a-elemento de arrays numpy quebraria o
    `__eq__` gerado por padrão pelo dataclass (ambiguidade de verdade em
    array). Ninguém precisa comparar dois Dataset por igualdade; identidade
    de objeto é suficiente.
    """

    X: np.ndarray # a matriz de espectros, (215, 100)
    y: np.ndarray # o alvo, (215,).
    axis: np.ndarray # o eixo espectral, (100,).
    unit: Unit # a unidade do eixo
    name: str
    sha256: str # hash do conteúdo carregado (ADR 004): proveniência verificável
    # Metadado extra por amostra, quando a fonte tem algo que a grade
    # principal não usa mas outro modo de protocolo precisa (ADR 006): a
    # divisão Cal/Tuning/Val Ext do Mango, usada no modo "protocolo da
    # literatura" do Estágio 2. None nos conjuntos sem esse metadado.
    metadata: dict | None = None
    # Identificador de amostra física por linha (ADR 009): réplicas da mesma
    # amostra compartilham o id, e o protocolo nunca as separa entre treino
    # e teste nem entre folds. None quando não há evidência de réplicas —
    # cada linha é então uma amostra independente.
    groups: np.ndarray | None = None


def _adjacent_replicate_groups(targets: np.ndarray) -> np.ndarray:
    """Linhas consecutivas com o vetor de alvos idêntico = mesma amostra."""
    both_nan = np.isnan(targets[1:]) & np.isnan(targets[:-1])
    same_as_next = np.all((targets[1:] == targets[:-1]) | both_nan, axis=1)
    return np.cumsum(np.concatenate([[True], ~same_as_next])) - 1


# Correção proposta das réplicas do Tecator (adendo de 05/11/2026 do ADR 009):
# juntar também as linhas com espectro e alvos idênticos. Desligada até a
# orientação decidir; ligada, muda as partições do Tecator e obriga a
# regenerar os resultados dele. O efeito está medido em
# `scripts/medir_correcao_replicas_tecator.py`.
TECATOR_GROUP_IDENTICAL_SPECTRA = False


def _merge_identical_spectra(groups: np.ndarray, X: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """Une, aos grupos dados, as linhas com espectro idêntico bit a bit e
    alvos idênticos. Os rótulos saem renumerados de 0 em diante, na ordem da
    primeira linha de cada grupo."""
    parent = {int(g): int(g) for g in np.unique(groups)}

    def root(g: int) -> int:
        while parent[g] != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g

    first_with: dict[tuple[bytes, bytes], int] = {}
    for i in range(len(X)):
        key = (np.ascontiguousarray(X[i]).tobytes(), np.ascontiguousarray(targets[i]).tobytes())
        if key in first_with:
            a, b = root(int(groups[first_with[key]])), root(int(groups[i]))
            if a != b:
                parent[max(a, b)] = min(a, b)
        else:
            first_with[key] = i

    merged = np.array([root(int(g)) for g in groups])
    _, first_row = np.unique(merged, return_index=True)
    relabel = {int(merged[r]): k for k, r in enumerate(np.sort(first_row))}
    return np.array([relabel[int(g)] for g in merged])


def _composition_groups(targets: np.ndarray) -> np.ndarray:
    """Linhas com o vetor de alvos idêntico, em qualquer posição = mesma
    amostra. NaN vira um valor comparável, para que réplicas com o mesmo
    alvo ausente também se agrupem."""
    key = np.where(np.isnan(targets), np.inf, targets)
    _, inverse = np.unique(key, axis=0, return_inverse=True)
    return inverse.ravel()


def load(name: str) -> Dataset:
    loaders = {
        "tecator": _load_tecator,
        "gasoline": _load_gasoline,
        "mango": _load_mango,
        "bioprocess": _load_bioprocess,
    }
    if name not in loaders:
        raise ValueError(
            f"dataset desconhecido: {name!r}. Disponíveis: {sorted(loaders)}."
        )
    return loaders[name]()


def _load_tecator() -> Dataset:
    import skfda.datasets

    curves, _ = skfda.datasets.fetch_tecator(return_X_y=True)
    # Segunda busca, com as_frame=True, só pelos nomes das colunas de alvo:
    # o ADR 004 exige seleção por nome, nunca por posição. Mesmo cache,
    # mesmas linhas.
    _, targets_frame = skfda.datasets.fetch_tecator(return_X_y=True, as_frame=True)

    X = np.asarray(curves.data_matrix[..., 0], dtype=float)
    axis = np.asarray(curves.grid_points[0], dtype=float)
    y = np.asarray(targets_frame["fat"], dtype=float)

    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(X).tobytes())
    digest.update(np.ascontiguousarray(axis).tobytes())
    for column in targets_frame.columns:
        digest.update(column.encode())
        digest.update(np.ascontiguousarray(targets_frame[column], dtype=float).tobytes())

    # Eixo (ADR 004): o fda.usc distribui os 100 canais como linspace(850,
    # 1050, 100), passo de 2,0202 nm; a fonte primária (StatLib) não define a
    # posição dos canais. Por indicação da orientação (18/09/2026), o eixo
    # passa a ser 850-1048 nm em passo de 2 nm. O hash acima fica sobre o
    # eixo da fonte, como prova do que foi carregado; a checagem abaixo
    # falha se a fonte mudar e a substituição deixar de ser válida.
    if not np.allclose(axis, np.linspace(850, 1050, 100), atol=1e-3):
        raise ValueError("eixo do Tecator na fonte mudou; rever o ADR 004")
    axis = 850.0 + 2.0 * np.arange(100)

    # Réplicas (ADR 009): 7 pares de linhas vizinhas com (fat, water,
    # protein) idênticos, ~19× acima do acaso, 2 deles com espectro idêntico.
    # Repetições não vizinhas são compatíveis com coincidência (alvos com uma
    # casa decimal), então só vizinhas contam como réplica.
    # (Premissa errada: há 22 pares de espectros idênticos, com alvos
    # idênticos, em linhas distantes; ver o adendo de 05/11 do ADR 009 e a
    # opção TECATOR_GROUP_IDENTICAL_SPECTRA acima.)
    targets = targets_frame[["fat", "water", "protein"]].to_numpy(dtype=float)
    groups = _adjacent_replicate_groups(targets)
    if TECATOR_GROUP_IDENTICAL_SPECTRA:
        groups = _merge_identical_spectra(groups, X, targets)

    return Dataset(
        X=X, y=y, axis=axis, unit="nm", name="tecator", sha256=digest.hexdigest(),
        groups=groups,
    )


# Dataset `gasoline` do pacote R `pls` (Kalivas 1997; Mevik & Wehrens 2007):
# 60 amostras, NIR 900-1700 nm em passo de 2 nm (401 pontos), alvo octanagem.
# Fonte confirmada na seção Data Availability do paper de referência (pgsg_0):
# CRAN, https://CRAN.R-project.org/package=pls. NÃO confundir com o dataset
# `octane` (Esbensen 2001, mrfDepth/rrcov, espelhado por skfda.fetch_octane),
# que é de detecção de outlier e não tem alvo contínuo de octanagem.
_PLS_TARBALL_URLS = (
    "https://cran.r-project.org/src/contrib/pls_2.9-0.tar.gz",
    # CRAN move versões antigas para Archive quando sai release novo
    "https://cran.r-project.org/src/contrib/Archive/pls/pls_2.9-0.tar.gz",
)


def _ensure_gasoline_rda() -> Path:
    path = DATA_DIR / "gasoline.rda"
    if path.exists():
        return path
    DATA_DIR.mkdir(exist_ok=True)
    errors = []
    for url in _PLS_TARBALL_URLS:
        try:
            with urllib.request.urlopen(url) as response:
                blob = response.read()
        except OSError as exc:
            errors.append(f"{url}: {exc}")
            continue
        with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
            member = tar.extractfile("pls/data/gasoline.RData")
            path.write_bytes(member.read())
        return path
    raise RuntimeError(f"download do pls/gasoline falhou: {errors}")


def _load_gasoline() -> Dataset:
    import rdata

    path = _ensure_gasoline_rda()
    with warnings.catch_warnings():
        # Avisos conhecidos e benignos do rdata neste arquivo: encoding
        # ausente (assume ASCII) e classe AsIs sem construtor
        warnings.simplefilter("ignore", UserWarning)
        parsed = rdata.parser.parse_file(str(path))
        constructor_dict = dict(rdata.conversion.DEFAULT_CLASS_MAP)
        # O data.frame traz o espectro como coluna-matriz (NIR), que o
        # construtor padrão de data.frame não representa; manter a lista
        # de colunas crua (dict) preserva octane e NIR por nome
        constructor_dict["data.frame"] = lambda obj, attrs: obj
        converted = rdata.conversion.convert(parsed, constructor_dict)

    gasoline = converted["gasoline"]
    y = np.asarray(gasoline["octane"], dtype=float)
    nir = gasoline["NIR"]  # xarray.DataArray com rótulos "900 nm".."1700 nm"
    X = np.asarray(nir.values, dtype=float)
    axis = np.array(
        [float(label.split()[0]) for label in nir.coords["dim_1"].values]
    )

    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(X).tobytes())
    digest.update(np.ascontiguousarray(axis).tobytes())
    digest.update(b"octane")
    digest.update(np.ascontiguousarray(y).tobytes())

    return Dataset(
        X=X, y=y, axis=axis, unit="nm", name="gasoline", sha256=digest.hexdigest()
    )


# Mango DMC v3 (Anderson et al. 2020, Mendeley Data 46htwnp833, versão 6 do
# repositório): arquivo MangoDMC_NIR_Data_v3.csv, escolhido porque o
# protocolo do projeto nomeia "Mango DMC v3" (o v4 do mesmo repositório tem
# 260 MB e safras extras fora do escopo). Alvo = DM (dry matter content, %).
# O CSV distribuído tem 12.011 amostras (safras 1-5); os papers originais
# cobrem só as safras 1-4 (11.691). Decisão de protocolo (ADR 006,
# aprovada pela orientação em 17/09/2026): cortar para Season != 5
# (equivalente a Set != "Val Ext 2", bijeção verificada), restando as
# 11.691 amostras comparáveis com a literatura. A coluna Set é preservada
# em Dataset.metadata — os papers usam a divisão Cal/Tuning/Val Ext
# codificada nela, necessária no modo "protocolo da literatura" do
# Estágio 2.
_MANGO_URL = (
    "https://data.mendeley.com/public-files/datasets/46htwnp833/files/"
    "10975117-717b-4504-a372-7845b4c42237/file_downloaded"
)
# Hash publicado pelo próprio Mendeley no registro do arquivo
_MANGO_SHA256 = "1e0e450417ed96b47b3808556706afa84a2e6441a76e380a8b64b18d85fddee1"


def _ensure_mango_csv() -> Path:
    path = DATA_DIR / "MangoDMC_NIR_Data_v3.csv"
    if not path.exists():
        DATA_DIR.mkdir(exist_ok=True)
        with urllib.request.urlopen(_MANGO_URL) as response:
            path.write_bytes(response.read())
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != _MANGO_SHA256:
        raise RuntimeError(
            f"MangoDMC_NIR_Data_v3.csv com hash inesperado: {actual} "
            f"(esperado {_MANGO_SHA256}); fonte pode ter mudado"
        )
    return path


def _load_mango() -> Dataset:
    import pandas as pd

    path = _ensure_mango_csv()
    df = pd.read_csv(path)

    # Corte de safra (ADR 006): safras 1-4 só, batendo com os papers
    # originais (11.691 amostras). Critério por nome de coluna (ADR 004).
    df = df[df["Season"] != 5].reset_index(drop=True)

    # Colunas espectrais são as de nome numérico (comprimento de onda em
    # nm); as demais são metadados (Set, Season, ..., DM)
    spectral_columns = []
    for column in df.columns:
        try:
            float(column)
        except ValueError:
            continue
        spectral_columns.append(column)

    X = df[spectral_columns].to_numpy(dtype=float)
    axis = np.array([float(c) for c in spectral_columns])

    # Canais mortos (adendo de 28/10/2026 ao ADR 006): o CSV vai de 285 a
    # 1200 nm, e 25 bandas têm o mesmo valor em todas as amostras — 285-306
    # nm e 1152-1200 nm. Não carregam informação e quebram o iPLS nos
    # intervalos das pontas (matriz singular no mdatools). O critério não
    # olha o alvo nem a partição: só "coluna constante no conjunto todo".
    # A trava falha se a fonte mudar, em vez de cortar outra coisa calada.
    constant = np.all(X == X[0], axis=0)
    dead = axis[constant]
    if not (
        constant.sum() == 25
        and np.all((dead <= 306) | (dead >= 1152))
    ):
        raise ValueError(
            f"Mango: esperadas 25 bandas constantes em 285-306 e 1152-1200 "
            f"nm, encontradas {constant.sum()}: {dead.tolist()}"
        )
    X, axis = X[:, ~constant], axis[~constant]

    y = np.asarray(pd.to_numeric(df["DM"]), dtype=float)
    # Preservada para o modo "protocolo da literatura" (ADR 006) — não
    # entra no sha256, que cobre só o conteúdo numérico já coberto acima.
    metadata = {"Set": df["Set"].to_numpy()}
    # Réplicas (ADR 009): cada fruto tem em geral duas leituras — metade das
    # linhas vizinhas repete o DM (5 casas decimais), contra 0,02% ao acaso,
    # e repetições não vizinhas de DM trazem os mesmos metadados em 98,5% dos
    # casos. Mesmo DM + mesmos metadados = mesmo fruto.
    groups = (
        df.groupby(
            ["DM", "Season", "Region", "Date", "Type", "Cultivar", "Pop"],
            dropna=False,
            sort=False,
        )
        .ngroup()
        .to_numpy()
    )

    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(X).tobytes())
    digest.update(np.ascontiguousarray(axis).tobytes())
    digest.update(b"DM")
    digest.update(np.ascontiguousarray(y).tobytes())

    return Dataset(
        X=X, y=y, axis=axis, unit="nm", name="mango", sha256=digest.hexdigest(),
        metadata=metadata, groups=groups,
    )


# Dataset `bioprocess_substrates` do pacote raman-data (RamanBench,
# Koddenbrock et al. 2026, github.com/ml-lab-htw/raman_data; fonte original
# huggingface.co/datasets/chlange/SubstrateMixRaman): 6.960 espectros Raman,
# eixo em número de onda (cm-1). Dos 8 alvos disponíveis (Glucose, Glycerol,
# Acetate, EnPump, Nitrate, Yeast_Extract, total_phosphate, total_sulfate),
# usamos GLICOSE — alvo definido pela orientação em 14/09/2026 e já
# implementado (ADR 007, aprovado com pendência: falta a confirmação da
# distribuição dos 488 espectros sem glicose): analito mais reportado na
# literatura de monitoramento de bioprocesso e de melhor razão sinal-ruído em Raman. 488 espectros não
# têm rótulo de glicose (7% do conjunto) e são descartados aqui, restando
# 6.472 — NaN no alvo não atravessa a camada de dados. A ausência não é
# uniforme (associada a EnPump e fosfato total mais altos, ver ADR 007),
# mas não se concentra num split nem num bloco de corrida — limitação
# declarada, não corrigida no loader.
def _load_bioprocess() -> Dataset:
    import raman_data

    dataset = raman_data.raman_data(
        "bioprocess_substrates", cache_dir=str(DATA_DIR / "raman_cache")
    )

    X_all = np.asarray(dataset.spectra, dtype=float)
    axis = np.asarray(dataset.raman_shifts, dtype=float)
    target_names = list(dataset.target_names)
    targets = np.asarray(dataset.targets, dtype=float)
    glucose = targets[:, target_names.index("Glucose")]  # por nome

    labeled = ~np.isnan(glucose)
    X, y = X_all[labeled], glucose[labeled]

    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(X).tobytes())
    digest.update(np.ascontiguousarray(axis).tobytes())
    for j, name in enumerate(target_names):
        digest.update(name.encode())
        digest.update(np.ascontiguousarray(targets[labeled, j]).tobytes())

    # Réplicas (ADR 009): o catálogo marca o conjunto como agrupado, sem
    # expor a amostra de cada espectro. Linhas vizinhas repetem os 8 alvos
    # muito acima do acaso, e a mesma composição reaparece em linhas
    # distantes (5.089 blocos vizinhos, 3.433 composições). Mesma composição
    # = mesma amostra, para nenhuma cair dos dois lados da partição.
    # Esses dois números são das 6.960 linhas, antes do descarte dos sem
    # glicose. Nas 6.472 que ficam, são 4.734 blocos vizinhos e 3.191
    # composições, que é o número de grupos devolvido aqui (medido em
    # 05/11/2026).
    groups = _composition_groups(targets[labeled])

    return Dataset(
        X=X, y=y, axis=axis, unit="cm-1", name="bioprocess", sha256=digest.hexdigest(),
        groups=groups,
    )
