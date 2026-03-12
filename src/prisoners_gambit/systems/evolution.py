from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from prisoners_gambit.content.names import build_lineage_descendant_name
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.doctrines import (
    ALL_BRANCH_FOCI,
    BRANCH_FOCUS_REFERENDUM,
    BRANCH_FOCUS_RUTHLESS,
    BRANCH_FOCUS_SAFE,
    BRANCH_FOCUS_UNSTABLE,
    BranchFocus,
)
from prisoners_gambit.core.lineage import detect_player_lineage_id, is_player_lineage
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import BlocPolitics, MercyShield, OpeningGambit, SaboteurBloc, TrustDividend, UnityTicket
from prisoners_gambit.core.strategy import StrategyGenome

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BranchFocusConfig:
    inherited_powerup_chance: float


BRANCH_FOCUS_CONFIG: dict[BranchFocus, BranchFocusConfig] = {
    BRANCH_FOCUS_SAFE: BranchFocusConfig(inherited_powerup_chance=0.85),
    BRANCH_FOCUS_RUTHLESS: BranchFocusConfig(inherited_powerup_chance=0.85),
    BRANCH_FOCUS_UNSTABLE: BranchFocusConfig(inherited_powerup_chance=0.40),
    BRANCH_FOCUS_REFERENDUM: BranchFocusConfig(inherited_powerup_chance=0.85),
}


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
        """Rebuild population while nudging active player-lineage branches to diverge earlier.

        The divergence pressure is intentional: it creates legible successor alternatives
        before late game. The focus + doctrine-powerup injection is deterministic under seed
        and controlled by `BRANCH_FOCUS_CONFIG` for easier balancing.
        """
        next_population = list(survivors)
        player_lineage_id = detect_player_lineage_id(survivors)

        while len(next_population) < target_size:
            parent = self.rng.choice(survivors)

            effective_mutation_rate = self.mutation_rate
            if is_player_lineage(parent.lineage_id, player_lineage_id):
                effective_mutation_rate = min(
                    0.90,
                    self.mutation_rate * self.descendant_mutation_bonus,
                )

            child_genome = parent.genome.mutate(self.rng, effective_mutation_rate)

            if is_player_lineage(parent.lineage_id, player_lineage_id) and self.rng.random() < 0.35:
                child_genome = child_genome.mutate(
                    self.rng,
                    min(0.90, effective_mutation_rate * 0.50),
                )

            name_override = None
            if is_player_lineage(parent.lineage_id, player_lineage_id):
                self._player_lineage_spawn_serial += 1
                name_override = build_lineage_descendant_name(
                    serial=self._player_lineage_spawn_serial,
                    depth=parent.lineage_depth + 1,
                )

            inherited_powerups = [powerup.clone() for powerup in parent.powerups[:2]]

            if is_player_lineage(parent.lineage_id, player_lineage_id):
                branch_focus = self.rng.choice(ALL_BRANCH_FOCI)
                child_genome = self._apply_branch_focus(child_genome, branch_focus)

                doctrine_powerup = self._doctrine_powerup(branch_focus)
                should_inject = doctrine_powerup is not None and self.rng.random() <= BRANCH_FOCUS_CONFIG[branch_focus].inherited_powerup_chance
                if should_inject:
                    inherited_powerups.append(doctrine_powerup)

                logger.debug(
                    "Applied player-lineage branch focus | parent=%s | focus=%s | doctrine_powerup=%s",
                    parent.name,
                    branch_focus,
                    doctrine_powerup.name if should_inject and doctrine_powerup else "none",
                )

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

    def _apply_branch_focus(self, genome: StrategyGenome, branch_focus: BranchFocus) -> StrategyGenome:
        if branch_focus == BRANCH_FOCUS_SAFE:
            genome.first_move = COOPERATE
            genome.response_table[(COOPERATE, COOPERATE)] = COOPERATE
            genome.response_table[(DEFECT, DEFECT)] = COOPERATE
            genome.noise = max(0.0, genome.noise - 0.06)
        elif branch_focus == BRANCH_FOCUS_RUTHLESS:
            genome.first_move = DEFECT
            genome.response_table[(COOPERATE, DEFECT)] = DEFECT
            genome.response_table[(DEFECT, COOPERATE)] = DEFECT
            genome.response_table[(DEFECT, DEFECT)] = DEFECT
            genome.noise = min(0.35, genome.noise + 0.02)
        elif branch_focus == BRANCH_FOCUS_UNSTABLE:
            genome.noise = min(0.35, genome.noise + 0.10)
            genome.response_table[(COOPERATE, COOPERATE)] = DEFECT
            if self.rng.random() < 0.5:
                genome.first_move = DEFECT if genome.first_move == COOPERATE else COOPERATE
        elif branch_focus == BRANCH_FOCUS_REFERENDUM:
            genome.first_move = COOPERATE
            genome.response_table[(COOPERATE, COOPERATE)] = COOPERATE
            genome.noise = max(0.0, genome.noise - 0.02)

        return genome

    def _doctrine_powerup(self, branch_focus: BranchFocus):
        if branch_focus == BRANCH_FOCUS_SAFE:
            return self.rng.choice([TrustDividend(bonus=1), MercyShield()])
        if branch_focus == BRANCH_FOCUS_RUTHLESS:
            return self.rng.choice([OpeningGambit(bonus=1), OpeningGambit(bonus=2)])
        if branch_focus == BRANCH_FOCUS_REFERENDUM:
            return self.rng.choice([UnityTicket(), SaboteurBloc(), BlocPolitics(bonus=2)])
        return None
