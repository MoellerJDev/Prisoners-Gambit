from __future__ import annotations

from collections.abc import Sequence


_TAG_HINTS: dict[str, tuple[str, ...]] = {
    "Aggressive": ("aggressive", "exploitative", "defected into your cooperation", "opened with d"),
    "Cooperative": ("cooperative", "opened with c", "forgave"),
    "Retaliatory": ("retaliated",),
    "Exploitative": ("exploitative", "defected into your cooperation"),
    "Forgiving": ("forgave",),
    "Control": ("directive", "control"),
    "Punishing": ("retaliated", "punished", "exploitative"),
    "Referendum": ("consensus", "forgave", "cooperative"),
    "Consensus": ("consensus", "forgave", "cooperative"),
    "Tempo": ("opening", "opened with"),
}


def synthesize_floor_featured_inference(clue_log: Sequence[str], *, max_lines: int = 3) -> list[str]:
    """Build a concise, deterministic floor-level summary from observed featured clues."""
    unique_clues = _dedupe_clues(clue_log)
    if not unique_clues:
        return []

    focus_clues = unique_clues[-max_lines:]
    summary: list[str] = [f"Observed featured signals: {' | '.join(focus_clues)}"]

    hinted_tags = _hinted_tags(unique_clues)
    if hinted_tags:
        summary.append(
            "Branch doctrine signals surfaced this floor: "
            + ", ".join(hinted_tags)
            + ". Use these reads to judge successor stability vs deception."
        )

    summary.append("Inference scope is observational only: no hidden opponents were revealed.")
    return summary


def successor_featured_inference_context(*, candidate_tags: Sequence[str], featured_inference_summary: Sequence[str]) -> str | None:
    if not candidate_tags or not featured_inference_summary:
        return None

    summary_text = " ".join(featured_inference_summary).lower()
    aligned = [tag for tag in candidate_tags if any(hint in summary_text for hint in _TAG_HINTS.get(tag, ()))]
    if aligned:
        joined = ", ".join(aligned[:2])
        return f"Featured inference fit: this branch aligns with floor reads on {joined.lower()} behavior."

    return "Featured inference tension: this branch is less represented in observed floor clues; treat as a higher-uncertainty future."


def _dedupe_clues(clue_log: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in clue_log:
        clue = raw.strip()
        if not clue:
            continue
        key = clue.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(clue)
    return result


def _hinted_tags(clues: Sequence[str]) -> list[str]:
    text = " ".join(clues).lower()
    tags = [tag for tag, hints in _TAG_HINTS.items() if any(hint in text for hint in hints)]
    return tags

