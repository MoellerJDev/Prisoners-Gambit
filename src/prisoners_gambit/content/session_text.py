from __future__ import annotations

from collections.abc import Sequence


# This module is the main edit surface for backend-generated session and
# chronicle copy that is not already sourced from the web i18n bundle.

UNKNOWN_OPPONENT_LABEL = "Unknown Opponent"
CIVIL_WAR_RIVAL_NAME = "Civil War Rival"

TRANSITION_ACTION_LABELS: dict[str, str] = {
    "successor_review": "Review successor options",
    "reward_selection": "Continue to reward selection",
    "civil_war_start": "Start civil-war round",
    "generic": "Continue to next phase",
}

PRESSURE_LABELS: dict[str, str] = {
    "high": "Containment floor",
    "rising": "Pressure-test floor",
    "low": "Expansion floor",
}


def transition_action_label(kind: str) -> str:
    return TRANSITION_ACTION_LABELS.get(kind, TRANSITION_ACTION_LABELS["generic"])


def pending_floor_complete_message(*, floor_number: int, next_step_label: str) -> str:
    return f"Floor {floor_number} complete. {next_step_label}."


def pending_civil_war_start_message(*, thesis: str) -> str:
    return f"{thesis} Start the civil-war round."


def featured_round_clue_channels(*, public_profile: str, powerup_names: Sequence[str]) -> list[str]:
    return [
        f"Profile signal: {public_profile}",
        f"Known powerups: {', '.join(powerup_names) if powerup_names else 'none'}",
        "Pattern signal: compare opening behavior and retaliation cadence.",
    ]


def featured_round_inference_focus() -> str:
    return "Opening read: stress-test the clue channels before you trust the line."


def featured_round_pattern_focus() -> str:
    return "Pattern read: update tag confidence from the response line."


def run_start_summary(*, seed: int) -> str:
    return f"Run started (seed {seed}) in ecosystem play."


def no_solid_clue_read_this_floor() -> str:
    return "No solid clue read survived this floor."


def unclear_playstyle_trend() -> str:
    return "Playstyle trend is unclear."


def floor_complete_summary(*, floor_number: int, player_score: int, featured_note: str) -> str:
    return f"Floor {floor_number} ended at {player_score} points. {featured_note}"


def doctrine_shift_summary(*, doctrine_note: str, doctrine_chip: str) -> str:
    return f"Lineage trend: {doctrine_note}. {doctrine_chip}"


def successor_pressure_summary(*, civil_war_pressure: str, threat_tags: Sequence[str]) -> str:
    threat_list = ", ".join(sorted(threat_tags)) or "none"
    return f"Succession pressure is {civil_war_pressure}; top threats: {threat_list}."


def successor_pressure_cause_fallback(*, threat_tags: Sequence[str]) -> str:
    return f"threat mix {', '.join(sorted(threat_tags)) or 'none'}"


def host_shift_summary(*, previous_host: str, chosen_name: str) -> str:
    return f"Host shifted from {previous_host} to {chosen_name}."


def host_hold_summary(*, host_name: str) -> str:
    return f"Host held by {host_name}."


def civil_war_started_summary(*, thesis: str) -> str:
    return f"Civil war started: {thesis}"


def civil_war_started_fallback() -> str:
    return "civil-war pressure forces a direct duel"


def civil_war_round_start_summary(*, opponent_name: str) -> str:
    return f"Civil-war round started against {opponent_name}."


def ecosystem_floor_start_summary(*, floor_number: int, identity_note: str) -> str:
    return f"Floor {floor_number} started in ecosystem play.{identity_note}"


def run_outcome_summary(*, outcome: str, floor_number: int, player_name: str) -> str:
    return f"Run ended in {outcome} on floor {floor_number} as {player_name}."


def lineage_cause_phrase(*, lead: str) -> str:
    compact = lead.strip().rstrip(".")
    return f"because {compact}"


def floor_pressure_unresolved() -> str:
    return "Floor pressure unresolved"


def lineage_direction_forming() -> str:
    return "Lineage direction still forming"


def risk_posture_civil_war() -> str:
    return "Risk posture: civil-war pressure is active"


def risk_posture_named(*, pressure: str) -> str:
    return f"Risk posture: {pressure}"


def risk_posture_instability() -> str:
    return "Risk posture: instability is rising"


def stability_posture_contested() -> str:
    return "Stability posture: succession is contested"


def stability_posture_controlled() -> str:
    return "Stability posture: controlled"


def strategic_snapshot_headline(*, host_name: str, floor_number: int, civil_war: bool) -> str:
    if civil_war:
        return f"Host {host_name} - Civil-war floor F{floor_number}"
    return f"Host {host_name} - F{floor_number}"


def strategic_snapshot_rival_name(*, rival_name: str | None) -> str:
    return rival_name or "none"


def strategic_snapshot_rival_signal(*, rival_signal: str | None) -> str:
    return rival_signal or "waiting for floor ranking"


def strategic_snapshot_rival_chip(*, rival_name: str) -> str:
    return f"Rival: {rival_name}"


def strategic_snapshot_pressure_chip(*, floor_pressure: str) -> str:
    return f"Pressure: {floor_pressure}"


def strategic_snapshot_lineage_chip(*, lineage_direction: str) -> str:
    return f"Lineage: {lineage_direction}"


def strategic_snapshot_rival_detail(*, rival_signal: str) -> str:
    return f"Central rival signal: {rival_signal}"


def strategic_snapshot_pressure_detail(*, pressure_cause: str) -> str:
    return f"Why dangerous now: {pressure_cause}"


def strategic_snapshot_civil_war_detail(*, civil_war_signal: str) -> str:
    return f"Civil-war buildup: {civil_war_signal}"


def floor_pressure_label(level: str | None) -> str:
    return PRESSURE_LABELS.get(level or "", "Lineage floor")


def dominant_pressure_fallback() -> str:
    return "no dominant threat tag"


def heir_tag_fallback() -> str:
    return "untyped"


def lineage_direction_text(*, doctrine: str) -> str:
    return f"Doctrine path: {doctrine}"


def floor_identity_pressure_reason(*, dominant_pressure: str, focus_name: str, focus_role: str, chosen_name: str) -> str:
    return f"{dominant_pressure} pressure via {focus_name} ({focus_role}) under {chosen_name}."


def floor_identity_focus(*, chosen_name: str, attractive_focus: str, danger_focus: str) -> str:
    return f"Push {chosen_name.lower()}: {attractive_focus}; hedge {danger_focus}."


def floor_identity_focus_with_clue(*, base_focus: str, clue_focus: str) -> str:
    return f"{base_focus[:-1]} Track clue: {clue_focus.lower()}."


def floor_identity_focus_with_cause(*, base_focus: str, cause_focus: str) -> str:
    return f"{base_focus[:-1]} Cause: {cause_focus.lower()}."


def floor_identity_headline(*, pressure_label: str, chosen_name: str, branch_role: str) -> str:
    return f"{pressure_label}: {chosen_name} - {branch_role}"
