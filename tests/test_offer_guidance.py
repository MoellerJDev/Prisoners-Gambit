from prisoners_gambit.core.offer_guidance import OfferDoctrineGuidance, doctrine_drift_text, lineage_commitment_text


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

    assert "ecosystem" in doctrine_drift_text(ecosystem).lower()
    assert "branch-mirror conflict" in doctrine_drift_text(civil_war).lower()
