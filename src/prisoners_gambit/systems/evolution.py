from __future__ import annotations

import logging
import random

from prisoners_gambit.content.names import build_lineage_descendant_name
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import BlocPolitics, MercyShield, OpeningGambit, SaboteurBloc, TrustDividend, UnityTicket

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

            inherited_powerups = [powerup.clone() for powerup in parent.powerups[:2]]

            if parent.lineage_id == 1:
                branch_focus = self.rng.choice([
                    "safe",
                    "ruthless",
                    "unstable",
                    "referendum",
                ])
                child_genome = self._apply_branch_focus(child_genome, branch_focus)

                doctrine_powerup = self._doctrine_powerup(branch_focus)
                if doctrine_powerup is not None:
                    inherited_powerups.append(doctrine_powerup)

            child = parent.clone_for_offspring(
                child_genome,
                name_override=name_override,
                inherited_powerups=inherited_powerups,
            )
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

    def _apply_branch_focus(self, genome, branch_focus: str):
        if branch_focus == "safe":
            genome.first_move = COOPERATE
            genome.response_table[(COOPERATE, COOPERATE)] = COOPERATE
            genome.response_table[(DEFECT, DEFECT)] = COOPERATE
            genome.noise = max(0.0, genome.noise - 0.06)
        elif branch_focus == "ruthless":
            genome.first_move = DEFECT
            genome.response_table[(COOPERATE, DEFECT)] = DEFECT
            genome.response_table[(DEFECT, COOPERATE)] = DEFECT
            genome.response_table[(DEFECT, DEFECT)] = DEFECT
            genome.noise = min(0.35, genome.noise + 0.02)
        elif branch_focus == "unstable":
            genome.noise = min(0.35, genome.noise + 0.10)
            genome.response_table[(COOPERATE, COOPERATE)] = DEFECT
            if self.rng.random() < 0.5:
                genome.first_move = DEFECT if genome.first_move == COOPERATE else COOPERATE
        elif branch_focus == "referendum":
            genome.first_move = COOPERATE
            genome.response_table[(COOPERATE, COOPERATE)] = COOPERATE
            genome.noise = max(0.0, genome.noise - 0.02)

        return genome

    def _doctrine_powerup(self, branch_focus: str):
        if branch_focus == "safe":
            return self.rng.choice([TrustDividend(bonus=1), MercyShield()])
        if branch_focus == "ruthless":
            return self.rng.choice([OpeningGambit(bonus=1), OpeningGambit(bonus=2)])
        if branch_focus == "referendum":
            return self.rng.choice([UnityTicket(), SaboteurBloc(), BlocPolitics(bonus=2)])
        return None
