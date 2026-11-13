"""Decomposição pareada e equivalência (Estágio 7 do pipeline; ADR 020).

**Regra central:** cada termo é calculado pareado, por (conjunto,
`seed_split`), e só depois agregado. Calcular a partir de médias marginais
quebra o pareamento e faz a soma deixar de reconstituir B4 − A1.

    Δ_não-lin[d,s]     = m(B1,d,s) − m(A1,d,s)
    Δ_ponderação[d,s]  = m(B2,d,s) − m(B1,d,s)
    Δ_aprendizado[d,s] = m(B4,d,s) − m(B2,d,s)
    Δ_prior[d,s]       = m(B4,d,s) − m(B3,d,s)   (contraste complementar)

com `m` a métrica (R² por padrão). Os três primeiros somam B4 − A1 em cada
partição; o Δ_prior envolve o B4 como o Δ_aprendizado, não é ortogonal a
ele e não entra na soma.

O B4 aqui é o B4-limpo (`gate_prior`), como o PROTOCOLO manda onde diz só
"B4"; o B4-fiel serve à comparação com o artigo.

**Equivalência (TOST):** dois testes t unilaterais sobre as diferenças
pareadas contra ±δ. "Equivalente" só se os dois rejeitarem, o que é o
mesmo que o intervalo de confiança de 1 − 2α ficar dentro de (−δ, δ). O
intervalo vai sempre junto.

**Comparação global:** Friedman entre braços sobre os blocos, com pós-teste
pareado (Wilcoxon) e correção de Holm.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from itertools import combinations

import numpy as np
from scipy import stats

# Os braços da decomposição, pelo nome que dão a si mesmos.
ARMS = {"A1": "pls_full", "B1": "mlp_full", "B2": "mlp_weighted",
        "B3": "gate_uniform", "B4": "gate_prior"}
TERMS = {
    "nao_lin": ("B1", "A1"),
    "ponderacao": ("B2", "B1"),
    "aprendizado": ("B4", "B2"),
    "prior": ("B4", "B3"),
}
ADDITIVE = ("nao_lin", "ponderacao", "aprendizado")


def _table(results: Iterable, metric: str) -> dict:
    """{(conjunto, seed_split): {braço: valor}}, recusando repetição."""
    t: dict = defaultdict(dict)
    for r in results:
        key = (r.dataset_name, r.seed_split)
        if r.arm_name in t[key]:
            # Mais de um seed_algo na mesma célula: como reduzir é a pergunta
            # 8 do protocolo, ainda aberta. Não se decide em silêncio aqui.
            raise ValueError(f"{r.arm_name} repetido em {key}: reduza seed_algo antes")
        t[key][r.arm_name] = float(getattr(r, metric))
    return t


def paired_differences(results: Iterable, arm_a: str, arm_b: str,
                       metric: str = "r2") -> dict:
    """{(conjunto, seed_split): m(a) − m(b)}, só onde os dois existem."""
    t = _table(results, metric)
    return {k: v[arm_a] - v[arm_b] for k, v in t.items() if arm_a in v and arm_b in v}


def decompose(results: Iterable, metric: str = "r2", arms: dict = ARMS) -> dict:
    """Os quatro termos por (conjunto, seed_split), mais B4 − A1.

    Só entram as partições com os cinco braços: uma partição incompleta sai
    de todos os termos, nunca só dos que faltam, para todos os termos
    ficarem sobre as mesmas partições. As que saíram vão em "excluidas".
    """
    t = _table(results, metric)
    names = {role: arms[role] for role in ("A1", "B1", "B2", "B3", "B4")}
    out: dict = {term: {} for term in TERMS}
    out["total"] = {}
    out["excluidas"] = []
    for key, v in sorted(t.items()):
        if not all(n in v for n in names.values()):
            out["excluidas"].append(key)
            continue
        m = {role: v[n] for role, n in names.items()}
        for term, (a, b) in TERMS.items():
            out[term][key] = m[a] - m[b]
        out["total"][key] = m["B4"] - m["A1"]
    return out


def additive_identity_gap(decomposition: dict) -> float:
    """Maior |Δ_não-lin + Δ_ponderação + Δ_aprendizado − (B4 − A1)| entre as
    partições. Zero, a menos de arredondamento, se o pareamento está certo."""
    gaps = [abs(sum(decomposition[t][k] for t in ADDITIVE) - total)
            for k, total in decomposition["total"].items()]
    return max(gaps) if gaps else 0.0


def tost(differences: Sequence[float], delta: float, alpha: float = 0.05) -> dict:
    """TOST pareado sobre as diferenças: H0 é |média| ≥ δ.

    Devolve a média, o intervalo de 1 − 2α, os dois p unilaterais, o p do
    TOST (o maior dos dois) e se é equivalente (p < α). O intervalo vai
    sempre junto: equivalente se e só se ele cabe em (−δ, δ).
    """
    d = np.asarray(differences, dtype=float)
    if d.size < 2:
        raise ValueError("são precisas pelo menos duas diferenças")
    if not delta > 0:
        raise ValueError("δ deve ser positivo")
    n = d.size
    mean = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(n))
    df = n - 1
    if se == 0:
        p_low = 0.0 if mean > -delta else 1.0
        p_high = 0.0 if mean < delta else 1.0
        half = 0.0
    else:
        p_low = float(stats.t.sf((mean + delta) / se, df))    # H0: média ≤ −δ
        p_high = float(stats.t.cdf((mean - delta) / se, df))  # H0: média ≥ +δ
        half = float(stats.t.ppf(1 - alpha, df) * se)
    p = max(p_low, p_high)
    return {"n": n, "delta": delta, "alpha": alpha, "mean": mean,
            "ci_low": mean - half, "ci_high": mean + half,
            "p_low": p_low, "p_high": p_high, "p": p, "equivalent": p < alpha}


def holm(pvalues: Sequence[float]) -> np.ndarray:
    """p ajustados de Holm (step-down), na ordem de entrada."""
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p, kind="stable")
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def friedman(table: np.ndarray) -> dict:
    """Friedman sobre uma tabela blocos × braços (um valor por célula)."""
    table = np.asarray(table, dtype=float)
    if table.ndim != 2 or table.shape[1] < 3 or table.shape[0] < 2:
        raise ValueError("tabela blocos × braços, com pelo menos 2 blocos e 3 braços")
    stat, p = stats.friedmanchisquare(*table.T)
    return {"statistic": float(stat), "p": float(p), "blocks": table.shape[0],
            "arms": table.shape[1]}


def posthoc_wilcoxon_holm(table: np.ndarray, names: Sequence[str]) -> dict:
    """Wilcoxon pareado entre cada par de braços, com Holm sobre todos os pares."""
    table = np.asarray(table, dtype=float)
    pairs = list(combinations(range(table.shape[1]), 2))
    raw = []
    for i, j in pairs:
        d = table[:, i] - table[:, j]
        raw.append(1.0 if np.all(d == 0) else float(stats.wilcoxon(d).pvalue))
    adj = holm(raw)
    return {(names[i], names[j]): {"p": raw[n], "p_holm": float(adj[n])}
            for n, (i, j) in enumerate(pairs)}
