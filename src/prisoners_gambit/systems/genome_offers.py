from __future__ import annotations

import random

from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.offer_guidance import guidance_for_genome_edit


def _offer_novelty_score(edit: GenomeEdit, chosen_vectors: set[str], chosen_phases: set[str]) -> int:
    guidance = guidance_for_genome_edit(edit)
    score = 0
    if guidance.doctrine_vector not in chosen_vectors:
        score += 3
    if guidance.phase_support not in chosen_phases:
        score += 1
    return score


def generate_genome_edit_offers(count: int, rng: random.Random) -> list[GenomeEdit]:
    """Generate deterministic doctrine-facing edit offers with directional diversity."""
    pool = build_genome_edit_pool()
    if count <= 0:
        return []

    chosen: list[GenomeEdit] = []
    chosen_vectors: set[str] = set()
    chosen_phases: set[str] = set()

    while len(chosen) < count:
        remaining_pool = [edit for edit in pool if all(type(edit) is not type(existing) for existing in chosen)]
        if not remaining_pool:
            break

        best_score = max(_offer_novelty_score(edit, chosen_vectors, chosen_phases) for edit in remaining_pool)
        candidates = [edit for edit in remaining_pool if _offer_novelty_score(edit, chosen_vectors, chosen_phases) == best_score]
        pick = rng.choice(candidates)
        chosen.append(pick)
        guidance = guidance_for_genome_edit(pick)
        chosen_vectors.add(guidance.doctrine_vector)
        chosen_phases.add(guidance.phase_support)

    offers = [edit.clone() for edit in chosen]

    while len(offers) < count:
        offers.append(rng.choice(pool).clone())

    return offers
