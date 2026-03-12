from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


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


@dataclass(frozen=True)
class FeaturedInferenceSignals:
    """Deterministic, normalized featured-inference signals derived from observed clues."""

    observed_clues: tuple[str, ...]
    inferred_tags: tuple[str, ...]


def normalize_featured_inference_signals(clue_log: Sequence[str], *, max_clues: int = 3) -> FeaturedInferenceSignals:
    unique_clues = _dedupe_clues(clue_log)
    if not unique_clues:
        return FeaturedInferenceSignals(observed_clues=(), inferred_tags=())

    observed_clues = tuple(unique_clues[-max_clues:])
    inferred_tags = tuple(_hinted_tags(unique_clues))
    return FeaturedInferenceSignals(observed_clues=observed_clues, inferred_tags=inferred_tags)


def summarize_featured_inference_signals(signals: FeaturedInferenceSignals) -> list[str]:
    if not signals.observed_clues:
        return []

    summary: list[str] = [f"Observed featured signals: {' | '.join(signals.observed_clues)}"]
    if signals.inferred_tags:
        summary.append(
            "Branch doctrine signals surfaced this floor: "
            + ", ".join(signals.inferred_tags)
            + ". Use these reads to judge successor stability vs deception."
        )

    summary.append("Inference scope is observational only: no hidden opponents were revealed.")
    return summary


def synthesize_floor_featured_inference(clue_log: Sequence[str], *, max_lines: int = 3) -> list[str]:
    """Build a concise, deterministic floor-level summary from observed featured clues."""
    signals = normalize_featured_inference_signals(clue_log, max_clues=max_lines)
    return summarize_featured_inference_signals(signals)


def successor_featured_inference_context(
    *,
    candidate_tags: Sequence[str],
    featured_inference_signals: FeaturedInferenceSignals,
) -> str | None:
    if not candidate_tags or not featured_inference_signals.observed_clues:
        return None

    aligned = [tag for tag in candidate_tags if tag in set(featured_inference_signals.inferred_tags)]
    future_frame = _future_frame(candidate_tags)
    stability_frame = _stability_frame(candidate_tags=candidate_tags, aligned=aligned)
    confidence_frame = _confidence_frame(aligned)
    return f"Competing future: {future_frame} Stability: {stability_frame} Featured-read confidence: {confidence_frame}"


def _future_frame(candidate_tags: Sequence[str]) -> str:
    tag_set = set(candidate_tags)
    hardline = tag_set & {"Aggressive", "Control", "Punishing", "Exploitative"}
    consensus = tag_set & {"Cooperative", "Forgiving", "Consensus", "Referendum"}

    if hardline and consensus:
        return "hybrid lineage branch blending coercive doctrine with consensus habits, creating dual succession pressures"
    if hardline:
        return "hardline lineage branch centered on control, punishment, and deception pressure"
    if consensus:
        return "consensus lineage branch centered on reciprocity, legitimacy, and coalition doctrine"
    return "ambiguous lineage branch with unclear doctrine inheritance"


def _stability_frame(*, candidate_tags: Sequence[str], aligned: Sequence[str]) -> str:
    tag_set = set(candidate_tags)
    aligned_set = set(aligned)
    hardline = tag_set & {"Aggressive", "Control", "Punishing", "Exploitative"}
    consensus = tag_set & {"Cooperative", "Forgiving", "Consensus", "Referendum"}

    if hardline and consensus:
        if aligned_set & hardline and aligned_set & consensus:
            return "broadly stable now, but civil-war fracture risk rises because rival heirs can challenge either doctrine wing"
        return "fragile because the floor has not clearly validated both doctrine wings"
    if hardline:
        if aligned_set & hardline:
            return "stable while coercive reads persist, but brittle if floors pivot toward cooperative legitimacy"
        return "fragile: coercive doctrine is under-read this floor and can trigger succession backlash"
    if consensus:
        if aligned_set & consensus:
            return "stable while trust loops hold, but vulnerable to betrayal cascades in civil-war mirrors"
        return "fragile: consensus doctrine lacks floor confirmation and can be exploited by deceptive rivals"
    return "uncertain because observed reads do not anchor a clear doctrine trajectory"


def _confidence_frame(aligned: Sequence[str]) -> str:
    if len(aligned) >= 2:
        joined = ", ".join(aligned[:2]).lower()
        return f"high—observed featured reads reinforce this branch on {joined}"
    if len(aligned) == 1:
        return f"moderate—only {aligned[0].lower()} is directly reinforced; keep deception risk in view"
    return "low—observed featured reads do not directly reinforce this branch future"


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
