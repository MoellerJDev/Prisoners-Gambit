from __future__ import annotations

from prisoners_gambit.content.strategic_text import (
    GenomeStrategicProfile,
    PowerupStrategicProfile,
    curated_powerup_tags as build_curated_powerup_tags,
    doctrine_commitment_line as build_doctrine_commitment_line,
    doctrine_commitment_summary as build_doctrine_commitment_summary,
    fallback_genome_profile,
    fallback_powerup_profile,
    genome_profile as lookup_genome_profile,
    offer_fit_detail as lookup_offer_fit_detail,
    powerup_profile as lookup_powerup_profile,
    successor_break_point as successor_break_point_text,
    successor_headline as successor_headline_text,
    successor_play_pattern as successor_play_pattern_text,
)
from prisoners_gambit.core.featured_inference import FeaturedInferenceBrief
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.identity_analysis import AgentIdentity
from prisoners_gambit.core.offer_guidance import OfferDoctrineGuidance
from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.core.successor_analysis import SuccessorAssessment
from prisoners_gambit.systems.offers import OfferCategory


def doctrine_commitment_summary(*, house: str | None, primary: str | None, secondary: str | None) -> tuple[str, str]:
    return build_doctrine_commitment_summary(house=house, primary=primary, secondary=secondary)


def offer_fit_detail(category: OfferCategory) -> str:
    return lookup_offer_fit_detail(category)


def curated_powerup_tags(powerup: Powerup) -> list[str]:
    return build_curated_powerup_tags(keywords=powerup.keywords, crown_piece=powerup.crown_piece)


def powerup_profile(powerup: Powerup) -> PowerupStrategicProfile:
    profile = lookup_powerup_profile(powerup.name)
    if profile is None:
        fallback_tags = tuple(curated_powerup_tags(powerup)[:3]) or ("Flexible Piece",)
        return fallback_powerup_profile(description=powerup.description, fallback_tags=fallback_tags)
    return profile


def genome_profile(edit: GenomeEdit) -> GenomeStrategicProfile:
    profile = lookup_genome_profile(edit.name)
    if profile is None:
        return fallback_genome_profile(description=edit.description)
    return profile


def successor_headline(identity: AgentIdentity, assessment: SuccessorAssessment) -> str:
    tags = set(identity.tags)
    if {"Cooperative", "Retaliatory"} <= tags:
        return successor_headline_text("reciprocal", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if {"Aggressive", "Exploitative"} <= tags:
        return successor_headline_text("knife_first", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if "Referendum" in tags and "Control" in tags:
        return successor_headline_text("referendum_control", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if "Referendum" in tags:
        return successor_headline_text("referendum", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if "Control" in tags and "Punishing" in tags:
        return successor_headline_text("discipline", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if "Unstable" in tags:
        return successor_headline_text("unstable", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if "Defensive" in tags:
        return successor_headline_text("defensive", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if assessment.branch_role == "Future civil-war monster":
        return successor_headline_text("civil_war_monster", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    if assessment.branch_role == "Safe heir":
        return successor_headline_text("safe_heir", branch_role=assessment.branch_role, descriptor=identity.descriptor)
    return successor_headline_text("default", branch_role=assessment.branch_role, descriptor=identity.descriptor)


def successor_play_pattern(identity: AgentIdentity) -> str:
    tags = set(identity.tags)
    if {"Cooperative", "Retaliatory"} <= tags:
        return successor_play_pattern_text("reciprocal")
    if {"Aggressive", "Exploitative"} <= tags:
        return successor_play_pattern_text("knife_first")
    if "Referendum" in tags and "Control" in tags:
        return successor_play_pattern_text("referendum_control")
    if "Referendum" in tags:
        return successor_play_pattern_text("referendum")
    if "Control" in tags:
        return successor_play_pattern_text("control")
    if "Punishing" in tags:
        return successor_play_pattern_text("punishing")
    if "Unstable" in tags:
        return successor_play_pattern_text("unstable")
    return successor_play_pattern_text("default")


def successor_break_point(identity: AgentIdentity, assessment: SuccessorAssessment) -> str:
    tags = set(identity.tags)
    if "Unstable" in tags:
        return successor_break_point_text("unstable")
    if "Referendum" in tags and "Aggressive" not in tags:
        return successor_break_point_text("referendum")
    if "Control" in tags and "Defensive" not in tags:
        return successor_break_point_text("control")
    if {"Cooperative", "Retaliatory"} <= tags:
        return successor_break_point_text("reciprocal")
    if {"Aggressive", "Exploitative"} <= tags:
        return successor_break_point_text("knife_first")
    if assessment.branch_role == "Safe heir":
        return successor_break_point_text("safe_heir")
    return successor_break_point_text("default")


def successor_doctrine_arc(assessment: SuccessorAssessment) -> str:
    return assessment.succession_pitch


def successor_watch_out(assessment: SuccessorAssessment) -> str:
    primary = assessment.succession_risk.rstrip(".")
    secondary = assessment.danger_later.rstrip(".")
    if not primary:
        return secondary
    if not secondary or secondary.lower() in primary.lower():
        return primary + "."
    return f"{primary}. {secondary}."


def successor_why_now(assessment: SuccessorAssessment) -> str:
    return assessment.attractive_now


def successor_dynasty_future(assessment: SuccessorAssessment) -> str:
    return assessment.lineage_future


def doctrine_commitment_line(guidance: OfferDoctrineGuidance, *, house: str | None, primary: str | None, secondary: str | None) -> str:
    return build_doctrine_commitment_line(
        house=house,
        primary=primary,
        secondary=secondary,
        branch_identity=guidance.branch_identity,
    )


def format_featured_inference_lines(brief: FeaturedInferenceBrief | None) -> tuple[str | None, str | None, str | None, str | None]:
    if brief is None:
        return (None, None, None, None)
    return (
        brief.future,
        brief.stability,
        brief.confidence_detail,
        brief.confidence_label,
    )
