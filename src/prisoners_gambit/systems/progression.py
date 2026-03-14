from __future__ import annotations

from dataclasses import dataclass
import logging
import random
from typing import TYPE_CHECKING

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.systems.offers import generate_powerup_offers

if TYPE_CHECKING:
    from prisoners_gambit.core.models import Agent

logger = logging.getLogger(__name__)

MAX_AI_POWERUPS = 3
MAX_AI_POWERUP_ROLL_ATTEMPTS = 3


@dataclass(slots=True)
class FloorConfig:
    floor_number: int
    rounds_per_match: int
    ai_powerup_chance: float
    featured_matches: int
    referendum_reward: int
    label: str


class ProgressionEngine:
    def __init__(
        self,
        rng: random.Random,
        offers_per_floor: int,
        featured_matches_per_floor: int,
    ) -> None:
        self.rng = rng
        self.offers_per_floor = offers_per_floor
        self.featured_matches_per_floor = featured_matches_per_floor

    def build_floor_config(self, floor_number: int) -> FloorConfig:
        rounds_per_match = 6 + ((floor_number - 1) // 3)
        ai_powerup_chance = min(0.25 + (floor_number - 1) * 0.03, 0.75)
        featured_matches = min(self.featured_matches_per_floor + ((floor_number - 1) // 5), 5)
        referendum_reward = 3 + ((floor_number - 1) // 4)

        if floor_number <= 5:
            label = "Opening Tables"
        elif floor_number <= 10:
            label = "Calculated Risk"
        elif floor_number <= 15:
            label = "Knife's Edge"
        else:
            label = "Endgame Spiral"

        config = FloorConfig(
            floor_number=floor_number,
            rounds_per_match=rounds_per_match,
            ai_powerup_chance=ai_powerup_chance,
            featured_matches=featured_matches,
            referendum_reward=referendum_reward,
            label=label,
        )

        logger.debug("Built floor config: %s", config)
        return config

    def grant_ai_powerups(
        self,
        survivors: list["Agent"],
        player: "Agent",
        floor_config: FloorConfig,
    ) -> None:
        for survivor in survivors:
            if survivor is player:
                continue

            if self.rng.random() <= floor_config.ai_powerup_chance:
                if len(survivor.powerups) >= MAX_AI_POWERUPS:
                    continue

                owned_types = {type(existing) for existing in survivor.powerups}
                available_types = {type(powerup) for powerup in build_powerup_pool()}
                unowned_type_count = len(available_types - owned_types)
                if unowned_type_count == 0:
                    continue

                attempt_budget = max(MAX_AI_POWERUP_ROLL_ATTEMPTS, unowned_type_count)
                for _ in range(attempt_budget):
                    powerup = generate_powerup_offers(1, self.rng)[0]
                    if type(powerup) in owned_types:
                        continue
                    survivor.powerups.append(powerup)
                    logger.debug(
                        "Granted AI powerup | agent=%s | powerup=%s | chance=%.2f",
                        survivor.name,
                        powerup.name,
                        floor_config.ai_powerup_chance,
                    )
                    break
