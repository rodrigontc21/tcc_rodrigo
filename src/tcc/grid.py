"""Executor da grade (Estágio 5 do pipeline; ADR 021).

Roda cada célula (conjunto, braço, `seed_split`, `seed_algo`) pelo
`evaluate()` e grava um arquivo por execução, com o resultado inteiro e a
proveniência. Requisitos do pipeline e onde estão:

- **sementes explícitas e separadas por eixo:** cada tarefa carrega as duas
  (`Task`), e o `run_id` as escreve;
- **retomada por `run_id`:** um arquivo `<run_id>.json` por execução, escrito
  de forma atômica; rodar de novo pula o que já existe (`run_grid`);
- **proveniência por execução:** commit e se havia mudança não commitada,
  versões dos pacotes, Python, processador, threads (`provenance`);
- **`n_fits` e `wall_time` sempre**, junto com seleção, escores de banda,
  predições e índices do teste, que as métricas leem depois;
- **réplicas idênticas:** `identical_replicas` acusa resultados iguais entre
  sementes, com a exceção declarada dos braços determinísticos no eixo
  `seed_algo`;
- **critério de aceitação:** rodar de novo com as mesmas sementes reproduz
  os resultados (conferido em `tests/test_grid.py`).

Paralelismo só entre execuções, uma thread por processo (ADR 017 e a
orientação em 12/11), fixada no ambiente antes de os processos nascerem.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
PACKAGES = ("numpy", "scipy", "sklearn", "torch", "pandas", "rpy2")


@dataclass(frozen=True)
class ArmSpec:
    """Um braço da grade, por referência importável, para atravessar processos.

    `factory` é "módulo:nome", por exemplo "tcc.arms.gate:gate_prior";
    `kwargs` vai para a fábrica por nome. `deterministic` diz se o braço
    ignora `seed_algo` (a exceção declarada do teste de réplicas).
    """

    name: str
    factory: str
    kwargs: tuple = ()
    deterministic: bool = False

    def build(self):
        module, attr = self.factory.split(":")
        return getattr(importlib.import_module(module), attr)(**dict(self.kwargs))


@dataclass(frozen=True)
class Task:
    dataset: str
    arm: ArmSpec
    seed_split: int
    seed_algo: int

    @property
    def run_id(self) -> str:
        return f"{self.dataset}__{self.arm.name}__s{self.seed_split}__a{self.seed_algo}"


@dataclass
class GridSpec:
    """A grade: conjuntos × braços × `seed_split`, com um `seed_algo` base, e,
    para os braços estocásticos, o eixo `seed_algo` numa partição fixa."""

    datasets: list[str]
    arms: list[ArmSpec]
    seed_splits: list[int]
    seed_algo: int = 0
    algo_axis_split: int | None = None
    algo_axis_seeds: list[int] = field(default_factory=list)

    def tasks(self) -> list[Task]:
        names = [a.name for a in self.arms]
        if len(names) != len(set(names)):
            raise ValueError("dois braços com o mesmo nome")
        out = [Task(dataset=d, arm=a, seed_split=s, seed_algo=self.seed_algo)
               for d in self.datasets for a in self.arms for s in self.seed_splits]
        if self.algo_axis_split is not None:
            # Só os estocásticos; a célula que já está na grade principal
            # (mesma partição, mesmo seed_algo) não se repete.
            out += [Task(dataset=d, arm=a, seed_split=self.algo_axis_split, seed_algo=g)
                    for d in self.datasets for a in self.arms if not a.deterministic
                    for g in self.algo_axis_seeds]
        unique = {}
        for t in out:
            unique.setdefault(t.run_id, t)
        return list(unique.values())


@lru_cache(maxsize=1)
def provenance() -> dict:
    """De onde veio a execução: código, ambiente, máquina e threads.

    Calculada uma vez por processo: o `git status` na pasta do Windows vista
    pelo WSL leva perto de um segundo, mais que um treino de rede.
    """
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    versions = {}
    for pkg in PACKAGES:
        try:
            versions[pkg] = importlib.import_module(pkg).__version__
        except Exception:  # noqa: BLE001 — pacote ausente não impede a execução
            versions[pkg] = None
    cpu = platform.processor()
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            cpu = next(l.split(":", 1)[1].strip() for l in f if l.startswith("model name"))
    except (OSError, StopIteration):
        pass
    try:
        import torch
        torch_threads = torch.get_num_threads()
    except Exception:  # noqa: BLE001
        torch_threads = None
    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "python": platform.python_version(),
        "packages": versions,
        "cpu": cpu,
        "system": platform.platform(),
        "threads": {v: os.environ.get(v) for v in THREAD_VARS},
        "torch_threads": torch_threads,
    }


def _jsonable(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    if isinstance(x, set):
        return sorted(int(v) for v in x)
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


@lru_cache(maxsize=4)
def _dataset(name: str):
    from tcc.data import load
    return load(name)


def run_task(task: Task) -> dict:
    """Uma execução, num processo próprio. Devolve o registro a gravar."""
    from tcc.protocol import evaluate
    r = evaluate(task.arm.build(), _dataset(task.dataset),
                 seed_split=task.seed_split, seed_algo=task.seed_algo)
    return {
        "run_id": task.run_id, "dataset": task.dataset, "arm": task.arm.name,
        "arm_factory": task.arm.factory, "arm_kwargs": dict(task.arm.kwargs),
        "deterministic": task.arm.deterministic,
        "seed_split": task.seed_split, "seed_algo": task.seed_algo,
        "r2": r.r2, "rmsep": r.rmsep, "rmse_cv": r.rmse_cv,
        "n_fits": r.n_fits, "wall_time": r.wall_time,
        "selection": r.selection, "band_scores": r.band_scores,
        "y_pred": r.y_pred, "test_idx": r.test_idx, "hyperparams": r.hyperparams,
        "provenance": dict(provenance()),
    }


def _write_atomic(path: Path, record: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_jsonable(record), allow_nan=True), encoding="utf-8")
    os.replace(tmp, path)


def _safe(task: Task):
    try:
        return task, run_task(task), None
    except Exception:  # noqa: BLE001 — a falha de uma célula não derruba a grade
        return task, None, traceback.format_exc()


def run_grid(spec: GridSpec, out_dir: Path, processes: int = 4, log=print) -> dict:
    """Roda o que falta da grade em `out_dir`. Devolve a contagem."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = spec.tasks()
    pending = [t for t in tasks if not (out_dir / f"{t.run_id}.json").exists()]
    for v in THREAD_VARS:
        os.environ[v] = "1"  # os processos filhos herdam
    done = failed = 0
    log(f"{len(tasks)} tarefas, {len(tasks) - len(pending)} já feitas, "
        f"{len(pending)} a rodar, {processes} processo(s), 1 thread cada")
    if pending:
        with ProcessPoolExecutor(processes, mp_context=mp.get_context("spawn")) as ex:
            for fut in as_completed([ex.submit(_safe, t) for t in pending]):
                task, record, error = fut.result()
                if error is None:
                    _write_atomic(out_dir / f"{task.run_id}.json", record)
                    erro = out_dir / f"{task.run_id}.erro.txt"
                    if erro.exists():
                        erro.unlink()
                    done += 1
                else:
                    (out_dir / f"{task.run_id}.erro.txt").write_text(error, encoding="utf-8")
                    failed += 1
                    log(f"FALHOU {task.run_id}")
    return {"total": len(tasks), "skipped": len(tasks) - len(pending),
            "done": done, "failed": failed}


def load_results(out_dir: Path) -> list:
    """Os registros gravados, como `tcc.protocol.Result`, prontos para as
    métricas. A proveniência fica no arquivo; `provenance_of` a lê."""
    from tcc.protocol import Result
    out = []
    for path in sorted(Path(out_dir).glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        out.append(Result(
            r2=d["r2"], rmsep=d["rmsep"], rmse_cv=d["rmse_cv"],
            y_pred=np.asarray(d["y_pred"], dtype=float),
            test_idx=np.asarray(d["test_idx"], dtype=int),
            selection=None if d["selection"] is None else set(d["selection"]),
            band_scores=None if d["band_scores"] is None
            else np.asarray(d["band_scores"], dtype=float),
            n_fits=d["n_fits"], wall_time=d["wall_time"], hyperparams=d["hyperparams"],
            arm_name=d["arm"], dataset_name=d["dataset"],
            seed_split=d["seed_split"], seed_algo=d["seed_algo"],
        ))
    return out


def result_hash(r) -> str:
    """Hash das predições, arredondadas a 12 algarismos, para comparar execuções."""
    return hashlib.sha256(np.round(np.asarray(r.y_pred, dtype=float), 12).tobytes()).hexdigest()


def identical_replicas(results: list, deterministic: set[str]) -> list[tuple]:
    """Pares de execuções com predições idênticas onde não deveria haver.

    - eixo `seed_split`: mesmo (conjunto, braço, `seed_algo`), partições
      diferentes — nunca deveriam coincidir;
    - eixo `seed_algo`: mesmo (conjunto, braço, `seed_split`), sementes
      diferentes — só os braços determinísticos podem coincidir (exceção
      declarada).
    """
    found = []
    by_split: dict = {}
    by_algo: dict = {}
    for r in results:
        h = result_hash(r)
        by_split.setdefault((r.dataset_name, r.arm_name, r.seed_algo, h), []).append(r)
        by_algo.setdefault((r.dataset_name, r.arm_name, r.seed_split, h), []).append(r)
    for (d, a, _, _), rs in by_split.items():
        if len({r.seed_split for r in rs}) > 1:
            found.append(("seed_split", d, a, sorted(r.seed_split for r in rs)))
    for (d, a, _, _), rs in by_algo.items():
        if a not in deterministic and len({r.seed_algo for r in rs}) > 1:
            found.append(("seed_algo", d, a, sorted(r.seed_algo for r in rs)))
    return found


def provenance_of(out_dir: Path, run_id: str) -> dict:
    return json.loads((Path(out_dir) / f"{run_id}.json").read_text(encoding="utf-8"))["provenance"]
