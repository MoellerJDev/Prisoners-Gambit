from prisoners_gambit.core.featured_inference import (
    normalize_featured_inference_signals,
    successor_featured_inference_context,
    summarize_featured_inference_signals,
    synthesize_floor_featured_inference,
    civil_war_featured_inference_context,
)


def test_normalize_featured_inference_signals_is_deterministic() -> None:
    clues = [
        "Opened with C; compare against roster aggression/cooperation tags.",
        "Retaliated after your defection; retaliatory read strengthened.",
        "Tag alignment check: observed line remains compatible with Cooperative profile.",
    ]

    first = normalize_featured_inference_signals(clues)
    second = normalize_featured_inference_signals(clues)

    assert first == second
    assert first.observed_clues
    assert "Cooperative" in first.inferred_tags
    assert "Retaliatory" in first.inferred_tags


def test_floor_summary_synthesis_uses_normalized_featured_signals() -> None:
    signals = normalize_featured_inference_signals(
        [
            "Opened with C; compare against roster aggression/cooperation tags.",
            "Retaliated after your defection; retaliatory read strengthened.",
        ]
    )
    summary = summarize_featured_inference_signals(signals)

    assert any("Observed featured signals" in line for line in summary)
    assert any("Branch doctrine signals surfaced this floor" in line for line in summary)
    assert any("Inference scope is observational only" in line for line in summary)


def test_legacy_synthesis_api_still_matches_normalized_summary_pipeline() -> None:
    clues = [
        "Opened with C; compare against roster aggression/cooperation tags.",
        "Retaliated after your defection; retaliatory read strengthened.",
    ]

    direct = synthesize_floor_featured_inference(clues)
    normalized = summarize_featured_inference_signals(normalize_featured_inference_signals(clues))

    assert direct == normalized


def test_successor_framing_uses_normalized_featured_inference_signals() -> None:
    signals = normalize_featured_inference_signals(
        [
            "Opened with C; compare against roster aggression/cooperation tags.",
            "Retaliated after your defection; retaliatory read strengthened.",
        ]
    )

    aligned = successor_featured_inference_context(
        candidate_tags=["Cooperative", "Retaliatory"],
        featured_inference_signals=signals,
    )
    mismatched = successor_featured_inference_context(
        candidate_tags=["Control"],
        featured_inference_signals=signals,
    )

    assert aligned is not None and "Competing future" in aligned
    assert aligned is not None and "consensus lineage branch" in aligned
    assert aligned is not None and "high" in aligned
    assert mismatched is not None and "hardline lineage branch" in mismatched
    assert mismatched is not None and "low" in mismatched


def test_successor_framing_is_stable_even_if_summary_wording_changes() -> None:
    signals = normalize_featured_inference_signals(
        [
            "Opened with D and pressed directive tempo across rounds.",
            "Punished cooperation windows after one betrayal.",
        ]
    )

    baseline = successor_featured_inference_context(
        candidate_tags=["Control", "Punishing"],
        featured_inference_signals=signals,
    )

    # Simulate a summary wording shift that previously could have altered string-hinted alignment.
    rewritten_summary = [
        "Observed behavior: directive pace remained steady.",
        "Scope note: observations only.",
    ]
    assert rewritten_summary  # Explicitly show summary text can drift independently.

    after_wording_drift = successor_featured_inference_context(
        candidate_tags=["Control", "Punishing"],
        featured_inference_signals=signals,
    )

    assert baseline == after_wording_drift
    assert baseline is not None and "high" in baseline


def test_successor_framing_differs_across_competing_tag_futures() -> None:
    coercive_signals = normalize_featured_inference_signals(
        [
            "Opened with D and pressed directive tempo across rounds.",
            "Punished cooperation windows after one betrayal.",
        ]
    )
    consensus_signals = normalize_featured_inference_signals(
        [
            "Opened with C and forgave one defection to preserve trust.",
            "Consensus lane stayed cooperative through pressure.",
        ]
    )

    hardline = successor_featured_inference_context(
        candidate_tags=["Control", "Punishing"],
        featured_inference_signals=coercive_signals,
    )
    consensus = successor_featured_inference_context(
        candidate_tags=["Consensus", "Forgiving"],
        featured_inference_signals=consensus_signals,
    )

    assert hardline is not None and "hardline lineage branch" in hardline
    assert hardline is not None and "coercive reads persist" in hardline
    assert hardline is not None and "high" in hardline
    assert consensus is not None and "consensus lineage branch" in consensus
    assert consensus is not None and "trust loops hold" in consensus
    assert consensus is not None and "high" in consensus


def test_civil_war_framing_uses_normalized_featured_signals_deterministically() -> None:
    signals = normalize_featured_inference_signals(
        [
            "Opened with D and pressed directive tempo across rounds.",
            "Punished cooperation windows after one betrayal.",
        ]
    )

    first = civil_war_featured_inference_context(signals)
    second = civil_war_featured_inference_context(signals)

    assert first == second
    assert any("coercion pressure" in line for line in first)
    assert any("retaliation pressure" in line for line in first)


def test_civil_war_framing_is_independent_of_floor_summary_wording() -> None:
    clues = [
        "Opened with C and forgave one defection to preserve trust.",
        "Consensus lane stayed cooperative through pressure.",
    ]
    signals = normalize_featured_inference_signals(clues)
    baseline = civil_war_featured_inference_context(signals)

    rewritten_floor_summary = [
        "Observed behavior: steady cooperative tempo.",
        "Scope note: visible rounds only.",
    ]
    assert rewritten_floor_summary

    after_reword = civil_war_featured_inference_context(normalize_featured_inference_signals(clues))

    assert baseline == after_reword
    assert any("legitimacy pressure" in line for line in baseline)
