"""Braços neurais (ADR 017): B1, B2, B2'(c), B3, B4-fiel, B4-limpo e B5(c)."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
import torch

from tcc.arms.base import Budget, CVFolds
from tcc.arms.gate import (
    GateNet,
    anova_prior,
    gate_prior,
    gate_prior_faithful,
    gate_prior_scaled,
    gate_uniform,
    mlp_full,
    mlp_weighted,
    mlp_weighted_scaled,
    prior_logits,
)

N_FOLDS = 5
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = (ROOT / "docs" / "fontes" / "prior-guided-spectral-gating-main"
            / "prior-guided-spectral-gating-main" / "src" / "models"
            / "band_select_net_light.py")


def all_arms():
    return [mlp_full(), mlp_weighted(), mlp_weighted_scaled(c=0.3), gate_uniform(),
            gate_prior_faithful(), gate_prior(), gate_prior_scaled(c=0.3)]


@pytest.fixture(scope="module")
def problem():
    """Espectros lisos com sinal nas bandas 10 a 14."""
    rng = np.random.default_rng(0)
    n, p = 80, 40
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 10:15].sum(axis=1) * 2.0 + 0.1 * rng.normal(size=n)
    folds: CVFolds = []
    for chunk in np.array_split(np.arange(n), N_FOLDS):
        folds.append((np.setdiff1d(np.arange(n), chunk), chunk))
    return X, y, folds


def fit(arm, problem, seed=0, y=None):
    X, y0, folds = problem
    return arm.fit(X, y0 if y is None else y, folds, np.random.default_rng(seed), Budget())


# --- a reimplementação contra o original -----------------------------------

def _load_original():
    """Carrega o módulo do artigo sem gravar `__pycache__` na pasta dele."""
    spec = importlib.util.spec_from_file_location("pgsg_light_original", ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.mark.skipif(not ORIGINAL.exists(), reason="cópia local do código do artigo ausente")
def test_reimplementation_matches_the_original_model():
    # Mesma semente: os parâmetros nascem iguais (a ordem de criação é a do
    # original sem prior), e com a mesma porta escrita por cima, a saída, o KL
    # e dez passos de treino com o Adam do artigo dão o mesmo resultado.
    original = _load_original()
    p = 100
    rng = np.random.default_rng(1)
    s = rng.uniform(size=p)
    X = torch.as_tensor(rng.normal(size=(30, p)), dtype=torch.float32)
    y = torch.as_tensor(rng.normal(size=30), dtype=torch.float32)

    torch.manual_seed(7)
    ref = original.BandSelectNetLight(n_bands=p, n_outputs=1, prior_scores=None,
                                      hidden_dim=16, dropout=0.5)
    torch.manual_seed(7)
    ours = GateNet(p)
    assert sum(t.numel() for t in ours.parameters()) == 1765  # o número do artigo
    for (n_ref, t_ref), (n_our, t_our) in zip(ref.state_dict().items(),
                                              _ordered_like_original(ours)):
        assert torch.equal(t_ref, t_our), (n_ref, n_our)

    with torch.no_grad():
        ref.gating.gates.copy_(torch.as_tensor(prior_logits(s), dtype=torch.float32))
        ref.gating.prior_probs.copy_(torch.as_tensor(np.clip(s, 1e-7, 1 - 1e-7),
                                                     dtype=torch.float32))
    ours.set_gate(prior_logits(s), np.clip(s, 1e-7, 1 - 1e-7))
    assert torch.equal(ref.get_kl_loss(), ours.kl())

    opt_ref = torch.optim.Adam(ref.parameters(), lr=0.01, weight_decay=1e-4)
    opt_our = torch.optim.Adam(_params_like_original(ours), lr=0.01, weight_decay=1e-4)
    for _ in range(10):
        for net, opt, out in ((ref, opt_ref, lambda m: m(X)[0]), (ours, opt_our, lambda m: m(X))):
            net.train()
            torch.manual_seed(3)  # o dropout sorteia igual nos dois
            loss = torch.nn.functional.mse_loss(out(net).squeeze(1), y)
            kl = net.get_kl_loss() if net is ref else net.kl()
            opt.zero_grad()
            (loss + 1e-3 * kl).backward()
            opt.step()
    ref.eval()
    ours.eval()
    with torch.no_grad():
        assert torch.equal(ref(X)[0], ours(X))
        assert torch.equal(ref.gating.gates, ours.gates)


@pytest.mark.skipif(not ORIGINAL.exists(), reason="cópia local do código do artigo ausente")
def test_without_drawing_the_gate_matches_the_original_built_with_a_prior():
    # A reprodução do artigo (scripts/reproduzir_b4_artigo.py) constrói como o
    # original com prior, que não sorteia a porta: a fc1 nasce de outro ponto
    # da sequência aleatória.
    original = _load_original()
    s = np.random.default_rng(2).uniform(size=50)
    torch.manual_seed(11)
    ref = original.BandSelectNetLight(n_bands=50, n_outputs=1, prior_scores=s,
                                      hidden_dim=16, dropout=0.5)
    torch.manual_seed(11)
    ours = GateNet(50, draw_gate=False)
    ours.set_gate(prior_logits(s), np.clip(s, 1e-7, 1 - 1e-7))
    for (_, t_ref), (_, t_our) in zip(ref.state_dict().items(), _ordered_like_original(ours)):
        assert torch.equal(t_ref, t_our)


def _ordered_like_original(net):
    # O original guarda a porta em `gating.gates` e `gating.prior_probs`.
    sd = net.state_dict()
    order = ["gates", "prior_probs", "fc1.weight", "fc1.bias", "fc2.weight", "fc2.bias",
             "bn.weight", "bn.bias", "bn.running_mean", "bn.running_var",
             "bn.num_batches_tracked"]
    return [(k, sd[k]) for k in order]


def _params_like_original(net):
    return [net.gates, net.fc1.weight, net.fc1.bias, net.fc2.weight, net.fc2.bias,
            net.bn.weight, net.bn.bias]


# --- comparabilidade entre os braços ----------------------------------------

def test_the_regressor_starts_identical_in_every_arm(problem):
    # Pipeline, Estágio 3: o regressor é byte a byte o mesmo. A rede inicial
    # vem da mesma função que o `fit` usa.
    X, y, _ = problem
    states = []
    for arm in all_arms():
        net, _, _ = arm.initial_net(X, y, seed=123)
        states.append({k: v.clone() for k, v in net.state_dict().items()
                       if not k.startswith(("gates", "prior_probs"))})
    assert set(states[0]) >= {"fc1.weight", "fc2.weight", "bn.weight"}
    for other in states[1:]:
        for k in states[0]:
            assert torch.equal(states[0][k], other[k]), k


def test_effective_hyperparameters_differ_only_where_allowed():
    # Pipeline, Estágio 3, critério 3: só os campos da porta mudam.
    allowed = {"gated", "init", "c", "trainable", "gate_weight_decay", "kl_ref"}
    configs = [asdict(a.config) for a in all_arms()]
    assert set(configs[0]) == allowed  # nada de hiperparâmetro de treino por braço
    import tcc.arms.gate as g
    shared = {k: getattr(g, k) for k in ("TEMPERATURE", "HIDDEN", "DROPOUT", "LR",
                                         "MAX_EPOCHS", "PATIENCE", "KL_WEIGHT",
                                         "WEIGHT_DECAY")}
    assert shared == {"TEMPERATURE": 5.0, "HIDDEN": 16, "DROPOUT": 0.5, "LR": 0.01,
                      "MAX_EPOCHS": 200, "PATIENCE": 30, "KL_WEIGHT": 1e-3,
                      "WEIGHT_DECAY": 1e-4}


def test_b2_with_gate_at_one_reproduces_b1(problem):
    # Pipeline, Estágio 3, critério 1: a ponderação por um vetor de uns é o
    # B1. Feito pela rede, com o mesmo treino do braço.
    X, y, folds = problem
    fit_idx, stop_idx = folds[0]
    Xf = torch.as_tensor(X[fit_idx], dtype=torch.float32)
    yf = torch.as_tensor(y[fit_idx], dtype=torch.float32)
    outs = []
    for multiplier in (None, torch.ones(X.shape[1])):
        torch.manual_seed(5)
        net = GateNet(X.shape[1])
        if multiplier is None:
            net.gated = False
        else:
            net.multiplier = multiplier
        net.gates.requires_grad_(False)
        rest = [p for n, p in net.named_parameters() if n != "gates"]
        opt = torch.optim.Adam(rest, lr=0.01, weight_decay=1e-4)
        for _ in range(20):
            net.train()
            loss = torch.nn.functional.mse_loss(net(Xf).squeeze(1), yf)
            opt.zero_grad()
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            outs.append(net(Xf))
    assert torch.equal(outs[0], outs[1])


def test_c_equal_one_recovers_b4_clean_and_b2(problem):
    for scaled, plain in ((gate_prior_scaled(c=1.0), gate_prior()),
                          (mlp_weighted_scaled(c=1.0), mlp_weighted())):
        a, b = fit(scaled, problem), fit(plain, problem)
        np.testing.assert_array_equal(a.predict(problem[0]), b.predict(problem[0]))
        assert a.hyperparams.keys() == b.hyperparams.keys()
        for k in a.hyperparams:  # nan == nan é falso; a porta congelada dá nan
            va, vb = a.hyperparams[k], b.hyperparams[k]
            assert va == vb or (va != va and vb != vb), k


# --- cada braço faz o que diz ------------------------------------------------

def test_frozen_gates_do_not_move(problem):
    for arm in (mlp_weighted(), mlp_weighted_scaled(c=0.3)):
        h = fit(arm, problem).hyperparams
        assert h["gate_max_disp"] == 0.0
        assert h["trainable_gate"] is False


def test_trainable_gates_move(problem):
    for arm in (gate_uniform(), gate_prior(), gate_prior_faithful(), gate_prior_scaled(c=0.3)):
        assert fit(arm, problem).hyperparams["gate_max_disp"] > 0


def test_initial_gates(problem):
    X, y, folds = problem
    fit_idx = folds[0][0]
    s = anova_prior((X[fit_idx] - X[fit_idx].mean(0)) / X[fit_idx].std(0), y[fit_idx])
    np.testing.assert_array_equal(fit(gate_uniform(), problem)._theta0, np.zeros(X.shape[1]))
    np.testing.assert_allclose(fit(gate_prior(), problem)._theta0, prior_logits(s))
    np.testing.assert_allclose(fit(gate_prior_scaled(c=0.3), problem)._theta0,
                               0.3 * prior_logits(s))
    assert fit(mlp_full(), problem).band_scores is None


def test_kl_reference(problem):
    p = problem[0].shape[1]
    uniform = fit(gate_uniform(), problem)._net.prior_probs.numpy()
    np.testing.assert_allclose(uniform, np.full(p, 1.0 / p), rtol=1e-6)
    prior = fit(gate_prior(), problem)
    np.testing.assert_allclose(prior._net.prior_probs.numpy(),
                               np.clip(prior._prior, 1e-7, 1 - 1e-7), rtol=1e-6)


def test_gate_weight_decay_only_in_the_faithful_b4(problem):
    assert fit(gate_prior_faithful(), problem).hyperparams["gate_weight_decay"] is True
    for arm in (gate_prior(), gate_uniform(), gate_prior_scaled(c=0.3)):
        assert fit(arm, problem).hyperparams["gate_weight_decay"] is False
    # e muda o resultado: o L2 na porta não é inócuo
    a = fit(gate_prior_faithful(), problem).hyperparams["gate_max_disp"]
    b = fit(gate_prior(), problem).hyperparams["gate_max_disp"]
    assert a != b


# --- o prior não vê a fold de parada (pergunta 7) -----------------------------

def test_prior_ignores_the_stopping_fold(problem):
    X, y, folds = problem
    stop_idx = folds[0][1]
    y_stop_changed = y.copy()
    y_stop_changed[stop_idx] += 50.0
    a, b = fit(gate_prior(), problem), fit(gate_prior(), problem, y=y_stop_changed)
    np.testing.assert_array_equal(a._prior, b._prior)
    np.testing.assert_array_equal(a._theta0, b._theta0)


def test_prior_does_see_the_fitting_rows(problem):
    # O controle do teste acima: a mesma perturbação nas linhas de ajuste
    # muda o prior, então o teste acima não passa por acaso.
    X, y, folds = problem
    fit_idx = folds[0][0]
    y_changed = y.copy()
    y_changed[fit_idx[:10]] += 50.0
    a, b = fit(gate_prior(), problem), fit(gate_prior(), problem, y=y_changed)
    assert not np.array_equal(a._prior, b._prior)


# --- parada, sementes, orçamento ----------------------------------------------

def test_best_epoch_is_kept(problem):
    h = fit(gate_prior(), problem).hyperparams
    assert 1 <= h["best_epoch"] <= h["epochs_run"] <= 200
    assert h["epochs_run"] == 200 or h["epochs_run"] - h["best_epoch"] == 30


def test_rmse_cv_is_the_stopping_rmse_at_the_best_epoch(problem):
    X, y, folds = problem
    stop_idx = folds[0][1]
    f = fit(gate_prior(), problem)
    rmse = float(np.sqrt(np.mean((f.predict(X[stop_idx]) - y[stop_idx]) ** 2)))
    assert f.rmse_cv == pytest.approx(rmse, rel=1e-5)


def test_same_seed_same_model_other_seed_other_model(problem):
    X = problem[0]
    a, b, c = fit(gate_prior(), problem, 0), fit(gate_prior(), problem, 0), fit(gate_prior(), problem, 1)
    np.testing.assert_array_equal(a.predict(X), b.predict(X))
    assert not np.array_equal(a.predict(X), c.predict(X))


def test_one_fit_per_training_and_one_thread_restored(problem):
    X, y, folds = problem
    before = torch.get_num_threads()
    budget = Budget()
    gate_prior().fit(X, y, folds, np.random.default_rng(0), budget)
    assert budget.n_fits == 1
    assert torch.get_num_threads() == before


def test_names_are_distinct():
    names = [a.name for a in all_arms()]
    assert len(set(names)) == len(names)
    assert gate_prior_scaled(c=0.054).name == "gate_prior(c=0.054)"


def test_gate_metrics_are_reported(problem):
    h = fit(gate_prior(), problem).hyperparams
    for k in ("gate_gap", "gate_max_disp", "gate_median_disp", "gate_frac_shrunk",
              "gate_corr_disp_neg_theta0", "gate_top_band_initial", "gate_top_band_final",
              "gate_top10_kept"):
        assert k in h
    assert h["gate_gap"] > 0
    assert 0 <= h["gate_top10_kept"] <= 10
    # porta congelada: o top-10 fica inteiro
    assert fit(mlp_weighted(), problem).hyperparams["gate_top10_kept"] == 10


# --- receita de treino (ADR 017, item 7) --------------------------------------------

def test_default_recipe_reproduces_the_recorded_sweep():
    # Regressão: com a receita padrão, o braço dá os mesmos números gravados
    # na varredura de c de 12/11 (results/varredura_c.csv), antes de a
    # receita existir.
    import csv
    from tcc.data import load
    from tcc.protocol import evaluate
    with open(ROOT / "results" / "varredura_c.csv", encoding="utf-8") as f:
        rows = {(r["braco"], r["c"]): r for r in csv.DictReader(f)
                if r["conjunto"] == "tecator" and r["seed_split"] == "0"}
    ds = load("tecator")
    for (braco, c), arm in ((("B5", "1"), gate_prior_scaled(c=1.0)),
                            (("B3", ""), gate_uniform()),
                            (("B2'", "0.3"), mlp_weighted_scaled(c=0.3))):
        r = evaluate(arm, ds, seed_split=0, seed_algo=0)
        row = rows[(braco, c)]
        assert f"{r.r2:.6f}" == row["r2"]
        assert f"{r.hyperparams['gate_max_disp']:.6f}" == row["d"]
        assert str(r.hyperparams["best_epoch"]) == row["melhor_epoca"]


def test_explicit_article_recipe_is_the_default(problem):
    from tcc.arms.gate import ARTICLE
    a, b = gate_prior(), gate_prior(recipe=ARTICLE)
    assert a.name == b.name == "gate_prior"
    np.testing.assert_array_equal(fit(a, problem).predict(problem[0]),
                                  fit(b, problem).predict(problem[0]))
    h = fit(a, problem).hyperparams
    assert (h["recipe"], h["lr"], h["max_epochs"], h["patience"], h["batch_size"]) == \
        ("artigo", 0.01, 200, 30, None)


def test_another_recipe_is_named_and_followed(problem):
    from tcc.arms.gate import TrainRecipe
    rec = TrainRecipe(name="curta", max_epochs=7, patience=1000)
    arm = gate_prior(recipe=rec)
    assert arm.name == "gate_prior[curta]"
    h = fit(arm, problem).hyperparams
    assert h["epochs_run"] == 7 and h["recipe"] == "curta"
    assert mlp_full(recipe=rec).name == "mlp_full[curta]"
    assert gate_prior_scaled(c=0.3, recipe=rec).name == "gate_prior(c=0.3)[curta]"


def test_minibatches_are_deterministic_and_differ_from_one_batch(problem):
    from tcc.arms.gate import TrainRecipe
    X = problem[0]
    rec = TrainRecipe(name="lotes", batch_size=16, max_epochs=20, patience=1000)
    a, b = fit(gate_prior(recipe=rec), problem), fit(gate_prior(recipe=rec), problem)
    np.testing.assert_array_equal(a.predict(X), b.predict(X))
    one = fit(gate_prior(recipe=TrainRecipe(name="um", max_epochs=20, patience=1000)), problem)
    assert not np.array_equal(a.predict(X), one.predict(X))
    assert a.hyperparams["batch_size"] == 16
    # 64 linhas de ajuste em lotes de 16: 4 passos por época; lote único, 1
    assert a.hyperparams["n_steps"] == 4 * a.hyperparams["epochs_run"]
    assert one.hyperparams["n_steps"] == one.hyperparams["epochs_run"]


def test_a_last_batch_of_one_row_is_merged(problem):
    # 64 linhas de ajuste em lotes de 21: sobraria um lote de 1 linha, que o
    # BatchNorm recusa; ele vai junto com o anterior.
    from tcc.arms.gate import TrainRecipe
    rec = TrainRecipe(name="sobra", batch_size=21, max_epochs=3, patience=1000)
    assert len(problem[2][0][0]) == 64
    assert fit(gate_prior(recipe=rec), problem).hyperparams["epochs_run"] == 3


@pytest.mark.parametrize("kw", [{"batch_size": 1}, {"lr": 0.0}, {"max_epochs": 0},
                                {"patience": 0}])
def test_invalid_recipes_are_rejected(kw):
    from tcc.arms.gate import TrainRecipe
    with pytest.raises(ValueError):
        TrainRecipe(name="ruim", **kw)


def test_recipe_patience_and_lr_are_used(problem):
    from tcc.arms.gate import TrainRecipe
    impaciente = fit(gate_prior(recipe=TrainRecipe(name="p1", patience=1)), problem).hyperparams
    assert impaciente["epochs_run"] - impaciente["best_epoch"] == 1 or impaciente["epochs_run"] == 200
    assert impaciente["epochs_run"] < fit(gate_prior(), problem).hyperparams["epochs_run"]
    X = problem[0]
    devagar = fit(gate_prior(recipe=TrainRecipe(name="lr", lr=0.001, max_epochs=20, patience=1000)), problem)
    rapido = fit(gate_prior(recipe=TrainRecipe(name="lr2", max_epochs=20, patience=1000)), problem)
    assert not np.array_equal(devagar.predict(X), rapido.predict(X))
