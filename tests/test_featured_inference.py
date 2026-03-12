from prisoners_gambit.core.featured_inference import (
    successor_featured_inference_context,
    synthesize_floor_featured_inference,
)


def test_floor_summary_includes_deterministic_featured_inference_synthesis() -> None:
    clues = [
        "Opened with C; compare against roster aggression/cooperation tags.",
        "Retaliated after your defection; retaliatory read strengthened.",
        "Tag alignment check: observed line remains compatible with Cooperative profile.",
    ]

    first = synthesize_floor_featured_inference(clues)
    second = synthesize_floor_featured_inference(clues)

    assert first == second
    assert any("Observed featured signals" in line for line in first)
    assert any("Inference scope is observational only" in line for line in first)


def test_successor_framing_uses_featured_inference_context() -> None:
    summary = synthesize_floor_featured_inference(
        [
            "Opened with C; compare against roster aggression/cooperation tags.",
            "Retaliated after your defection; retaliatory read strengthened.",
        ]
    )

    aligned = successor_featured_inference_context(
        candidate_tags=["Cooperative", "Retaliatory"],
        featured_inference_summary=summary,
    )
    mismatched = successor_featured_inference_context(
        candidate_tags=["Control"],
        featured_inference_summary=summary,
    )

    assert aligned is not None and "Competing future" in aligned
    assert aligned is not None and "consensus lineage branch" in aligned
    assert aligned is not None and "high" in aligned
    assert mismatched is not None and "hardline lineage branch" in mismatched
    assert mismatched is not None and "low" in mismatched


def test_successor_framing_differs_across_competing_tag_futures() -> None:
    coercive_summary = synthesize_floor_featured_inference(
        [
            "Opened with D and pressed directive tempo across rounds.",
            "Punished cooperation windows after one betrayal.",
        ]
    )
    consensus_summary = synthesize_floor_featured_inference(
        [
            "Opened with C and forgave one defection to preserve trust.",
            "Consensus lane stayed cooperative through pressure.",
        ]
    )

    hardline = successor_featured_inference_context(
        candidate_tags=["Control", "Punishing"],
        featured_inference_summary=coercive_summary,
    )
    consensus = successor_featured_inference_context(
        candidate_tags=["Consensus", "Forgiving"],
        featured_inference_summary=consensus_summary,
    )

    assert hardline is not None and "hardline lineage branch" in hardline
    assert hardline is not None and "coercive reads persist" in hardline
    assert hardline is not None and "high" in hardline
    assert consensus is not None and "consensus lineage branch" in consensus
    assert consensus is not None and "trust loops hold" in consensus
    assert consensus is not None and "high" in consensus
