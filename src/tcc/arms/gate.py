"""Braços neurais: B1, B2, B2'(c), B3, B4-fiel, B4-limpo e B5(c) (ADR 017).

Todos são a mesma rede, uma reimplementação do `BandSelectNetLight` do
artigo (pgsg_0): porta espectral (softmax dos logits / τ, τ = 5) que
multiplica o espectro, depois `fc1` (16) → BatchNorm → ReLU → dropout 0,5 →
`fc2`. A equivalência numérica com o original é conferida em
`tests/test_gate.py` contra a cópia local do código do artigo, que fica fora
do git; a reimplementação existe porque a cópia não tem licença (ADR 017,
Em aberto, item 1).

Os braços diferem só na porta (ADR 017, tabela "Os braços"):

    braço     porta inicial         gradiente  L2 na porta  referência do KL
    B1        sem porta             -          -            sem KL
    B2        logit(clip(s))        não        -            clip(s), inerte
    B2'(c)    c * logit(clip(s))    não        -            clip(s), inerte
    B3        0 (uniforme exato)    sim        não          1/p
    B4-fiel   logit(clip(s))        sim        sim          clip(s)
    B4-limpo  logit(clip(s))        sim        não          clip(s)
    B5(c)     c * logit(clip(s))    sim        não          clip(s)

com `s` o prior ANOVA (`f_regression`, normalizado por mínimo e máximo).

Regras de comparabilidade (pipeline, Estágio 3):
- a rede é sempre construída do mesmo jeito, com a mesma sequência de
  números aleatórios, e a porta de cada braço é escrita depois; assim
  `fc1`, BatchNorm e `fc2` começam byte a byte iguais em todos os braços;
- mesmo otimizador, mesmo L2 no MLP e mesma regra de parada.

Treino (ADR 017): Z-score de X e de y nas linhas de ajuste; a validação da
primeira fold de `cv_folds` é o conjunto de parada e não ajusta a rede nem
entra no prior; lote único, Adam, lr 0,01, até 200 épocas, paciência 30,
L2 1e-4 no MLP, KL 1e-3; o modelo final é o da melhor época no conjunto de
parada. Uma thread no torch, porque o `wall_time` é resultado.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.feature_selection import f_regression

from tcc.arms.base import Budget, CVFolds

TEMPERATURE = 5.0
HIDDEN = 16
DROPOUT = 0.5
LR = 0.01
MAX_EPOCHS = 200
PATIENCE = 30
KL_WEIGHT = 1e-3
WEIGHT_DECAY = 1e-4
CLIP = 1e-7


class GateNet(nn.Module):
    """Reimplementação do `BandSelectNetLight` do artigo.

    A ordem de criação dos parâmetros é a do original: primeiro os logits da
    porta, sorteados como `randn(p) * 0,01` (o caso "sem prior" do
    original), depois `fc1`, `fc2` e o BatchNorm. Construir sempre assim faz
    a sequência de números aleatórios até a `fc1` ser a mesma em todo braço;
    a porta de cada braço é escrita por cima com `set_gate`.

    `gated=False` é o B1: o espectro entra na `fc1` sem ponderação.
    `multiplier`, se dado, substitui a porta por um vetor fixo; existe para
    o teste de sanidade do pipeline (B2 com a porta em 1,0 igual ao B1).
    """

    def __init__(self, n_bands: int, *, draw_gate: bool = True):
        super().__init__()
        self.n_bands = n_bands
        self.temperature = TEMPERATURE
        # `draw_gate=False` imita o original construído **com** prior, que não
        # sorteia a porta; só a reprodução do artigo usa (scripts/
        # reproduzir_b4_artigo.py). Os braços sempre sorteiam (ADR 017).
        init = torch.randn(n_bands) * 0.01 if draw_gate else torch.zeros(n_bands)
        self.gates = nn.Parameter(init)
        self.register_buffer("prior_probs", torch.ones(n_bands) / n_bands)
        self.fc1 = nn.Linear(n_bands, HIDDEN)
        self.dropout = nn.Dropout(DROPOUT)
        self.fc2 = nn.Linear(HIDDEN, 1)
        self.bn = nn.BatchNorm1d(HIDDEN)
        self.gated = True
        self.multiplier: torch.Tensor | None = None

    def set_gate(self, logits: np.ndarray, prior_probs: np.ndarray) -> None:
        with torch.no_grad():
            self.gates.copy_(torch.as_tensor(logits, dtype=torch.float32))
            self.prior_probs.copy_(torch.as_tensor(prior_probs, dtype=torch.float32))

    def gate_probs(self) -> torch.Tensor:
        return F.softmax(self.gates / self.temperature, dim=0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.multiplier is not None:
            x = x * self.multiplier.unsqueeze(0)
        elif self.gated:
            x = x * self.gate_probs().unsqueeze(0)
        x = F.relu(self.bn(self.fc1(x)))
        x = self.dropout(x)
        return self.fc2(x)

    def kl(self) -> torch.Tensor:
        g = self.gate_probs()
        return (g * (torch.log(g + 1e-10) - torch.log(self.prior_probs + 1e-10))).sum()


def anova_prior(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Prior ANOVA do artigo: F de `f_regression`, normalizado para [0, 1]."""
    f, _ = f_regression(X, np.ravel(y))
    f = np.nan_to_num(f, nan=0.0)
    span = f.max() - f.min()
    if span == 0:
        return np.zeros_like(f)
    return (f - f.min()) / span


def prior_logits(s: np.ndarray) -> np.ndarray:
    s = np.clip(s, CLIP, 1 - CLIP)
    return np.log(s / (1 - s))


@dataclass(frozen=True)
class GateConfig:
    """O que distingue os braços. Todo o resto é igual entre eles."""

    gated: bool  # False só no B1
    init: str  # "prior" ou "uniform"
    c: float  # fator dos logits iniciais (B2' e B5); 1 nos outros
    trainable: bool  # gradiente na porta
    gate_weight_decay: bool  # L2 na porta (só o B4-fiel)
    kl_ref: str  # "prior", "uniform" ou "none"


@dataclass(frozen=True)
class _FittedGateArm:
    _net: GateNet
    _x_mean: np.ndarray
    _x_std: np.ndarray
    _y_mean: float
    _y_std: float
    _hyperparams: dict
    _rmse_cv: float
    _band_scores: np.ndarray | None
    _theta0: np.ndarray | None
    _prior: np.ndarray | None

    def predict(self, X: np.ndarray) -> np.ndarray:
        Xz = (X - self._x_mean) / self._x_std
        self._net.eval()
        with torch.no_grad():
            out = self._net(torch.as_tensor(Xz, dtype=torch.float32)).numpy().ravel()
        return out * self._y_std + self._y_mean

    @property
    def band_scores(self) -> np.ndarray | None:
        return self._band_scores

    @property
    def hyperparams(self) -> dict:
        return self._hyperparams

    @property
    def rmse_cv(self) -> float:
        return self._rmse_cv

    @property
    def cv_selections(self) -> list[set[int]] | None:
        # A rede não seleciona bandas por fold: há um só treino, com uma
        # fold de parada. O vazamento que importa aqui, o do prior, é
        # conferido à parte em tests/test_gate.py.
        return None


def _zscore(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = A.mean(axis=0)
    std = A.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    return mean, std


def _gate_metrics(theta0: np.ndarray, theta1: np.ndarray) -> dict:
    """Medidas da H8 e do `c` do TOST (PROTOCOLO; ADR 017)."""
    d = theta1 - theta0
    top2 = np.sort(theta0)[::-1][:2]
    moved = np.abs(d)
    if np.std(d) > 0 and np.std(theta0) > 0:
        corr = float(np.corrcoef(d, -theta0)[0, 1])
    else:
        corr = float("nan")
    return {
        "gate_gap": float(top2[0] - top2[1]),  # g: 1º menos 2º logit inicial
        "gate_max_disp": float(moved.max()),  # d: maior |θ_final − θ_inicial|
        "gate_median_disp": float(np.median(moved)),
        "gate_frac_shrunk": float(np.mean(np.abs(theta1) < np.abs(theta0))),
        "gate_corr_disp_neg_theta0": corr,
        "gate_top_band_initial": int(np.argmax(theta0)),
        "gate_top_band_final": int(np.argmax(theta1)),
        # Quantas das 10 bandas iniciais de maior logit seguem no top-10 final
        # (a medida "top10 kept" da varredura da orientação, 12/11). Com a
        # porta uniforme (c = 0) o top-10 inicial não é definido.
        "gate_top10_kept": int(len(set(np.argsort(theta0)[-10:])
                                   & set(np.argsort(theta1)[-10:]))),
    }


class GateArm:
    """Um braço neural. Use as fábricas abaixo, não o construtor."""

    def __init__(self, *, name: str, config: GateConfig):
        self.name = name
        self.config = config

    def initial_net(
        self, Xz_fit: np.ndarray, y_fit: np.ndarray, seed: int
    ) -> tuple[GateNet, np.ndarray | None, np.ndarray | None]:
        """A rede antes do treino: construída sempre igual, porta por cima.

        O prior vem só de `Xz_fit` e `y_fit`, as linhas que ajustam a rede
        (pergunta 7); a fold de parada nunca chega aqui.
        """
        cfg = self.config
        p = Xz_fit.shape[1]
        torch.manual_seed(seed)
        net = GateNet(p)
        prior = theta0 = None
        if cfg.gated:
            prior = anova_prior(Xz_fit, y_fit)
            theta0 = cfg.c * prior_logits(prior) if cfg.init == "prior" else np.zeros(p)
            ref = (np.clip(prior, CLIP, 1 - CLIP) if cfg.kl_ref == "prior"
                   else np.full(p, 1.0 / p))
            net.set_gate(theta0, ref)
            # O θ inicial é o que a rede guarda (float32), para o
            # deslocamento de uma porta congelada dar exatamente zero.
            theta0 = net.gates.detach().numpy().astype(float).copy()
        else:
            net.gated = False
        return net, theta0, prior

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedGateArm:
        cfg = self.config
        fit_idx, stop_idx = cv_folds[0]
        X_fit, y_fit = X_train[fit_idx], np.ravel(y_train)[fit_idx]
        X_stop, y_stop = X_train[stop_idx], np.ravel(y_train)[stop_idx]

        x_mean, x_std = _zscore(X_fit)
        y_mean, y_std = float(y_fit.mean()), float(y_fit.std()) or 1.0
        Xf = torch.as_tensor((X_fit - x_mean) / x_std, dtype=torch.float32)
        yf = torch.as_tensor((y_fit - y_mean) / y_std, dtype=torch.float32)
        Xs = torch.as_tensor((X_stop - x_mean) / x_std, dtype=torch.float32)
        ys = torch.as_tensor((y_stop - y_mean) / y_std, dtype=torch.float32)

        p = X_train.shape[1]
        seed = int(rng_algo.integers(2**31 - 1))
        threads = torch.get_num_threads()
        torch.set_num_threads(1)
        try:
            net, theta0, prior = self.initial_net((X_fit - x_mean) / x_std, y_fit, seed)

            rest = [prm for n, prm in net.named_parameters() if n != "gates"]
            groups = [{"params": rest, "weight_decay": WEIGHT_DECAY}]
            if cfg.gated and cfg.trainable:
                groups.append({"params": [net.gates],
                               "weight_decay": WEIGHT_DECAY if cfg.gate_weight_decay else 0.0})
            else:
                net.gates.requires_grad_(False)
            opt = torch.optim.Adam(groups, lr=LR)
            use_kl = cfg.gated and cfg.kl_ref != "none"

            best, best_state, best_epoch, bad, epochs = float("inf"), None, 0, 0, 0
            for epoch in range(MAX_EPOCHS):
                net.train()
                loss = F.mse_loss(net(Xf).squeeze(1), yf)
                if use_kl:
                    loss = loss + KL_WEIGHT * net.kl()
                opt.zero_grad()
                loss.backward()
                opt.step()
                epochs = epoch + 1
                net.eval()
                with torch.no_grad():
                    r = torch.sqrt(F.mse_loss(net(Xs).squeeze(1), ys)).item()
                if r < best:
                    best, best_state, best_epoch, bad = r, copy.deepcopy(net.state_dict()), epochs, 0
                else:
                    bad += 1
                    if bad >= PATIENCE:
                        break
            if best_state is None:
                raise RuntimeError("o RMSE no conjunto de parada nunca foi finito")
            net.load_state_dict(best_state)
            net.eval()
        finally:
            torch.set_num_threads(threads)
        budget.increment()

        hyper = {
            "n_bands": p,
            "gated": cfg.gated,
            "init": cfg.init if cfg.gated else None,
            "c": cfg.c if cfg.gated else None,
            "trainable_gate": cfg.gated and cfg.trainable,
            "gate_weight_decay": cfg.gated and cfg.trainable and cfg.gate_weight_decay,
            "kl_ref": cfg.kl_ref if cfg.gated else "none",
            "best_epoch": best_epoch,
            "epochs_run": epochs,
            "torch_seed": seed,
        }
        band_scores = None
        if cfg.gated:
            theta1 = net.gates.detach().numpy().astype(float).copy()
            hyper.update(_gate_metrics(theta0, theta1))
            band_scores = net.gate_probs().detach().numpy().astype(float)

        return _FittedGateArm(
            _net=net, _x_mean=x_mean, _x_std=x_std, _y_mean=y_mean, _y_std=y_std,
            _hyperparams=hyper, _rmse_cv=best * y_std, _band_scores=band_scores,
            _theta0=theta0, _prior=prior,
        )


def _fmt(c: float) -> str:
    return f"{c:g}"


def mlp_full() -> GateArm:
    """B1: o MLP sem porta."""
    return GateArm(name="mlp_full", config=GateConfig(
        gated=False, init="prior", c=1.0, trainable=False,
        gate_weight_decay=False, kl_ref="none"))


def mlp_weighted() -> GateArm:
    """B2: a porta inicial do PGSG, congelada."""
    return GateArm(name="mlp_weighted", config=GateConfig(
        gated=True, init="prior", c=1.0, trainable=False,
        gate_weight_decay=False, kl_ref="prior"))


def mlp_weighted_scaled(*, c: float) -> GateArm:
    """B2'(c): a porta do B5(c), congelada."""
    return GateArm(name=f"mlp_weighted(c={_fmt(c)})", config=GateConfig(
        gated=True, init="prior", c=c, trainable=False,
        gate_weight_decay=False, kl_ref="prior"))


def gate_uniform() -> GateArm:
    """B3: porta treinável, começando no uniforme exato, KL ancorado no uniforme."""
    return GateArm(name="gate_uniform", config=GateConfig(
        gated=True, init="uniform", c=1.0, trainable=True,
        gate_weight_decay=False, kl_ref="uniform"))


def gate_prior_faithful() -> GateArm:
    """B4-fiel: como o B4-limpo, mas com L2 também na porta, como no artigo."""
    return GateArm(name="gate_prior_fiel", config=GateConfig(
        gated=True, init="prior", c=1.0, trainable=True,
        gate_weight_decay=True, kl_ref="prior"))


def gate_prior() -> GateArm:
    """B4-limpo: a porta inicial do PGSG, treinável, isenta de L2."""
    return GateArm(name="gate_prior", config=GateConfig(
        gated=True, init="prior", c=1.0, trainable=True,
        gate_weight_decay=False, kl_ref="prior"))


def gate_prior_scaled(*, c: float) -> GateArm:
    """B5(c): logits iniciais escalados por c, porta treinável e isenta."""
    return GateArm(name=f"gate_prior(c={_fmt(c)})", config=GateConfig(
        gated=True, init="prior", c=c, trainable=True,
        gate_weight_decay=False, kl_ref="prior"))
