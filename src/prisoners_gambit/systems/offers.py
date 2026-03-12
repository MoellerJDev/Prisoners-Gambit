from __future__ import annotations

import random

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.doctrines import BRANCH_FOCUS_REFERENDUM, BRANCH_FOCUS_RUTHLESS, BRANCH_FOCUS_SAFE, BRANCH_FOCUS_UNSTABLE
from prisoners_gambit.core.powerups import Powerup


def generate_powerup_offers(count: int, rng: random.Random) -> list[Powerup]:
    """Generate deterministic powerup offers with one doctrine-pillar nudge in larger sets.

    The bias is small and explicit so branch divergence remains understandable and tuneable.
    """
    pool = build_powerup_pool()

    pillar_groups = {
        BRANCH_FOCUS_SAFE: {"Trust Dividend", "Mercy Shield", "Golden Handshake"},
        BRANCH_FOCUS_RUTHLESS: {"Opening Gambit", "Spite Engine", "Compliance Dividend", "Last Laugh"},
        BRANCH_FOCUS_REFERENDUM: {"Unity Ticket", "Saboteur Bloc", "Bloc Politics"},
        BRANCH_FOCUS_UNSTABLE: {"Coercive Control", "Counter-Intel", "Panic Button"},
    }

    chosen: list[Powerup] = []
    if count >= 3:
        pillar_name = rng.choice(list(pillar_groups.keys()))
        pillar_candidates = [powerup for powerup in pool if powerup.name in pillar_groups[pillar_name]]
        if pillar_candidates:
            chosen.append(rng.choice(pillar_candidates))

    remaining_pool = [powerup for powerup in pool if all(type(powerup) is not type(existing) for existing in chosen)]
    chosen.extend(rng.sample(remaining_pool, k=min(max(0, count - len(chosen)), len(remaining_pool))))
    offers = [powerup.clone() for powerup in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers
