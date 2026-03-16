from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from prisoners_gambit.content.strategic_text import (
    civil_war_featured_inference_lines,
    featured_inference_confidence_detail,
    featured_inference_confidence_label,
    featured_inference_future_text,
    featured_inference_stability_text,
    featured_inference_summary_clues,
    featured_inference_summary_scope,
    featured_inference_summary_tags,
)


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


@dataclass(frozen=True)
class FeaturedInferenceBrief:
    future: str
    stability: str
    confidence_label: str
    confidence_detail: str


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

    summary: list[str] = [featured_inference_summary_clues(signals.observed_clues)]
    if signals.inferred_tags:
        summary.append(featured_inference_summary_tags(signals.inferred_tags))

    summary.append(featured_inference_summary_scope())
    return summary


def synthesize_floor_featured_inference(clue_log: Sequence[str], *, max_lines: int = 3) -> list[str]:
    """Build a concise, deterministic floor-level summary from observed featured clues."""
    signals = normalize_featured_inference_signals(clue_log, max_clues=max_lines)
    return summarize_featured_inference_signals(signals)


def successor_featured_inference_brief(
    *,
    candidate_tags: Sequence[str],
    featured_inference_signals: FeaturedInferenceSignals,
) -> FeaturedInferenceBrief | None:
    if not candidate_tags or not featured_inference_signals.observed_clues:
        return None

    inferred = set(featured_inference_signals.inferred_tags)
    aligned = [tag for tag in candidate_tags if tag in inferred]
    return FeaturedInferenceBrief(
        future=_future_frame(candidate_tags),
        stability=_stability_frame(candidate_tags=candidate_tags, aligned=aligned),
        confidence_label=_confidence_label(aligned),
        confidence_detail=_confidence_detail(aligned),
    )


def successor_featured_inference_context(
    *,
    candidate_tags: Sequence[str],
    featured_inference_signals: FeaturedInferenceSignals,
) -> str | None:
    brief = successor_featured_inference_brief(
        candidate_tags=candidate_tags,
        featured_inference_signals=featured_inference_signals,
    )
    if brief is None:
        return None
    return (
        f"Future path: {brief.future} "
        f"Stability: {brief.stability} "
        f"Clue confidence: {brief.confidence_detail}"
    )


def civil_war_featured_inference_context(featured_inference_signals: FeaturedInferenceSignals) -> list[str]:
    """Map normalized featured signals to compact, deterministic civil-war framing."""
    inferred = set(featured_inference_signals.inferred_tags)
    if not inferred:
        return []

    framing: list[str] = []
    coercive = inferred & {"Aggressive", "Control", "Punishing", "Exploitative"}
    legitimacy = inferred & {"Cooperative", "Forgiving", "Consensus", "Referendum"}

    if coercive and legitimacy:
        framing.append(civil_war_featured_inference_lines("mixed"))
    elif coercive:
        framing.append(civil_war_featured_inference_lines("coercive"))
    elif legitimacy:
        framing.append(civil_war_featured_inference_lines("legitimacy"))

    if inferred & {"Retaliatory", "Punishing"}:
        framing.append(civil_war_featured_inference_lines("retaliation"))
    if inferred & {"Exploitative", "Aggressive", "Punishing"}:
        framing.append(civil_war_featured_inference_lines("deception"))

    return framing[:2]


def _future_frame(candidate_tags: Sequence[str]) -> str:
    tag_set = set(candidate_tags)
    hardline = tag_set & {"Aggressive", "Control", "Punishing", "Exploitative"}
    consensus = tag_set & {"Cooperative", "Forgiving", "Consensus", "Referendum"}

    if hardline and consensus:
        return featured_inference_future_text("hybrid")
    if hardline:
        return featured_inference_future_text("hardline")
    if consensus:
        return featured_inference_future_text("consensus")
    return featured_inference_future_text("ambiguous")


def _stability_frame(*, candidate_tags: Sequence[str], aligned: Sequence[str]) -> str:
    tag_set = set(candidate_tags)
    aligned_set = set(aligned)
    hardline = tag_set & {"Aggressive", "Control", "Punishing", "Exploitative"}
    consensus = tag_set & {"Cooperative", "Forgiving", "Consensus", "Referendum"}

    if hardline and consensus:
        if aligned_set & hardline and aligned_set & consensus:
            return featured_inference_stability_text("hybrid_confirmed")
        return featured_inference_stability_text("hybrid_unconfirmed")
    if hardline:
        if aligned_set & hardline:
            return featured_inference_stability_text("hardline_confirmed")
        return featured_inference_stability_text("hardline_unconfirmed")
    if consensus:
        if aligned_set & consensus:
            return featured_inference_stability_text("consensus_confirmed")
        return featured_inference_stability_text("consensus_unconfirmed")
    return featured_inference_stability_text("ambiguous")


def _confidence_label(aligned: Sequence[str]) -> str:
    return featured_inference_confidence_label(len(aligned))


def _confidence_detail(aligned: Sequence[str]) -> str:
    return featured_inference_confidence_detail(aligned)


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
    return [tag for tag, hints in _TAG_HINTS.items() if any(hint in text for hint in hints)]
