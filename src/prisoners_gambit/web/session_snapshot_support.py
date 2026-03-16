from __future__ import annotations

from dataclasses import dataclass

from prisoners_gambit.content.session_text import (
    floor_pressure_unresolved,
    lineage_cause_phrase as build_lineage_cause_phrase,
    lineage_direction_forming,
    risk_posture_civil_war,
    risk_posture_instability,
    risk_posture_named,
    stability_posture_contested,
    stability_posture_controlled,
    strategic_snapshot_civil_war_detail,
    strategic_snapshot_headline,
    strategic_snapshot_lineage_chip,
    strategic_snapshot_pressure_chip,
    strategic_snapshot_pressure_detail,
    strategic_snapshot_rival_chip,
    strategic_snapshot_rival_detail,
    strategic_snapshot_rival_name,
    strategic_snapshot_rival_signal,
)
from prisoners_gambit.core.analysis import analyze_agent_identity
from prisoners_gambit.core.choice_presenters import doctrine_commitment_summary
from prisoners_gambit.core.interaction import DynastyBoardEntryView, DynastyBoardState, RunSnapshot, StrategicSnapshotState
from prisoners_gambit.core.models import Agent


@dataclass(frozen=True)
class DynastyBoardBuildContext:
    snapshot: RunSnapshot
    player: Agent
    opponent: Agent
    successor_candidates: list[Agent]
    current_floor_central_rival: str | None
    current_floor_new_central_rival: str | None


def lineage_cause_phrase(shaping_causes: list[str], fallback: str) -> str:
    lead = shaping_causes[0] if shaping_causes else fallback
    return build_lineage_cause_phrase(lead=lead)


def refresh_strategic_snapshot(snapshot: RunSnapshot, *, player_name: str, floor_number: int) -> StrategicSnapshotState:
    host_name = player_name
    floor_identity = snapshot.floor_identity
    if floor_identity and floor_identity.target_floor == floor_number and floor_identity.host_name:
        host_name = floor_identity.host_name

    dynasty_board = snapshot.dynasty_board
    board_entries = dynasty_board.entries if dynasty_board else []
    central_rival = next((entry for entry in board_entries if entry.is_central_rival), None)

    floor_pressure = floor_pressure_unresolved()
    if floor_identity is not None:
        floor_pressure = floor_identity.dominant_pressure
    elif snapshot.civil_war_context is not None:
        floor_pressure = (
            snapshot.civil_war_context.dangerous_branches[0]
            if snapshot.civil_war_context.dangerous_branches
            else snapshot.civil_war_context.thesis
        )
    elif snapshot.successor_options and snapshot.successor_options.threat_profile:
        floor_pressure = snapshot.successor_options.threat_profile[0]
    elif snapshot.floor_summary and snapshot.floor_summary.heir_pressure:
        heir_pressure = snapshot.floor_summary.heir_pressure
        floor_pressure = heir_pressure.future_threats[0].name if heir_pressure.future_threats else heir_pressure.branch_doctrine

    lineage_direction = lineage_direction_forming()
    if floor_identity is not None:
        lineage_direction = floor_identity.lineage_direction
    elif snapshot.successor_options and snapshot.successor_options.lineage_doctrine:
        lineage_direction = snapshot.successor_options.lineage_doctrine
    elif snapshot.floor_summary and snapshot.floor_summary.heir_pressure:
        lineage_direction = snapshot.floor_summary.heir_pressure.branch_doctrine

    if snapshot.current_phase == "civil_war":
        immediate_posture = risk_posture_civil_war()
    elif snapshot.successor_options and snapshot.successor_options.civil_war_pressure:
        immediate_posture = risk_posture_named(pressure=snapshot.successor_options.civil_war_pressure)
    elif central_rival and central_rival.has_civil_war_danger:
        immediate_posture = risk_posture_instability()
    elif central_rival and central_rival.has_successor_pressure:
        immediate_posture = stability_posture_contested()
    else:
        immediate_posture = stability_posture_controlled()

    pressure_cause = None
    if floor_identity is not None:
        pressure_cause = floor_identity.pressure_reason
    elif central_rival and central_rival.has_civil_war_danger:
        pressure_cause = central_rival.civil_war_danger_cause
    elif central_rival and central_rival.has_successor_pressure:
        pressure_cause = central_rival.successor_pressure_cause

    civil_war_signal = None
    if snapshot.civil_war_context is not None and snapshot.civil_war_context.doctrine_pressure:
        civil_war_signal = snapshot.civil_war_context.doctrine_pressure[0]

    doctrine_chip, doctrine_detail = doctrine_commitment_summary(
        house=snapshot.house_doctrine_family,
        primary=snapshot.primary_doctrine_family,
        secondary=snapshot.secondary_doctrine_family,
    )

    headline = strategic_snapshot_headline(
        host_name=host_name,
        floor_number=floor_number,
        civil_war=snapshot.current_phase == "civil_war",
    )
    rival_name = strategic_snapshot_rival_name(rival_name=central_rival.name if central_rival is not None else None)
    rival_signal = strategic_snapshot_rival_signal(
        rival_signal=central_rival.doctrine_signal if central_rival is not None else None
    )

    return StrategicSnapshotState(
        headline=headline,
        chips=[
            strategic_snapshot_rival_chip(rival_name=rival_name),
            strategic_snapshot_pressure_chip(floor_pressure=floor_pressure),
            strategic_snapshot_lineage_chip(lineage_direction=lineage_direction),
            doctrine_chip,
        ],
        details=[
            immediate_posture,
            doctrine_detail,
            strategic_snapshot_rival_detail(rival_signal=rival_signal),
            *([strategic_snapshot_pressure_detail(pressure_cause=pressure_cause)] if pressure_cause else []),
            *([strategic_snapshot_civil_war_detail(civil_war_signal=civil_war_signal)] if civil_war_signal else []),
        ],
    )


def rebuild_dynasty_board(context: DynastyBoardBuildContext) -> DynastyBoardState:
    snapshot = context.snapshot
    player = context.player
    opponent = context.opponent
    successor_candidates = context.successor_candidates

    pressure_names: set[str] = set()
    danger_names: set[str] = set()
    pressure_causes: dict[str, str] = {}
    danger_causes: dict[str, str] = {}
    floor_summary = snapshot.floor_summary
    if floor_summary and floor_summary.heir_pressure:
        pressure_names.update(entry.name for entry in floor_summary.heir_pressure.successor_candidates)
        danger_names.update(entry.name for entry in floor_summary.heir_pressure.future_threats)
        for entry in floor_summary.heir_pressure.successor_candidates:
            pressure_causes[entry.name] = lineage_cause_phrase(entry.shaping_causes, entry.rationale)
        for entry in floor_summary.heir_pressure.future_threats:
            danger_causes[entry.name] = lineage_cause_phrase(entry.shaping_causes, entry.rationale)

    successor_options = snapshot.successor_options
    successor_candidate_views = {candidate.name: candidate for candidate in successor_options.candidates} if successor_options else {}
    if successor_options and successor_options.candidates:
        top_score = max(candidate.score for candidate in successor_options.candidates)
        for candidate in successor_options.candidates:
            if candidate.score == top_score:
                pressure_names.add(candidate.name)
                if candidate.name not in pressure_causes:
                    pressure_causes[candidate.name] = lineage_cause_phrase(candidate.shaping_causes, candidate.succession_pitch)

    entries: list[DynastyBoardEntryView] = []
    floor_entry_by_name = {entry.name: entry for entry in floor_summary.entries} if floor_summary else {}
    if floor_summary and floor_summary.entries:
        for entry in floor_summary.entries:
            doctrine_signal = ", ".join(entry.tags[:2]) if entry.tags else entry.descriptor
            entries.append(
                DynastyBoardEntryView(
                    name=entry.name,
                    role=entry.descriptor,
                    doctrine_signal=doctrine_signal,
                    score=entry.score,
                    wins=entry.wins,
                    lineage_depth=entry.lineage_depth,
                    is_current_host=entry.is_player or entry.name == player.name,
                    has_successor_pressure=entry.name in pressure_names,
                    has_civil_war_danger=entry.name in danger_names,
                    successor_pressure_cause=pressure_causes.get(entry.name),
                    civil_war_danger_cause=danger_causes.get(entry.name),
                    lineage_relation=("host" if entry.name == player.name else entry.lineage_relation),
                    survived_previous_floor=entry.survived_previous_floor,
                    continuity_streak=entry.continuity_streak,
                    score_delta=entry.score_delta,
                    wins_delta=entry.wins_delta,
                    pressure_trend=entry.pressure_trend,
                    is_central_rival=entry.name == context.current_floor_central_rival,
                    is_new_central_rival=entry.name == context.current_floor_new_central_rival,
                )
            )
    elif snapshot.successor_options and successor_candidates:
        branch_pool = list(successor_candidates)
        if all(agent.name != player.name for agent in branch_pool):
            branch_pool.append(player)
        for agent in branch_pool:
            identity = analyze_agent_identity(agent)
            doctrine_signal = ", ".join(identity.tags[:2]) if identity.tags else identity.descriptor
            entries.append(
                DynastyBoardEntryView(
                    name=agent.name,
                    role=identity.descriptor,
                    doctrine_signal=doctrine_signal,
                    score=agent.score,
                    wins=agent.wins,
                    lineage_depth=agent.lineage_depth,
                    is_current_host=agent.is_player or agent.name == player.name,
                    has_successor_pressure=agent.name in pressure_names,
                    has_civil_war_danger=agent.name in danger_names,
                    successor_pressure_cause=pressure_causes.get(agent.name),
                    civil_war_danger_cause=danger_causes.get(agent.name),
                    lineage_relation=(
                        floor_entry_by_name[agent.name].lineage_relation
                        if agent.name in floor_entry_by_name
                        else (
                            "host"
                            if (agent.is_player or agent.name == player.name)
                            else ("kin" if player.lineage_id is not None and agent.lineage_id == player.lineage_id else "outsider")
                        )
                    ),
                    survived_previous_floor=(floor_entry_by_name[agent.name].survived_previous_floor if agent.name in floor_entry_by_name else False),
                    continuity_streak=(floor_entry_by_name[agent.name].continuity_streak if agent.name in floor_entry_by_name else 1),
                    score_delta=(floor_entry_by_name[agent.name].score_delta if agent.name in floor_entry_by_name else 0),
                    wins_delta=(floor_entry_by_name[agent.name].wins_delta if agent.name in floor_entry_by_name else 0),
                    pressure_trend=(floor_entry_by_name[agent.name].pressure_trend if agent.name in floor_entry_by_name else "steady"),
                    is_central_rival=agent.name == context.current_floor_central_rival,
                    is_new_central_rival=agent.name == context.current_floor_new_central_rival,
                )
            )
    else:
        for agent in (player, opponent):
            identity = analyze_agent_identity(agent)
            doctrine_signal = ", ".join(identity.tags[:2]) if identity.tags else identity.descriptor
            entries.append(
                DynastyBoardEntryView(
                    name=agent.name,
                    role=identity.descriptor,
                    doctrine_signal=doctrine_signal,
                    score=agent.score,
                    wins=agent.wins,
                    lineage_depth=agent.lineage_depth,
                    is_current_host=agent.is_player,
                    has_successor_pressure=False,
                    has_civil_war_danger=False,
                    successor_pressure_cause=None,
                    civil_war_danger_cause=None,
                    lineage_relation=("host" if agent.is_player else ("kin" if player.lineage_id is not None and agent.lineage_id == player.lineage_id else "outsider")),
                    survived_previous_floor=False,
                    continuity_streak=1,
                    score_delta=0,
                    wins_delta=0,
                    pressure_trend="steady",
                    is_central_rival=agent.name == context.current_floor_central_rival,
                    is_new_central_rival=agent.name == context.current_floor_new_central_rival,
                )
            )

    if snapshot.current_phase == "civil_war":
        threat_tags = set((snapshot.successor_options and snapshot.successor_options.threat_profile) or [])
        for idx, board_entry in enumerate(entries):
            candidate = next((agent for agent in successor_candidates if agent.name == board_entry.name), None)
            if candidate is None:
                continue
            tags = set(analyze_agent_identity(candidate).tags)
            if tags & threat_tags:
                existing_cause = entries[idx].civil_war_danger_cause
                candidate_view = successor_candidate_views.get(candidate.name)
                danger_cause = existing_cause or lineage_cause_phrase(
                    candidate_view.shaping_causes if candidate_view else [],
                    candidate_view.danger_later if candidate_view else "civil-war threat tags are active",
                )
                entries[idx] = DynastyBoardEntryView(
                    name=board_entry.name,
                    role=board_entry.role,
                    doctrine_signal=board_entry.doctrine_signal,
                    score=board_entry.score,
                    wins=board_entry.wins,
                    lineage_depth=board_entry.lineage_depth,
                    is_current_host=board_entry.is_current_host,
                    has_successor_pressure=board_entry.has_successor_pressure,
                    has_civil_war_danger=True,
                    successor_pressure_cause=board_entry.successor_pressure_cause,
                    civil_war_danger_cause=danger_cause,
                    lineage_relation=board_entry.lineage_relation,
                    survived_previous_floor=board_entry.survived_previous_floor,
                    continuity_streak=board_entry.continuity_streak,
                    score_delta=board_entry.score_delta,
                    wins_delta=board_entry.wins_delta,
                    pressure_trend=board_entry.pressure_trend,
                    is_central_rival=board_entry.is_central_rival,
                    is_new_central_rival=board_entry.is_new_central_rival,
                )

    entries.sort(key=lambda entry: (-entry.score, entry.name, entry.lineage_depth))
    return DynastyBoardState(phase=snapshot.current_phase, entries=entries)
