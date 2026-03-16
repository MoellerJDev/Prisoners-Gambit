from __future__ import annotations

from prisoners_gambit.core.choice_presenters import (
    format_featured_inference_lines,
    successor_break_point,
    successor_doctrine_arc,
    successor_dynasty_future,
    successor_headline,
    successor_play_pattern,
    successor_watch_out,
    successor_why_now,
)
from prisoners_gambit.core.featured_inference import FeaturedInferenceBrief
from prisoners_gambit.core.heir_pressure import FloorHeirPressure
from prisoners_gambit.core.interaction import FloorSummaryHeirPressureView, FloorSummaryPressureEntryView, SuccessorCandidateView


def to_floor_summary_heir_pressure_view(pressure: FloorHeirPressure) -> FloorSummaryHeirPressureView:
    return FloorSummaryHeirPressureView(
        branch_doctrine=pressure.branch_doctrine,
        successor_candidates=[to_floor_summary_pressure_entry_view(candidate) for candidate in pressure.successor_candidates],
        future_threats=[to_floor_summary_pressure_entry_view(candidate) for candidate in pressure.future_threats],
    )


def to_floor_summary_pressure_entry_view(candidate) -> FloorSummaryPressureEntryView:
    return FloorSummaryPressureEntryView(
        name=candidate.name,
        branch_role=candidate.branch_role,
        shaping_causes=list(candidate.shaping_causes),
        score=candidate.score,
        wins=candidate.wins,
        tags=list(candidate.tags),
        descriptor=candidate.descriptor,
        rationale=candidate.rationale,
    )


def to_successor_candidate_view(
    *,
    agent,
    identity,
    assessment,
    featured_inference_context: str | None = None,
    featured_inference_brief: FeaturedInferenceBrief | None = None,
) -> SuccessorCandidateView:
    clue_future, clue_stability, clue_confidence, clue_confidence_label = format_featured_inference_lines(featured_inference_brief)
    return SuccessorCandidateView(
        name=agent.name,
        lineage_depth=agent.lineage_depth,
        score=agent.score,
        wins=agent.wins,
        branch_role=assessment.branch_role,
        branch_doctrine=assessment.branch_doctrine,
        shaping_causes=list(assessment.shaping_causes),
        tags=identity.tags,
        descriptor=identity.descriptor,
        tradeoffs=list(assessment.tradeoffs),
        strengths=list(assessment.strengths),
        liabilities=list(assessment.liabilities),
        attractive_now=assessment.attractive_now,
        danger_later=assessment.danger_later,
        lineage_future=assessment.lineage_future,
        succession_pitch=assessment.succession_pitch,
        succession_risk=assessment.succession_risk,
        anti_score_note=assessment.anti_score_note,
        genome_summary=agent.genome.summary(),
        powerups=[powerup.name for powerup in agent.powerups],
        featured_inference_context=featured_inference_context,
        headline=successor_headline(identity, assessment),
        play_pattern=successor_play_pattern(identity),
        why_now=successor_why_now(assessment),
        watch_out=successor_watch_out(assessment),
        dynasty_future=successor_dynasty_future(assessment),
        doctrine_arc=successor_doctrine_arc(assessment),
        clue_future=clue_future,
        clue_stability=clue_stability,
        clue_confidence=clue_confidence,
        clue_confidence_label=clue_confidence_label,
    )
