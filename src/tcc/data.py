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

    return Dataset(
        X=X, y=y, axis=axis, unit="nm", name="tecator", sha256=digest.hexdigest()
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
# Atenção documentada: os papers do v3 reportam 11.691 amostras (safras
# 1-4); o CSV atual traz 12.011 — a atualização de 2024 acrescentou 320
# amostras de uma safra 5 ("Val Ext 2"). Carregamos o arquivo como
# distribuído; qualquer recorte de safra é decisão de protocolo, não do
# loader.
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
    y = np.asarray(pd.to_numeric(df["DM"]), dtype=float)

    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(X).tobytes())
    digest.update(np.ascontiguousarray(axis).tobytes())
    digest.update(b"DM")
    digest.update(np.ascontiguousarray(y).tobytes())

    return Dataset(
        X=X, y=y, axis=axis, unit="nm", name="mango", sha256=digest.hexdigest()
    )


# Dataset `bioprocess_substrates` do pacote raman-data (RamanBench,
# Koddenbrock et al. 2026, github.com/ml-lab-htw/raman_data; fonte original
# huggingface.co/datasets/chlange/SubstrateMixRaman): 6.960 espectros Raman,
# eixo em número de onda (cm-1). Dos 8 alvos disponíveis (Glucose, Glycerol,
# Acetate, EnPump, Nitrate, Yeast_Extract, total_phosphate, total_sulfate),
# usamos GLICOSE — PROVISÓRIO: é o analito mais reportado na literatura de
# monitoramento de bioprocesso que levantamos, mas a escolha ainda será
# confirmada com a orientação. 488 espectros não têm rótulo de glicose
# (has_missing_labels do catálogo) e são descartados aqui, restando 6.472 —
# NaN no alvo não atravessa a camada de dados.
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

    return Dataset(
        X=X, y=y, axis=axis, unit="cm-1", name="bioprocess", sha256=digest.hexdigest()
    )
