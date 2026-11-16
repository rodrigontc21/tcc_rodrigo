"""A configuração da grade final (src/tcc/final_grid.py)."""

from __future__ import annotations

import pytest

from tcc import final_grid as G
from tcc.arms.gate import ARTICLE, TrainRecipe


def test_final_mode_refuses_while_something_is_undecided():
    with pytest.raises(ValueError) as e:
        G.specs("final")
    msg = str(e.value)
    for item in ("c_TOST do mango", "receita de treino do mango", "SEED_SPLITS",
                 "partição do eixo seed_algo", "sementes do eixo seed_algo"):
        assert item in msg


def test_final_mode_refuses_pilot_partitions(monkeypatch):
    monkeypatch.setattr(G, "C_TOST", {**G.C_TOST, "mango": 0.04})
    monkeypatch.setattr(G, "RECIPE", {**G.RECIPE, "mango": ARTICLE})
    monkeypatch.setattr(G, "SEED_SPLITS", range(100, 200))
    monkeypatch.setattr(G, "ALGO_AXIS_SEEDS", [0, 1])
    monkeypatch.setattr(G, "ALGO_AXIS_SPLIT", 29)
    with pytest.raises(ValueError, match="≥ 100"):
        G.specs("final")
    monkeypatch.setattr(G, "ALGO_AXIS_SPLIT", 100)
    specs = G.specs("final")
    assert [s.datasets for s in specs] == [[d] for d in G.DATASETS]
    assert specs[0].seed_splits == list(range(100, 200))


def test_trial_never_touches_final_partitions(monkeypatch):
    monkeypatch.setitem(G.TRIAL, "seed_splits", (0, 100))
    with pytest.raises(ValueError, match="não toca"):
        G.specs("ensaio")


def test_unknown_mode_is_an_error():
    with pytest.raises(ValueError):
        G.specs("piloto")


@pytest.fixture(scope="module")
def trial():
    return {s.datasets[0]: s for s in G.specs("ensaio")}


def test_trial_has_every_arm_of_the_final_grid(trial):
    assert list(trial) == ["tecator", "gasoline", "mango"]
    for spec in trial.values():
        names = [a.name for a in spec.arms]
        assert len(names) == len(set(names)) == 6 + 23
        assert spec.seed_splits == [0]


def test_each_dataset_runs_the_fixed_c_grid_plus_its_own_c_tost(trial):
    names = {a.name for a in trial["tecator"].arms}
    for c in ("1", "0.5", "0.3", "0.17", "0.1", "0.054", "0.026", "0", "0.0306"):
        assert f"gate_prior(c={c})" in names and f"mlp_weighted(c={c})" in names
    assert "gate_prior(c=0.0289)" in {a.name for a in trial["gasoline"].arms}
    assert "gate_prior(c=0.0306)" not in {a.name for a in trial["gasoline"].arms}


def test_every_spec_name_is_the_name_the_arm_gives_itself(trial):
    # O executor recusa nome diferente (revisão de 16/11); aqui se confere
    # antes de rodar, em todos os braços do ensaio.
    for spec in trial.values():
        for a in spec.arms:
            assert a.build().name == a.name


def test_mango_trial_nets_carry_the_recipe_and_classical_arms_do_not(trial):
    mango = {a.name: a for a in trial["mango"].arms}
    assert "gate_prior[ensaio]" in mango and "gate_prior(c=0.0417)[ensaio]" in mango
    assert "pls_full" in mango and "ipls" in mango
    assert dict(mango["gate_prior[ensaio]"].kwargs)["recipe"] == TrainRecipe(name="ensaio")
    assert not any("[" in a.name for a in trial["tecator"].arms)


def test_trial_tasks_include_the_algo_axis_for_stochastic_arms_only(trial):
    tasks = trial["tecator"].tasks()
    det = {a.name for a in trial["tecator"].arms if a.deterministic}
    assert det == {"pls_full", "ipls", "vip_threshold"}
    assert len(tasks) == 29 + (29 - 3) * 2
    assert not {t.arm.name for t in tasks if t.seed_algo != 0} & det


def test_roles_follow_the_recipe_in_the_net_names():
    assert G.roles("tecator", ARTICLE) == G.ROLES
    r = G.roles("mango", TrainRecipe(name="x"))
    assert r["A1"] == "pls_full" and r["B4"] == "gate_prior[x]" and r["B1"] == "mlp_full[x]"
