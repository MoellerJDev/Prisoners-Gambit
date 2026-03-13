from __future__ import annotations

from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import GenomeEditOfferView, PowerupOfferView
from prisoners_gambit.core.offer_guidance import (
    doctrine_drift_text,
    guidance_for_genome_edit,
    guidance_for_powerup,
    lineage_commitment_text,
)
from prisoners_gambit.core.powerups import Powerup


def to_powerup_offer_view(powerup: Powerup) -> PowerupOfferView:
    guidance = guidance_for_powerup(powerup)
    return PowerupOfferView(
        name=powerup.name,
        description=powerup.description,
        lineage_commitment=lineage_commitment_text(guidance),
        doctrine_vector=guidance.doctrine_vector,
        branch_identity=guidance.branch_identity,
        tradeoff=guidance.tradeoff,
        phase_support=guidance.phase_support,
        successor_pressure=guidance.successor_pressure,
        tags=list(powerup.keywords),
    )


def to_genome_edit_offer_view(
    edit: GenomeEdit,
    current_summary: str | None = None,
    projected_summary: str | None = None,
) -> GenomeEditOfferView:
    guidance = guidance_for_genome_edit(edit)
    return GenomeEditOfferView(
        name=edit.name,
        description=edit.description,
        lineage_commitment=lineage_commitment_text(guidance),
        doctrine_vector=guidance.doctrine_vector,
        branch_identity=guidance.branch_identity,
        tradeoff=guidance.tradeoff,
        phase_support=guidance.phase_support,
        successor_pressure=guidance.successor_pressure,
        current_summary=current_summary,
        projected_summary=projected_summary,
        doctrine_drift=doctrine_drift_text(guidance),
    )
