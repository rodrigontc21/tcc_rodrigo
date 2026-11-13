"""Executor da grade (Estágio 5; ADR 021)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from tcc.data import load
from tcc.grid import (
    ArmSpec,
    GridSpec,
    identical_replicas,
    load_results,
    provenance_of,
    result_hash,
    run_grid,
)
from tcc.protocol import evaluate

MEAN = ArmSpec("mean", "tcc.arms.mean:MeanArm", deterministic=True)
PLS = ArmSpec("pls_full", "tcc.arms.pls:PLSArm", deterministic=True)
VIP = ArmSpec("vip_threshold", "tcc.arms.vip:VIPArm", deterministic=True)
GATE = ArmSpec("gate_prior", "tcc.arms.gate:gate_prior")
MLP = ArmSpec("mlp_full", "tcc.arms.gate:mlp_full")


def quiet(*_):
    pass


def small_spec(**kw):
    base = dict(datasets=["tecator"], arms=[MEAN, PLS, VIP, GATE], seed_splits=[0, 1],
                algo_axis_split=0, algo_axis_seeds=[0, 1, 2])
    base.update(kw)
    return GridSpec(**base)


# --- montagem das tarefas --------------------------------------------------------

def test_tasks_cover_the_grid_and_the_algo_axis_only_for_stochastic_arms():
    tasks = small_spec().tasks()
    ids = [t.run_id for t in tasks]
    assert len(ids) == len(set(ids))
    # grade principal: 4 braços × 2 partições; eixo do algoritmo: só o
    # estocástico, sementes 1 e 2 (a 0 já está na grade principal)
    assert len(tasks) == 8 + 2
    extra = [t for t in tasks if t.seed_algo != 0]
    assert {t.arm.name for t in extra} == {"gate_prior"}
    assert {(t.seed_split, t.seed_algo) for t in extra} == {(0, 1), (0, 2)}
    assert "tecator__gate_prior__s0__a2" in ids


def test_two_arms_with_the_same_name_are_an_error():
    with pytest.raises(ValueError):
        small_spec(arms=[GATE, ArmSpec("gate_prior", "tcc.arms.gate:gate_uniform")]).tasks()


def test_arm_spec_builds_with_keyword_arguments():
    arm = ArmSpec("b5", "tcc.arms.gate:gate_prior_scaled", kwargs=(("c", 0.3),)).build()
    assert arm.name == "gate_prior(c=0.3)"


# --- rodar, gravar, ler, retomar ----------------------------------------------------

@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    out = tmp_path_factory.mktemp("grade")
    counts = run_grid(small_spec(), out, processes=2, log=quiet)
    return out, counts


def test_every_task_is_written(ran):
    out, counts = ran
    assert counts == {"total": 10, "skipped": 0, "done": 10, "failed": 0}
    assert len(list(out.glob("*.json"))) == 10
    assert not list(out.glob("*.tmp"))


def test_loaded_results_match_a_direct_evaluate(ran):
    out, _ = ran
    loaded = {(r.arm_name, r.seed_split, r.seed_algo): r for r in load_results(out)}
    ds = load("tecator")
    # O VIP é o único aqui com seleção explícita: sem ele, perder a seleção
    # na leitura passava despercebido (mutação de 13/11).
    for spec, arm in ((PLS, "pls_full"), (VIP, "vip_threshold"), (GATE, "gate_prior")):
        direct = evaluate(spec.build(), ds, seed_split=1, seed_algo=0)
        r = loaded[(arm, 1, 0)]
        np.testing.assert_array_equal(r.y_pred, direct.y_pred)
        np.testing.assert_array_equal(r.test_idx, direct.test_idx)
        assert r.r2 == direct.r2 and r.n_fits == direct.n_fits
        assert r.selection == direct.selection
        if arm == "vip_threshold":
            assert r.selection  # não vazia
        if direct.band_scores is None:
            assert r.band_scores is None
        else:
            np.testing.assert_array_equal(r.band_scores, direct.band_scores)


def test_rerun_skips_what_is_done(ran):
    out, _ = ran
    before = {p.name: p.read_bytes() for p in out.glob("*.json")}
    counts = run_grid(small_spec(), out, processes=2, log=quiet)
    assert counts == {"total": 10, "skipped": 10, "done": 0, "failed": 0}
    assert {p.name: p.read_bytes() for p in out.glob("*.json")} == before


def test_provenance_is_recorded(ran):
    out, _ = ran
    prov = provenance_of(out, "tecator__gate_prior__s0__a0")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                          cwd=Path(__file__).resolve().parents[1]).stdout.strip()
    assert prov["commit"] == head
    assert isinstance(prov["dirty"], bool)
    assert set(prov["threads"].values()) == {"1"}
    assert prov["torch_threads"] == 1
    assert prov["packages"]["numpy"] == np.__version__
    assert prov["cpu"] and prov["python"]


def test_rerunning_from_scratch_reproduces_the_results(ran, tmp_path):
    # Critério de aceitação do pipeline: as mesmas sementes reproduzem.
    out, _ = ran
    run_grid(small_spec(), tmp_path, processes=2, log=quiet)
    a = {(r.arm_name, r.seed_split, r.seed_algo): result_hash(r) for r in load_results(out)}
    b = {(r.arm_name, r.seed_split, r.seed_algo): result_hash(r) for r in load_results(tmp_path)}
    assert a == b


def test_a_failing_task_is_recorded_and_retried(tmp_path):
    bad = ArmSpec("ruim", "tcc.arms.gate:gate_prior_scaled", kwargs=(("c", "x"),))
    spec = GridSpec(datasets=["tecator"], arms=[MEAN, bad], seed_splits=[0])
    counts = run_grid(spec, tmp_path, processes=1, log=quiet)
    assert counts["done"] == 1 and counts["failed"] == 1
    assert (tmp_path / "tecator__ruim__s0__a0.erro.txt").exists()
    assert not (tmp_path / "tecator__ruim__s0__a0.json").exists()
    again = run_grid(spec, tmp_path, processes=1, log=quiet)
    assert again["skipped"] == 1 and again["failed"] == 1  # tenta de novo


# --- réplicas idênticas -------------------------------------------------------------

def test_the_real_grid_has_no_identical_replicas(ran):
    out, _ = ran
    assert identical_replicas(load_results(out),
                              deterministic={"mean", "pls_full", "vip_threshold"}) == []


@dataclass
class F:
    dataset_name: str
    arm_name: str
    seed_split: int
    seed_algo: int
    y_pred: np.ndarray


def test_identical_replicas_are_caught_on_both_axes():
    same = np.array([1.0, 2.0, 3.0])
    rs = [F("d", "a", 0, 0, same), F("d", "a", 1, 0, same),          # eixo partição
          F("d", "b", 0, 0, same), F("d", "b", 0, 1, same),          # eixo algoritmo
          F("d", "pls", 0, 0, same), F("d", "pls", 0, 1, same)]      # exceção declarada
    found = identical_replicas(rs, deterministic={"pls"})
    assert ("seed_split", "d", "a", [0, 1]) in found
    assert ("seed_algo", "d", "b", [0, 1]) in found
    assert not any(f[2] == "pls" and f[0] == "seed_algo" for f in found)


def test_written_files_are_plain_json(ran):
    out, _ = ran
    d = json.loads((out / "tecator__pls_full__s0__a0.json").read_text(encoding="utf-8"))
    assert d["arm"] == "pls_full" and d["seed_split"] == 0 and d["deterministic"] is True
