"""Janelas de atribuição espectroscópica (plausibilidade química; ADR 019).

As bandas de `docs/janelas_quimicas.md`, cada uma com a fonte lida. Só a
posição do pico vem da fonte; a **largura** da janela é escolha deste
trabalho, ainda em aberto, e por isso entra como parâmetro obrigatório, sem
valor padrão. O mesmo vale para quais papéis contam: o padrão é só o alvo.

Papéis:
- `alvo`: bandas do constituinte medido (gordura, octanagem pelos grupos de
  hidrocarboneto, matéria seca pelo C–H de açúcar, glicose);
- `agua`: O–H da água, interferente;
- `pigmento`: clorofila e carotenoides no Mango, que não são matéria seca;
- `outras`: outras bandas da glicose, fora da região de impressão digital.

Uso: `fraction_in_windows(selection, dataset.axis, windows("tecator", 25))`.
"""

from __future__ import annotations

from dataclasses import dataclass

ELMASRY = "ElMasry e Nakauchi (2016), Food Sci. Nutr. 4(2):269–283"
WORKMAN = "Workman e Weyer (2008), Practical Guide to Interpretive NIR Spectroscopy"
GOLIC = "Golic, Walsh e Lawson (2003), Appl. Spectrosc. 57(2):139–145, Tabela I"
WALSH = "Walsh et al. (2020), Postharvest Biol. Technol. 168:111246"
BOHACS = "Bohács, Ovádi e Salgó (1998), J. Near Infrared Spectrosc. 6:341–348"
DUMOUILLA = "Dumouilla e Dussap (2021), Bioengineered 12(1):4420–4431, Tabela 1"
DU = "Du et al. (2026), Communications Chemistry 9"


@dataclass(frozen=True)
class Band:
    position: float
    role: str
    assignment: str
    sources: tuple[str, ...]


BANDS: dict[str, tuple[Band, ...]] = {
    "tecator": (  # nm
        Band(position=930, role="alvo", assignment="gordura: C–H de CH2, 3ª harmônica",
         sources=(WORKMAN, GOLIC, ELMASRY)),
        Band(position=1040, role="alvo", assignment="gordura: combinação de estiramento e deformação do CH2",
         sources=(ELMASRY, WORKMAN)),
        Band(position=970, role="agua", assignment="água: O–H, 2ª harmônica",
         sources=(ELMASRY, GOLIC)),
    ),
    "gasoline": (  # nm
        Band(position=1144, role="alvo", assignment="C–H aromático, 2ª harmônica",
         sources=(BOHACS, WORKMAN)),
        Band(position=1190, role="alvo", assignment="C–H de metila, 2ª harmônica",
         sources=(BOHACS, WORKMAN)),
        Band(position=1395, role="alvo", assignment="combinação de C–H de metileno",
         sources=(BOHACS, WORKMAN)),
        Band(position=1674, role="alvo", assignment="C–H aromático, 1ª harmônica",
         sources=(BOHACS, WORKMAN)),
    ),
    "mango": (  # nm
        Band(position=910, role="alvo", assignment="C–H de açúcar (e amido), 3ª harmônica",
         sources=(GOLIC, WALSH)),
        Band(position=970, role="agua", assignment="O–H, 2ª harmônica",
         sources=(GOLIC,)),
        Band(position=840, role="agua", assignment="combinação de O–H",
         sources=(GOLIC,)),
        Band(position=738, role="agua", assignment="O–H, 3ª harmônica",
         sources=(GOLIC,)),
        Band(position=680, role="pigmento", assignment="clorofila",
         sources=(WALSH,)),
        Band(position=475, role="pigmento", assignment="beta-caroteno",
         sources=(WALSH,)),
        Band(position=435, role="pigmento", assignment="xantofilas",
         sources=(WALSH,)),
    ),
    "bioprocess": (  # cm⁻¹
        Band(position=1126, role="alvo", assignment="glicose: δ(COH) para Dumouilla; estiramento C–C do anel de piranose para Du et al.",
         sources=(DUMOUILLA, DU)),
        Band(position=1061, role="alvo", assignment="glicose: ώ(CH2)",
         sources=(DUMOUILLA, DU)),
        Band(position=1017, role="alvo", assignment="glicose: δ(COH)",
         sources=(DUMOUILLA, DU)),
        Band(position=910, role="alvo", assignment="glicose: δ(COH)",
         sources=(DUMOUILLA,)),
        Band(position=899, role="alvo", assignment="glicose: δ(COH)",
         sources=(DUMOUILLA,)),
        Band(position=1462, role="outras", assignment="glicose: δ(CH2)",
         sources=(DUMOUILLA,)),
        Band(position=1367, role="outras", assignment="glicose: δ(CH2)",
         sources=(DUMOUILLA,)),
        Band(position=1336, role="outras", assignment="glicose: δ(CH)",
         sources=(DUMOUILLA,)),
        Band(position=1264, role="outras", assignment="glicose: ώ(CH2)",
         sources=(DUMOUILLA,)),
        Band(position=846, role="outras", assignment="glicose: δ(COH), região anomérica",
         sources=(DUMOUILLA,)),
        Band(position=1645, role="agua", assignment="água: δ(HOH)",
         sources=(DUMOUILLA,)),
    ),
}

ROLES = ("alvo", "agua", "pigmento", "outras")


def windows(dataset: str, half_width: float, roles=("alvo",)) -> list[tuple[float, float]]:
    """As janelas [pico − meia largura, pico + meia largura] do conjunto.

    `half_width` vai na unidade do eixo do conjunto (nm no NIR, cm⁻¹ no
    Raman) e não tem padrão: a largura ainda não foi decidida.
    """
    if dataset not in BANDS:
        raise ValueError(f"conjunto sem janelas: {dataset}")
    if not half_width > 0:
        raise ValueError("a meia largura precisa ser positiva")
    unknown = set(roles) - set(ROLES)
    if unknown:
        raise ValueError(f"papéis desconhecidos: {sorted(unknown)}")
    return [(b.position - half_width, b.position + half_width)
            for b in BANDS[dataset] if b.role in roles]
