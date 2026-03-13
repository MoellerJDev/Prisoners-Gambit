from __future__ import annotations

from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import GenomeEditOfferView, PowerupOfferView
from prisoners_gambit.core.offer_guidance import (
    doctrine_drift_text,
    guidance_for_genome_edit,
    guidance_for_powerup,
    lineage_commitment_text,
)
from prisoners_gambit.core.powerups import Powerup, powerup_presentation

_ROLE_ORDER = ("anchor", "enabler", "payoff", "amplifier", "bridge")


def _role_hint(powerup: Powerup) -> str | None:
    tags = set(powerup.keywords)
    for role in _ROLE_ORDER:
        if role in tags:
            return role
    return None


def to_powerup_offer_view(powerup: Powerup, relevance_hint: str | None = None) -> PowerupOfferView:
    guidance = guidance_for_powerup(powerup)
    role_hint = _role_hint(powerup)
    branch_identity = guidance.branch_identity if role_hint is None else f"{guidance.branch_identity} ({role_hint})"
    trigger, effect, role_text = powerup_presentation(powerup)
    return PowerupOfferView(
        name=powerup.name,
        description=powerup.description,
        trigger=trigger,
        effect=effect,
        role=role_text,
        lineage_commitment=lineage_commitment_text(guidance),
        doctrine_vector=guidance.doctrine_vector,
        branch_identity=branch_identity,
        tradeoff=guidance.tradeoff,
        phase_support=guidance.phase_support,
        successor_pressure=guidance.successor_pressure,
        tags=list(powerup.keywords),
        relevance_hint=relevance_hint,
        crown_hint=("Crown piece · dynasty-defining" if powerup.crown_piece else None),
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
