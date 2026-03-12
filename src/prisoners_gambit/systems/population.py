from __future__ import annotations

import random

from prisoners_gambit.content.archetypes import build_archetype, build_player_starter_genome
from prisoners_gambit.content.names import build_agent_name
from prisoners_gambit.core.lineage import PLAYER_LINEAGE_ID
from prisoners_gambit.core.models import Agent


def create_population(size: int, rng: random.Random) -> list[Agent]:
    if size < 2:
        raise ValueError("Population size must be at least 2.")

    population: list[Agent] = [
        Agent(
            name="You",
            genome=build_player_starter_genome(),
            public_profile="Adaptive human pilot",
            is_player=True,
            lineage_id=PLAYER_LINEAGE_ID,
            lineage_depth=0,
        )
    ]

    for index in range(size - 1):
        name = build_agent_name(index=index, rng=rng)
        archetype = build_archetype(index=index, rng=rng)
        population.append(
            Agent(
                name=name,
                genome=archetype.genome,
                public_profile=archetype.public_profile,
                is_player=False,
                lineage_id=None,
                lineage_depth=0,
            )
        )

    return population