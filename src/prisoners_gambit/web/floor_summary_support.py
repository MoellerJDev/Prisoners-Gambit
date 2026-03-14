from __future__ import annotations

from dataclasses import dataclass

from prisoners_gambit.app.heir_view_mapping import to_floor_summary_heir_pressure_view
from prisoners_gambit.core.analysis import analyze_agent_identity, analyze_floor_heir_pressure
from prisoners_gambit.core.featured_inference import normalize_featured_inference_signals, summarize_featured_inference_signals
from prisoners_gambit.core.interaction import FloorSummaryEntryView, FloorSummaryState
from prisoners_gambit.core.models import Agent


@dataclass(frozen=True)
class FloorContinuityContext:
    previous_floor_names: set[str]
    branch_continuity_streaks: dict[str, int]
    previous_branch_stats: dict[str, tuple[int, int]]
    previous_pressure_levels: dict[str, int]
    previous_central_rival: str | None


@dataclass
class FloorSummarySynthesis:
    summary: FloorSummaryState
    continuity: FloorContinuityContext
    central_rival_name: str | None
    current_floor_new_central_rival: str | None


def synthesize_floor_summary(
    *,
    floor_number: int,
    summary_agents: list[Agent],
    player: Agent,
    floor_clue_log: list[str],
    continuity: FloorContinuityContext,
) -> FloorSummarySynthesis:
    pressure = analyze_floor_heir_pressure(summary_agents, player.lineage_id)
    heir_pressure = to_floor_summary_heir_pressure_view(pressure)
    successor_names = {entry.name for entry in heir_pressure.successor_candidates}
    threat_names = {entry.name for entry in heir_pressure.future_threats}

    entries: list[FloorSummaryEntryView] = []
    for agent in summary_agents:
        identity = analyze_agent_identity(agent)
        if agent.is_player:
            lineage_relation = "host"
        elif player.lineage_id is not None and agent.lineage_id == player.lineage_id:
            lineage_relation = "kin"
        else:
            lineage_relation = "outsider"

        survived_previous_floor = agent.name in continuity.previous_floor_names
        continuity_streak = continuity.branch_continuity_streaks.get(agent.name, 0) + 1 if survived_previous_floor else 1
        previous_score, previous_wins = continuity.previous_branch_stats.get(agent.name, (agent.score, agent.wins))
        score_delta = agent.score - previous_score
        wins_delta = agent.wins - previous_wins
        pressure_level = int(agent.name in successor_names) + int(agent.name in threat_names)
        previous_pressure_level = continuity.previous_pressure_levels.get(agent.name, pressure_level)
        if pressure_level > previous_pressure_level:
            pressure_trend = "rising"
        elif pressure_level < previous_pressure_level:
            pressure_trend = "falling"
        else:
            pressure_trend = "steady"

        entries.append(
            FloorSummaryEntryView(
                agent_id=agent.agent_id,
                name=agent.name,
                is_player=agent.is_player,
                score=agent.score,
                wins=agent.wins,
                lineage_depth=agent.lineage_depth,
                tags=identity.tags,
                descriptor=identity.descriptor,
                genome_summary=agent.genome.summary(),
                powerups=[p.name for p in agent.powerups],
                lineage_relation=lineage_relation,
                survived_previous_floor=survived_previous_floor,
                continuity_streak=continuity_streak,
                score_delta=score_delta,
                wins_delta=wins_delta,
                pressure_trend=pressure_trend,
            )
        )

    ordered_entries = sorted(entries, key=lambda entry: (-entry.score, entry.name, entry.lineage_depth))
    central_rival_name = next((entry.name for entry in ordered_entries if not entry.is_player), None)
    current_floor_new_central_rival = (
        central_rival_name
        if central_rival_name is not None and central_rival_name != continuity.previous_central_rival
        else None
    )

    summary = FloorSummaryState(
        floor_number=floor_number,
        entries=ordered_entries,
        heir_pressure=heir_pressure,
        featured_inference_summary=summarize_featured_inference_signals(normalize_featured_inference_signals(floor_clue_log)),
    )
    next_continuity = FloorContinuityContext(
        previous_floor_names={entry.name for entry in ordered_entries},
        branch_continuity_streaks={entry.name: entry.continuity_streak for entry in ordered_entries},
        previous_branch_stats={entry.name: (entry.score, entry.wins) for entry in ordered_entries},
        previous_pressure_levels={
            entry.name: int(entry.name in successor_names) + int(entry.name in threat_names) for entry in ordered_entries
        },
        previous_central_rival=central_rival_name,
    )
    return FloorSummarySynthesis(
        summary=summary,
        continuity=next_continuity,
        central_rival_name=central_rival_name,
        current_floor_new_central_rival=current_floor_new_central_rival,
    )
