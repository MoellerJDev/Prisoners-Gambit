from __future__ import annotations

import pytest

from prisoners_gambit.core.constants import DEFECT
from prisoners_gambit.core.interaction import ChooseSuccessorAction

from support.builders import build_seeded_session
from support.session_driver import (
    advance_through_transition_and_complete,
    play_until_floor_summary,
    reach_successor_choice,
)


@pytest.mark.parametrize("seed", [7, 21, 41, 77, 99])
def test_seeded_floor_progression_slice_reaches_floor_summary(seed: int) -> None:
    session = build_seeded_session(seed=seed, rounds=2)
    play_until_floor_summary(session, featured_mode="manual_cooperate")

    view = session.view()
    assert view["pending_screen"] == "floor_summary"
    assert view["snapshot"]["floor_summary"] is not None
    assert view["snapshot"]["floor_vote_result"] is not None


@pytest.mark.parametrize("seed", [11, 41, 88])
def test_seeded_successor_choice_slice_promotes_selected_candidate(seed: int) -> None:
    session = build_seeded_session(seed=seed, rounds=2)
    reach_successor_choice(session)

    first_candidate = session.view()["decision"]["candidates"][0]["name"]
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    view = session.view()
    assert view["pending_screen"] is None
    assert view["snapshot"]["current_phase"] == "ecosystem"
    assert view["snapshot"]["current_floor"] == 1
    assert view["decision_type"] == "PowerupChoiceState"
    assert view["snapshot"]["completion"] is None
    assert session.player.name == first_candidate


@pytest.mark.parametrize("seed", [41, 123])
def test_seeded_alternate_successor_path_chooses_second_candidate(seed: int) -> None:
    session = build_seeded_session(seed=seed, rounds=2)
    reach_successor_choice(session)

    candidates = session.view()["decision"]["candidates"]
    assert len(candidates) >= 2
    chosen_name = candidates[1]["name"]

    session.submit_action(ChooseSuccessorAction(candidate_index=1))
    session.advance()

    assert session.player.name == chosen_name
    assert session.view()["snapshot"]["current_phase"] == "ecosystem"


@pytest.mark.parametrize("seed", [77, 178])
def test_seeded_autopilot_match_slice_reaches_summary(seed: int) -> None:
    session = build_seeded_session(seed=seed, rounds=3)
    play_until_floor_summary(session, featured_mode="autopilot_match")

    snapshot = session.view()["snapshot"]
    assert snapshot["latest_featured_round"] is not None
    assert snapshot["latest_featured_round"]["round_index"] == 2
    assert session.view()["pending_screen"] == "floor_summary"


@pytest.mark.parametrize("seed", [88, 111])
def test_seeded_stance_slice_reaches_summary_with_active_stance_history(seed: int) -> None:
    session = build_seeded_session(seed=seed, rounds=3)
    play_until_floor_summary(session, featured_mode="stance_follow_autopilot")

    snapshot = session.view()["snapshot"]
    assert snapshot["latest_featured_round"] is not None
    assert snapshot["floor_vote_result"] is not None


def test_seeded_defect_vote_path_changes_vote_summary_shape() -> None:
    session = build_seeded_session(seed=61, rounds=2)
    play_until_floor_summary(session, featured_mode="manual_cooperate", floor_vote=DEFECT)

    vote = session.view()["snapshot"]["floor_vote_result"]
    assert vote["player_vote"] == DEFECT
    assert vote["cooperation_prevailed"] is False
    assert vote["defectors"] > vote["cooperators"]


@pytest.mark.parametrize("seed,candidate_index", [(41, 1), (99, 0)])
def test_seeded_completion_slice_finishes_for_multiple_paths(seed: int, candidate_index: int) -> None:
    session = build_seeded_session(seed=seed, rounds=2)
    reach_successor_choice(session)
    session.snapshot.floor_summary.heir_pressure.future_threats = []
    advance_through_transition_and_complete(session, candidate_index=candidate_index)

    completion = session.view()["snapshot"]["completion"]
    assert completion is not None
    assert completion["outcome"] in {"victory", "eliminated"}
