from __future__ import annotations

from dataclasses import dataclass
import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.strategy import StrategyGenome, random_genome


@dataclass(slots=True)
class ArchetypeBlueprint:
    label: str
    public_profile: str
    genome: StrategyGenome


def _always_cooperate(rng: random.Random) -> ArchetypeBlueprint:
    return ArchetypeBlueprint(
        label="The Saint",
        public_profile="Openly cooperative",
        genome=StrategyGenome(
            first_move=COOPERATE,
            response_table={
                (COOPERATE, COOPERATE): COOPERATE,
                (COOPERATE, DEFECT): COOPERATE,
                (DEFECT, COOPERATE): COOPERATE,
                (DEFECT, DEFECT): COOPERATE,
            },
            noise=0.0,
        ),
    )


def _always_defect(rng: random.Random) -> ArchetypeBlueprint:
    return ArchetypeBlueprint(
        label="The Rat",
        public_profile="Openly predatory",
        genome=StrategyGenome(
            first_move=DEFECT,
            response_table={
                (COOPERATE, COOPERATE): DEFECT,
                (COOPERATE, DEFECT): DEFECT,
                (DEFECT, COOPERATE): DEFECT,
                (DEFECT, DEFECT): DEFECT,
            },
            noise=0.0,
        ),
    )


def _tit_for_tat(rng: random.Random) -> ArchetypeBlueprint:
    return ArchetypeBlueprint(
        label="The Mirror",
        public_profile="Reciprocal and reactive",
        genome=StrategyGenome(
            first_move=COOPERATE,
            response_table={
                (COOPERATE, COOPERATE): COOPERATE,
                (COOPERATE, DEFECT): DEFECT,
                (DEFECT, COOPERATE): COOPERATE,
                (DEFECT, DEFECT): DEFECT,
            },
            noise=0.0,
        ),
    )


def _grudger(rng: random.Random) -> ArchetypeBlueprint:
    return ArchetypeBlueprint(
        label="The Grudge",
        public_profile="Punishes betrayal hard",
        genome=StrategyGenome(
            first_move=COOPERATE,
            response_table={
                (COOPERATE, COOPERATE): COOPERATE,
                (COOPERATE, DEFECT): DEFECT,
                (DEFECT, COOPERATE): DEFECT,
                (DEFECT, DEFECT): DEFECT,
            },
            noise=0.0,
        ),
    )


def _chaotic(rng: random.Random) -> ArchetypeBlueprint:
    genome = random_genome(rng)
    genome.noise = max(genome.noise, 0.18)
    return ArchetypeBlueprint(
        label="The Schemer",
        public_profile="Erratic and hard to read",
        genome=genome,
    )


_ARCHETYPES = [
    _always_cooperate,
    _always_defect,
    _tit_for_tat,
    _grudger,
    _chaotic,
]


def build_archetype(index: int, rng: random.Random) -> ArchetypeBlueprint:
    if index < len(_ARCHETYPES):
        return _ARCHETYPES[index](rng)

    if rng.random() < 0.65:
        return rng.choice(_ARCHETYPES)(rng)

    return ArchetypeBlueprint(
        label="Unknown",
        public_profile="Unclassified behavior",
        genome=random_genome(rng),
    )


def build_player_starter_genome() -> StrategyGenome:
    return StrategyGenome(
        first_move=COOPERATE,
        response_table={
            (COOPERATE, COOPERATE): COOPERATE,
            (COOPERATE, DEFECT): DEFECT,
            (DEFECT, COOPERATE): COOPERATE,
            (DEFECT, DEFECT): DEFECT,
        },
        noise=0.0,
    )