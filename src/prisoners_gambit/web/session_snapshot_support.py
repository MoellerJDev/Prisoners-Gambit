from __future__ import annotations

from prisoners_gambit.core.analysis import analyze_agent_identity
from prisoners_gambit.core.interaction import DynastyBoardEntryView, DynastyBoardState, StrategicSnapshotState
from prisoners_gambit.core.models import Agent


def lineage_cause_phrase(shaping_causes: list[str], fallback: str) -> str:
    lead = shaping_causes[0] if shaping_causes else fallback
    compact = lead.strip().rstrip(".")
    return f"because {compact}"


def refresh_strategic_snapshot(snapshot, *, player_name: str, floor_number: int) -> StrategicSnapshotState:
    def _pick(source, attr: str, default=None):
        if source is None:
            return default
        if hasattr(source, attr):
            return getattr(source, attr)
        if isinstance(source, dict):
            return source.get(attr, default)
        return default

    host_name = player_name
    floor_identity = snapshot.floor_identity
    identity_target_floor = _pick(floor_identity, "target_floor")
    identity_host_name = _pick(floor_identity, "host_name")
    if identity_target_floor == floor_number and identity_host_name:
        host_name = identity_host_name

    dynasty_board = snapshot.dynasty_board
    board_entries = list(_pick(dynasty_board, "entries", []))
    central_rival = next(
        (
            entry
            for entry in board_entries
            if (entry.is_central_rival if hasattr(entry, "is_central_rival") else entry.get("is_central_rival", False))
        ),
        None,
    )

    floor_pressure = "Floor pressure unresolved"
    if floor_identity is not None:
        floor_pressure = _pick(floor_identity, "dominant_pressure", floor_pressure)
    elif snapshot.civil_war_context is not None:
        dangerous_branches = list(_pick(snapshot.civil_war_context, "dangerous_branches", []))
        floor_pressure = dangerous_branches[0] if dangerous_branches else _pick(snapshot.civil_war_context, "thesis", floor_pressure)
    elif snapshot.successor_options and _pick(snapshot.successor_options, "threat_profile"):
        floor_pressure = _pick(snapshot.successor_options, "threat_profile", [floor_pressure])[0]
    elif snapshot.floor_summary and _pick(snapshot.floor_summary, "heir_pressure"):
        heir_pressure = _pick(snapshot.floor_summary, "heir_pressure")
        future_threats = list(_pick(heir_pressure, "future_threats", []))
        floor_pressure = _pick(future_threats[0], "name") if future_threats else _pick(heir_pressure, "branch_doctrine", floor_pressure)

    lineage_direction = "Lineage direction forming"
    if floor_identity is not None:
        lineage_direction = _pick(floor_identity, "lineage_direction", lineage_direction)
    elif snapshot.successor_options and _pick(snapshot.successor_options, "lineage_doctrine"):
        lineage_direction = _pick(snapshot.successor_options, "lineage_doctrine", lineage_direction)
    elif snapshot.floor_summary and _pick(snapshot.floor_summary, "heir_pressure"):
        lineage_direction = _pick(_pick(snapshot.floor_summary, "heir_pressure"), "branch_doctrine", lineage_direction)

    if snapshot.current_phase == "civil_war":
        immediate_posture = "Risk posture: coercive pressure"
    elif snapshot.successor_options and _pick(snapshot.successor_options, "civil_war_pressure"):
        immediate_posture = f"Risk posture: {_pick(snapshot.successor_options, 'civil_war_pressure')}"
    elif central_rival and (central_rival.has_civil_war_danger if hasattr(central_rival, "has_civil_war_danger") else central_rival.get("has_civil_war_danger", False)):
        immediate_posture = "Risk posture: instability rising"
    elif central_rival and (central_rival.has_successor_pressure if hasattr(central_rival, "has_successor_pressure") else central_rival.get("has_successor_pressure", False)):
        immediate_posture = "Stability posture: contested succession"
    else:
        immediate_posture = "Stability posture: controlled"

    headline = f"Host {host_name} · F{floor_number}"
    if snapshot.current_phase == "civil_war":
        headline = f"Host {host_name} · Civil-war floor F{floor_number}"

    rival_name = "none"
    rival_signal = "waiting for floor ranking"
    if central_rival is not None:
        rival_name = central_rival.name if hasattr(central_rival, "name") else str(central_rival.get("name", "none"))
        rival_signal = central_rival.doctrine_signal if hasattr(central_rival, "doctrine_signal") else str(central_rival.get("doctrine_signal", "waiting for floor ranking"))

    chips = [
        f"Rival: {rival_name}",
        f"Pressure: {floor_pressure}",
        f"Lineage: {lineage_direction}",
    ]
    details = [
        immediate_posture,
        f"Central rival signal: {rival_signal}",
    ]
    return StrategicSnapshotState(
        headline=headline,
        chips=chips,
        details=details,
    )


def rebuild_dynasty_board(
    snapshot,
    *,
    player: Agent,
    opponent: Agent,
    successor_candidates: list[Agent],
    current_floor_central_rival: str | None,
    current_floor_new_central_rival: str | None,
) -> DynastyBoardState:
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
    if snapshot.successor_options and successor_candidates:
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
                    is_central_rival=agent.name == current_floor_central_rival,
                    is_new_central_rival=agent.name == current_floor_new_central_rival,
                )
            )
    elif floor_summary and floor_summary.entries:
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
                    is_current_host=entry.is_player,
                    has_successor_pressure=entry.name in pressure_names,
                    has_civil_war_danger=entry.name in danger_names,
                    successor_pressure_cause=pressure_causes.get(entry.name),
                    civil_war_danger_cause=danger_causes.get(entry.name),
                    lineage_relation=getattr(entry, "lineage_relation", "host" if entry.is_player else "outsider"),
                    survived_previous_floor=getattr(entry, "survived_previous_floor", False),
                    continuity_streak=getattr(entry, "continuity_streak", 1),
                    score_delta=getattr(entry, "score_delta", 0),
                    wins_delta=getattr(entry, "wins_delta", 0),
                    pressure_trend=getattr(entry, "pressure_trend", "steady"),
                    is_central_rival=entry.name == current_floor_central_rival,
                    is_new_central_rival=entry.name == current_floor_new_central_rival,
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
                    is_central_rival=agent.name == current_floor_central_rival,
                    is_new_central_rival=agent.name == current_floor_new_central_rival,
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
