from __future__ import annotations

import random

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.offer_guidance import guidance_for_powerup
from prisoners_gambit.core.powerups import Powerup


def _offer_novelty_score(powerup: Powerup, chosen_vectors: set[str], chosen_phases: set[str]) -> int:
    guidance = guidance_for_powerup(powerup)
    score = 0
    if guidance.doctrine_vector not in chosen_vectors:
        score += 3
    if guidance.phase_support not in chosen_phases:
        score += 1
    return score


def generate_powerup_offers(count: int, rng: random.Random) -> list[Powerup]:
    """Generate deterministic doctrine-facing offers with directional diversity.

    For sets of 3+, the generator biases toward vectors and phase-support lanes not
    already represented so players choose between distinct lineage futures.
    """
    pool = build_powerup_pool()
    if count <= 0:
        return []

    chosen: list[Powerup] = []
    chosen_vectors: set[str] = set()
    chosen_phases: set[str] = set()

    while len(chosen) < count:
        remaining_pool = [powerup for powerup in pool if all(type(powerup) is not type(existing) for existing in chosen)]
        if not remaining_pool:
            break

        best_score = max(_offer_novelty_score(powerup, chosen_vectors, chosen_phases) for powerup in remaining_pool)
        candidates = [
            powerup for powerup in remaining_pool if _offer_novelty_score(powerup, chosen_vectors, chosen_phases) == best_score
        ]
        pick = rng.choice(candidates)
        chosen.append(pick)
        guidance = guidance_for_powerup(pick)
        chosen_vectors.add(guidance.doctrine_vector)
        chosen_phases.add(guidance.phase_support)

    offers = [powerup.clone() for powerup in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers
