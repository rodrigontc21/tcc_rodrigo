"""A configuração da grade final (Estágio 5; ADR 021).

Junta num lugar só o que a grade final roda: os quatro conjuntos, os seis
braços clássicos e os 23 de rede por conjunto (B1, B2, B3, os dois B4 e as
nove posições da grade de `c` no B2' e no B5), as partições e o eixo
`seed_algo`. O que a orientação ainda não decidiu fica em `A_DECIDIR`, e o
modo "final" se recusa a montar a grade enquanto houver algum.

O modo "ensaio" monta a mesma grade na partição piloto 0, para pegar erro
de configuração antes dos dias de máquina da final. Ele nunca toca as
partições da grade final (≥ 100), e a final nunca usa as do piloto (0–29).
"""

from __future__ import annotations

from tcc.arms.gate import ARTICLE, TrainRecipe
from tcc.grid import ArmSpec, GridSpec

A_DECIDIR = None

DATASETS = ("tecator", "gasoline", "mango", "bioprocess")

# PROTOCOLO, "A grade de `c`" (declarada em 12/11/2026): a grade fixa da
# orientação, mais o `c_TOST` de cada conjunto. O do Mango está suspenso
# até a receita de treino dele ser decidida (ADR 017, item 7).
C_GRID = (1.0, 0.5, 0.3, 0.17, 0.10, 0.054, 0.026, 0.0)
C_TOST = {"tecator": 0.0306, "gasoline": 0.0289, "mango": A_DECIDIR, "bioprocess": 0.1140}

# A receita de treino das redes por conjunto. A do artigo onde ela ajusta;
# a do Mango espera a orientação (ADR 017, item 7).
RECIPE = {"tecator": ARTICLE, "gasoline": ARTICLE, "mango": A_DECIDIR, "bioprocess": ARTICLE}

# Partições e sementes: a grade final usa `seed_split` ≥ 100 (as 0–29 são
# piloto). Quantas partições, e quantas sementes no eixo do algoritmo e em
# qual partição, ainda não foram decididos.
SEED_SPLITS = A_DECIDIR
SEED_ALGO = 0
ALGO_AXIS_SPLIT = A_DECIDIR
ALGO_AXIS_SEEDS = A_DECIDIR
FIRST_FINAL_SPLIT = 100

# Ensaio: a partição piloto 0, sem o bioprocess (uma partição dele leva ~3 h;
# as 30 partições piloto dele já testam esses braços). No Mango, o `c_TOST`
# medido sob a receita do artigo e uma receita de nome "ensaio", com os
# mesmos valores da do artigo: exercita o caminho do nome com receita sem
# mudar nenhum número.
TRIAL = {
    "datasets": ("tecator", "gasoline", "mango"),
    "seed_splits": (0,),
    "algo_axis_split": 0,
    "algo_axis_seeds": (0, 1, 2),
    "c_tost": {"mango": 0.0417},
    "recipe": {"mango": TrainRecipe(name="ensaio")},
}

CLASSICAL = (
    ArmSpec(name="pls_full", factory="tcc.arms.pls:PLSArm", deterministic=True),
    ArmSpec(name="ipls", factory="tcc.arms.ipls:IPLSArm", deterministic=True),
    ArmSpec(name="vip_threshold", factory="tcc.arms.vip:VIPArm", deterministic=True),
    ArmSpec(name="ga_pls", factory="tcc.arms.gapls:GAPLSArm"),
    ArmSpec(name="cars", factory="tcc.arms.cars:CARSArm"),
    ArmSpec(name="cars_fiel", factory="tcc.arms.cars:CARSArm", kwargs=(("mode", "fiel"),)),
)

# Os papéis da decomposição (tcc.decomposition.ARMS) e o braço de cada um.
ROLES = {"A1": "pls_full", "B1": "mlp_full", "B2": "mlp_weighted", "B3": "gate_uniform",
         "B4": "gate_prior"}


def arm_name(base: str, recipe: TrainRecipe) -> str:
    """O nome que o braço de rede dá a si mesmo com essa receita."""
    return base if recipe == ARTICLE else f"{base}[{recipe.name}]"


def neural_arms(c_tost: float, recipe: TrainRecipe) -> list[ArmSpec]:
    """Os 23 braços de rede de um conjunto, todos com a mesma receita."""
    def spec(base, factory, **kw):
        if recipe != ARTICLE:
            kw["recipe"] = recipe
        return ArmSpec(name=arm_name(base, recipe), factory=f"tcc.arms.gate:{factory}",
                       kwargs=tuple(sorted(kw.items())))
    arms = [spec("mlp_full", "mlp_full"), spec("mlp_weighted", "mlp_weighted"),
            spec("gate_uniform", "gate_uniform"), spec("gate_prior_fiel", "gate_prior_faithful"),
            spec("gate_prior", "gate_prior")]
    for c in sorted(set(C_GRID) | {c_tost}, reverse=True):
        arms.append(spec(f"mlp_weighted(c={c:g})", "mlp_weighted_scaled", c=c))
        arms.append(spec(f"gate_prior(c={c:g})", "gate_prior_scaled", c=c))
    return arms


def undecided() -> list[str]:
    """O que ainda falta decidir para a grade final."""
    out = [f"c_TOST do {d}" for d, c in C_TOST.items() if c is A_DECIDIR]
    out += [f"receita de treino do {d}" for d, r in RECIPE.items() if r is A_DECIDIR]
    for nome, v in (("número de partições (SEED_SPLITS)", SEED_SPLITS),
                    ("partição do eixo seed_algo", ALGO_AXIS_SPLIT),
                    ("sementes do eixo seed_algo", ALGO_AXIS_SEEDS)):
        if v is A_DECIDIR:
            out.append(nome)
    return out


def roles(dataset: str, recipe: TrainRecipe) -> dict:
    """Os papéis da decomposição com os nomes dos braços daquele conjunto:
    as redes levam a receita no nome; o A1 (PLS) não tem receita."""
    return {r: (n if r == "A1" else arm_name(n, recipe)) for r, n in ROLES.items()}


def specs(mode: str) -> list[GridSpec]:
    """Uma `GridSpec` por conjunto (cada um tem o seu `c_TOST` e a sua receita)."""
    if mode == "final":
        falta = undecided()
        if falta:
            raise ValueError("a grade final ainda depende de: " + "; ".join(falta))
        datasets, seed_splits = DATASETS, list(SEED_SPLITS)
        axis_split, axis_seeds = ALGO_AXIS_SPLIT, list(ALGO_AXIS_SEEDS)
        c_tost, recipe = dict(C_TOST), dict(RECIPE)
        if min(seed_splits + [axis_split]) < FIRST_FINAL_SPLIT:
            raise ValueError(f"a grade final usa seed_split ≥ {FIRST_FINAL_SPLIT}")
    elif mode == "ensaio":
        datasets, seed_splits = TRIAL["datasets"], list(TRIAL["seed_splits"])
        axis_split, axis_seeds = TRIAL["algo_axis_split"], list(TRIAL["algo_axis_seeds"])
        c_tost = {**C_TOST, **TRIAL["c_tost"]}
        recipe = {**RECIPE, **TRIAL["recipe"]}
        if max(seed_splits + [axis_split]) >= FIRST_FINAL_SPLIT:
            raise ValueError("o ensaio não toca as partições da grade final")
    else:
        raise ValueError("modo deve ser 'final' ou 'ensaio'")
    return [GridSpec(datasets=[d], arms=list(CLASSICAL) + neural_arms(c_tost[d], recipe[d]),
                     seed_splits=seed_splits, seed_algo=SEED_ALGO,
                     algo_axis_split=axis_split, algo_axis_seeds=axis_seeds)
            for d in datasets]
