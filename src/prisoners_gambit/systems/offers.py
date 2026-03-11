from __future__ import annotations

import random

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.powerups import Powerup


def generate_powerup_offers(count: int, rng: random.Random) -> list[Powerup]:
    pool = build_powerup_pool()
    chosen = rng.sample(pool, k=min(count, len(pool)))
    offers = [powerup.clone() for powerup in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers