from __future__ import annotations

import random

_TITLES = [
    "The Mirror",
    "The Rat",
    "The Saint",
    "The Schemer",
    "The Opportunist",
    "The Grudge",
    "The Optimist",
    "The Cold Eye",
    "The Pact",
    "The Knife",
    "The Liar",
    "The Patient One",
]

_SUFFIXES = [
    "of Ash",
    "of Silence",
    "of the Table",
    "of Small Mercies",
    "of Teeth",
    "of Doubt",
    "of Echoes",
    "of Smoke",
]

_LINEAGE_TITLES = [
    "Alpha",
    "Beta",
    "Gamma",
    "Delta",
    "Epsilon",
    "Zeta",
    "Eta",
    "Theta",
    "Iota",
    "Kappa",
    "Lambda",
    "Mu",
    "Nu",
    "Xi",
    "Omicron",
    "Pi",
    "Rho",
    "Sigma",
    "Tau",
    "Upsilon",
    "Phi",
    "Chi",
    "Psi",
    "Omega",
]


def build_agent_name(index: int, rng: random.Random) -> str:
    title = _TITLES[index % len(_TITLES)]

    if index < len(_TITLES):
        return f"{title} #{index + 1}"

    suffix = rng.choice(_SUFFIXES)
    return f"{title} {suffix} #{index + 1}"


def build_lineage_descendant_name(serial: int, depth: int) -> str:
    title = _LINEAGE_TITLES[(serial - 1) % len(_LINEAGE_TITLES)]
    cycle = ((serial - 1) // len(_LINEAGE_TITLES)) + 1

    if cycle == 1:
        return f"Heir {title}"

    return f"Heir {title}-{cycle}"