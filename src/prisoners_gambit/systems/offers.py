from __future__ import annotations

import random

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.offer_guidance import guidance_for_powerup
from prisoners_gambit.core.powerups import Powerup


def generate_powerup_offers(count: int, rng: random.Random) -> list[Powerup]:
    """Generate deterministic doctrine-facing offers with directional diversity.

    For sets of 3+, the generator prefers at least two distinct doctrine vectors so
    players choose between futures instead of taking flat-value upgrades.
    """
    pool = build_powerup_pool()
    if count <= 0:
        return []

    chosen: list[Powerup] = []
    chosen_vectors: set[str] = set()

    # Anchor larger sets with two different doctrine directions when possible.
    if count >= 3:
        vector_groups: dict[str, list[Powerup]] = {}
        for powerup in pool:
            vector_groups.setdefault(guidance_for_powerup(powerup).doctrine_vector, []).append(powerup)

        vectors = list(vector_groups.keys())
        rng.shuffle(vectors)
        for vector in vectors[:2]:
            candidates = vector_groups.get(vector, [])
            if candidates:
                pick = rng.choice(candidates)
                if all(type(pick) is not type(existing) for existing in chosen):
                    chosen.append(pick)
                    chosen_vectors.add(vector)

    while len(chosen) < count:
        remaining_pool = [powerup for powerup in pool if all(type(powerup) is not type(existing) for existing in chosen)]
        if not remaining_pool:
            break

        # Prefer vectors not represented yet to reduce obvious same-lane upgrades.
        unseen_vectors = [
            powerup for powerup in remaining_pool if guidance_for_powerup(powerup).doctrine_vector not in chosen_vectors
        ]
        selection_pool = unseen_vectors or remaining_pool
        pick = rng.choice(selection_pool)
        chosen.append(pick)
        chosen_vectors.add(guidance_for_powerup(pick).doctrine_vector)

    offers = [powerup.clone() for powerup in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers
