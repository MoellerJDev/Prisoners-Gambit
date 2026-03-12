from __future__ import annotations

import random

from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.offer_guidance import guidance_for_genome_edit


def generate_genome_edit_offers(count: int, rng: random.Random) -> list[GenomeEdit]:
    """Generate deterministic doctrine-facing edit offers with directional diversity."""
    pool = build_genome_edit_pool()
    if count <= 0:
        return []

    chosen: list[GenomeEdit] = []
    chosen_vectors: set[str] = set()

    if count >= 3:
        vector_groups: dict[str, list[GenomeEdit]] = {}
        for edit in pool:
            vector_groups.setdefault(guidance_for_genome_edit(edit).doctrine_vector, []).append(edit)

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
        remaining_pool = [edit for edit in pool if all(type(edit) is not type(existing) for existing in chosen)]
        if not remaining_pool:
            break

        unseen_vectors = [edit for edit in remaining_pool if guidance_for_genome_edit(edit).doctrine_vector not in chosen_vectors]
        selection_pool = unseen_vectors or remaining_pool
        pick = rng.choice(selection_pool)
        chosen.append(pick)
        chosen_vectors.add(guidance_for_genome_edit(pick).doctrine_vector)

    offers = [edit.clone() for edit in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers
