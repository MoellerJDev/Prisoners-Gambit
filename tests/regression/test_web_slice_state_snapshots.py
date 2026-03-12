from __future__ import annotations

"""Regression contracts for web-slice state.

These tests intentionally validate stable semantics and structure rather than freezing
incidental content (exact names/order text) that may evolve during balancing.
"""

from support.builders import build_seeded_session
from support.session_driver import advance_through_transition_and_complete, play_until_floor_summary, reach_successor_choice


REQUIRED_COMPLETION_KEYS = {"outcome", "floor_number", "player_name", "seed"}
REQUIRED_SUMMARY_ENTRY_KEYS = {"agent_id", "name", "is_player", "score", "wins", "lineage_depth", "tags", "descriptor", "genome_summary", "powerups"}
REQUIRED_VOTE_KEYS = {"floor_number", "cooperation_prevailed", "cooperators", "defectors", "player_vote", "player_reward"}
REQUIRED_SUCCESSOR_KEYS = {
    "name",
    "lineage_depth",
    "branch_role",
    "tradeoffs",
    "strengths",
    "liabilities",
    "lineage_future",
    "succession_pitch",
    "succession_risk",
    "anti_score_note",
}


def test_regression_floor_summary_snapshot_contract_shape() -> None:
    session = build_seeded_session(seed=7, rounds=1)
    play_until_floor_summary(session)

    snapshot = session.view()["snapshot"]
    summary = snapshot["floor_summary"]
    vote = snapshot["floor_vote_result"]

    assert snapshot["current_phase"] == "ecosystem"
    assert snapshot["current_floor"] == 1
    assert snapshot["session_status"] == "running"

    assert isinstance(summary, dict)
    assert summary["floor_number"] == snapshot["current_floor"]
    assert len(summary["entries"]) >= 2
    assert sum(1 for entry in summary["entries"] if entry["is_player"]) == 1
    for entry in summary["entries"]:
        assert REQUIRED_SUMMARY_ENTRY_KEYS.issubset(entry.keys())
        assert isinstance(entry["score"], int)
        assert isinstance(entry["wins"], int)

    assert isinstance(vote, dict)
    assert REQUIRED_VOTE_KEYS.issubset(vote.keys())
    assert vote["cooperators"] + vote["defectors"] > 0


def test_regression_successor_transition_payload_contract() -> None:
    session = build_seeded_session(seed=7, rounds=1)
    reach_successor_choice(session)

    decision = session.view()["decision"]
    assert decision is not None
    assert decision["floor_number"] == session.view()["snapshot"]["current_floor"]
    assert len(decision["candidates"]) >= 1
    assert {"current_phase", "lineage_doctrine", "threat_profile", "civil_war_pressure"}.issubset(decision.keys())

    candidate = decision["candidates"][0]
    assert REQUIRED_SUCCESSOR_KEYS.issubset(candidate.keys())

    from prisoners_gambit.core.interaction import ChooseSuccessorAction

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    snapshot = session.view()["snapshot"]
    assert session.view()["pending_screen"] == "civil_war_transition"
    assert snapshot["current_phase"] == "civil_war"
    assert snapshot["current_floor"] == 2


def test_regression_completion_snapshot_contract() -> None:
    session = build_seeded_session(seed=7, rounds=1)
    reach_successor_choice(session)
    advance_through_transition_and_complete(session, candidate_index=0)

    view = session.view()
    snapshot = view["snapshot"]
    completion = snapshot["completion"]

    assert view["status"] == "completed"
    assert isinstance(completion, dict)
    assert REQUIRED_COMPLETION_KEYS.issubset(completion.keys())
    assert completion["outcome"] in {"victory", "eliminated"}
    assert completion["floor_number"] == snapshot["current_floor"]
    assert completion["seed"] == 7
    assert completion["player_name"]
