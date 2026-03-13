from __future__ import annotations

from prisoners_gambit.content.powerup_metadata import presentation_for_powerup
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import GenomeEditOfferView, PowerupOfferView
from prisoners_gambit.core.offer_guidance import (
    doctrine_drift_text,
    guidance_for_genome_edit,
    guidance_for_powerup,
    lineage_commitment_text,
)
from prisoners_gambit.core.powerups import Powerup


def to_powerup_offer_view(powerup: Powerup, relevance_hint: str | None = None) -> PowerupOfferView:
    guidance = guidance_for_powerup(powerup)
    presentation = presentation_for_powerup(powerup)
    branch_identity = f"{guidance.branch_identity} ({presentation.role_hint})"
    return PowerupOfferView(
        name=powerup.name,
        description=powerup.description,
        trigger=presentation.trigger,
        effect=presentation.effect,
        role=presentation.role_text,
        lineage_commitment=lineage_commitment_text(guidance),
        doctrine_vector=guidance.doctrine_vector,
        branch_identity=branch_identity,
        tradeoff=guidance.tradeoff,
        phase_support=guidance.phase_support,
        successor_pressure=guidance.successor_pressure,
        tags=list(powerup.keywords),
        relevance_hint=relevance_hint,
        crown_hint=presentation.crown_hint,
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
