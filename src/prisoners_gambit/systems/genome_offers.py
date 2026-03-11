from __future__ import annotations

import random

from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.core.genome_edits import GenomeEdit


def generate_genome_edit_offers(count: int, rng: random.Random) -> list[GenomeEdit]:
    pool = build_genome_edit_pool()
    chosen = rng.sample(pool, k=min(count, len(pool)))
    offers = [edit.clone() for edit in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers