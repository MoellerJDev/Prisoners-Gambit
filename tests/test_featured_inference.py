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

    assert aligned is not None and "aligns" in aligned
    assert mismatched is not None and "higher-uncertainty future" in mismatched
