from __future__ import annotations

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


def to_successor_candidate_view(*, agent, identity, assessment) -> SuccessorCandidateView:
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
        genome_summary=agent.genome.summary(),
        powerups=[powerup.name for powerup in agent.powerups],
    )
