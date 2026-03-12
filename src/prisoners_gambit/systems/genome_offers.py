from __future__ import annotations

import random

from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.core.genome_edits import FortressDoctrine, TyrantDoctrine, WildcardDoctrine
from prisoners_gambit.core.genome_edits import GenomeEdit


def generate_genome_edit_offers(count: int, rng: random.Random) -> list[GenomeEdit]:
    pool = build_genome_edit_pool()
    pivot_types = (FortressDoctrine, TyrantDoctrine, WildcardDoctrine)

    chosen: list[GenomeEdit] = []
    if count >= 3:
        pivot_pool = [edit for edit in pool if isinstance(edit, pivot_types)]
        if pivot_pool:
            chosen.append(rng.choice(pivot_pool))

    remaining_pool = [edit for edit in pool if all(type(edit) is not type(existing) for existing in chosen)]
    additional = rng.sample(remaining_pool, k=min(max(0, count - len(chosen)), len(remaining_pool)))
    chosen.extend(additional)

    offers = [edit.clone() for edit in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers
