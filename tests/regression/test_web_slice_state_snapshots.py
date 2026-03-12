from __future__ import annotations

from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

from support.session_driver import advance_through_transition_and_complete, play_until_floor_summary


def test_regression_snapshot_at_floor_summary_is_structured_and_stable() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    play_until_floor_summary(session)

    snapshot = session.view()["snapshot"]
    summary = snapshot["floor_summary"]
    assert {
        "current_phase": snapshot["current_phase"],
        "current_floor": snapshot["current_floor"],
        "session_status": snapshot["session_status"],
        "summary_floor": summary["floor_number"],
        "entry_names": [entry["name"] for entry in summary["entries"]],
        "vote_result": snapshot["floor_vote_result"],
    } == {
        "current_phase": "ecosystem",
        "current_floor": 1,
        "session_status": "running",
        "summary_floor": 1,
        "entry_names": ["You", "Echo Branch", "Delta Branch"],
        "vote_result": {
            "floor_number": 1,
            "cooperation_prevailed": True,
            "cooperators": 6,
            "defectors": 2,
            "player_vote": 0,
            "player_reward": 2,
        },
    }


def test_regression_snapshot_at_completion_preserves_run_contract() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    play_until_floor_summary(session)
    session.advance()
    advance_through_transition_and_complete(session)

    view = session.view()
    snapshot = view["snapshot"]
    assert view["status"] == "completed"
    assert {
        "phase": snapshot["current_phase"],
        "floor": snapshot["current_floor"],
        "completion": snapshot["completion"],
        "successor_options_count": len(snapshot["successor_options"]["candidates"]),
    } == {
        "phase": "civil_war",
        "floor": 2,
        "completion": {
            "outcome": "victory",
            "floor_number": 2,
            "player_name": "Heir A",
            "seed": 7,
        },
        "successor_options_count": 2,
    }
