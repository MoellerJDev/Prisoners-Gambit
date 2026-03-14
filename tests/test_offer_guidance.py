import pytest

from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.core.offer_guidance import (
    OfferDoctrineGuidance,
    doctrine_drift_text,
    guidance_for_dynamic_genome_edit,
    guidance_for_dynamic_powerup,
    guidance_for_genome_edit,
    guidance_for_powerup,
    lineage_commitment_text,
    validate_declared_guidance_coverage,
)
from prisoners_gambit.core.powerups import ALL_POWERUP_TYPES


def test_lineage_commitment_uses_doctrine_vector_vocabulary() -> None:
    guidance = OfferDoctrineGuidance(
        doctrine_vector="trust / reciprocity",
        branch_identity="x",
        tradeoff="x",
        phase_support="ecosystem survival",
        successor_pressure="x",
    )

    assert "reciprocal" in lineage_commitment_text(guidance).lower()


def test_doctrine_drift_tracks_phase_support_lane() -> None:
    ecosystem = OfferDoctrineGuidance("v", "b", "t", "ecosystem survival", "s")
    civil_war = OfferDoctrineGuidance("v", "b", "t", "civil-war readiness", "s")

    assert doctrine_drift_text(ecosystem).startswith("Favors heirs") and "ecosystem" in doctrine_drift_text(ecosystem).lower()
    assert doctrine_drift_text(civil_war).startswith("Favors heirs") and "branch-mirror conflict" in doctrine_drift_text(civil_war).lower()



def test_guidance_lookup_fails_loudly_for_missing_catalog_entries() -> None:
    class _UnknownPowerup:
        name = "Unknown Powerup"

    class _UnknownGenomeEdit:
        name = "Unknown Genome Edit"

    with pytest.raises(KeyError, match="Missing doctrine guidance"):
        guidance_for_powerup(_UnknownPowerup())  # type: ignore[arg-type]
    with pytest.raises(KeyError, match="Missing doctrine guidance"):
        guidance_for_genome_edit(_UnknownGenomeEdit())  # type: ignore[arg-type]


def test_all_declared_powerups_and_genome_edits_have_guidance() -> None:
    powerup_names = {powerup_type().name for powerup_type in ALL_POWERUP_TYPES}
    genome_edit_names = {edit.name for edit in build_genome_edit_pool()}

    validate_declared_guidance_coverage(powerup_names=powerup_names, genome_edit_names=genome_edit_names)


def test_dynamic_guidance_lookup_is_explicitly_optional() -> None:
    assert guidance_for_dynamic_powerup("not-a-catalog-powerup") is None
    assert guidance_for_dynamic_genome_edit("not-a-catalog-genome-edit") is None
