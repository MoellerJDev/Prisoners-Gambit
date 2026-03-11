from __future__ import annotations

import logging
import random

from prisoners_gambit.content.names import build_lineage_descendant_name
from prisoners_gambit.core.models import Agent

logger = logging.getLogger(__name__)


class EvolutionEngine:
    def __init__(
        self,
        survivor_count: int,
        mutation_rate: float,
        descendant_mutation_bonus: float,
        rng: random.Random,
    ) -> None:
        self.survivor_count = survivor_count
        self.mutation_rate = mutation_rate
        self.descendant_mutation_bonus = descendant_mutation_bonus
        self.rng = rng
        self._player_lineage_spawn_serial = 0

    def split_population(self, ranked: list[Agent]) -> tuple[list[Agent], list[Agent]]:
        survivors = ranked[: self.survivor_count]
        eliminated = ranked[self.survivor_count :]

        logger.info(
            "Population split complete | survivors=%s | eliminated=%s",
            len(survivors),
            len(eliminated),
        )
        logger.debug(
            "Survivor names: %s | Eliminated names: %s",
            [agent.name for agent in survivors],
            [agent.name for agent in eliminated],
        )

        return survivors, eliminated

    def split_population_civil_war(self, ranked: list[Agent]) -> tuple[list[Agent], list[Agent]]:
        survivor_count = max(1, (len(ranked) + 1) // 2)
        survivors = ranked[:survivor_count]
        eliminated = ranked[survivor_count:]

        logger.info(
            "Civil war split complete | survivors=%s | eliminated=%s",
            len(survivors),
            len(eliminated),
        )
        logger.debug(
            "Civil war survivor names: %s | eliminated names: %s",
            [agent.name for agent in survivors],
            [agent.name for agent in eliminated],
        )

        return survivors, eliminated

    def repopulate(self, survivors: list[Agent], target_size: int) -> list[Agent]:
        next_population = list(survivors)

        while len(next_population) < target_size:
            parent = self.rng.choice(survivors)

            effective_mutation_rate = self.mutation_rate
            if parent.lineage_id == 1:
                effective_mutation_rate = min(
                    0.90,
                    self.mutation_rate * self.descendant_mutation_bonus,
                )

            child_genome = parent.genome.mutate(self.rng, effective_mutation_rate)

            if parent.lineage_id == 1 and self.rng.random() < 0.35:
                child_genome = child_genome.mutate(
                    self.rng,
                    min(0.90, effective_mutation_rate * 0.50),
                )

            name_override = None
            if parent.lineage_id == 1:
                self._player_lineage_spawn_serial += 1
                name_override = build_lineage_descendant_name(
                    serial=self._player_lineage_spawn_serial,
                    depth=parent.lineage_depth + 1,
                )

            child = parent.clone_for_offspring(child_genome, name_override=name_override)
            next_population.append(child)

            logger.debug(
                "Created offspring | parent=%s | child=%s | mutation_rate=%.3f | target_progress=%s/%s",
                parent.name,
                child.name,
                effective_mutation_rate,
                len(next_population),
                target_size,
            )

        return next_population