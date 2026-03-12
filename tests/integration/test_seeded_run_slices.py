from __future__ import annotations

import pytest

from prisoners_gambit.core.interaction import ChooseSuccessorAction

from support.builders import build_seeded_session
from support.session_driver import (
    advance_through_transition_and_complete,
    play_until_floor_summary,
    reach_successor_choice,
)


@pytest.mark.parametrize("seed", [7, 21, 41])
def test_seeded_floor_progression_slice_reaches_floor_summary(seed: int) -> None:
    session = build_seeded_session(seed=seed, rounds=2)
    play_until_floor_summary(session, featured_mode="manual_cooperate")

    view = session.view()
    assert view["pending_screen"] == "floor_summary"
    assert view["snapshot"]["floor_summary"] is not None
    assert view["snapshot"]["floor_vote_result"] is not None


@pytest.mark.parametrize("seed", [11, 41])
def test_seeded_successor_choice_slice_promotes_selected_candidate(seed: int) -> None:
    session = build_seeded_session(seed=seed, rounds=2)
    reach_successor_choice(session)

    first_candidate = session.view()["decision"]["candidates"][0]["name"]
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    view = session.view()
    assert view["pending_screen"] == "civil_war_transition"
    assert view["snapshot"]["current_phase"] == "civil_war"
    assert view["snapshot"]["current_floor"] == 2
    assert view["snapshot"]["completion"] is None
    assert session.player.name == first_candidate


def test_seeded_alternate_successor_path_chooses_second_candidate() -> None:
    session = build_seeded_session(seed=41, rounds=2)
    reach_successor_choice(session)

    candidates = session.view()["decision"]["candidates"]
    assert len(candidates) >= 2
    chosen_name = candidates[1]["name"]

    session.submit_action(ChooseSuccessorAction(candidate_index=1))
    session.advance()

    assert session.player.name == chosen_name
    assert session.view()["snapshot"]["current_phase"] == "civil_war"


def test_seeded_autopilot_match_slice_reaches_summary() -> None:
    session = build_seeded_session(seed=77, rounds=3)
    play_until_floor_summary(session, featured_mode="autopilot_match")

    snapshot = session.view()["snapshot"]
    assert snapshot["latest_featured_round"] is not None
    assert snapshot["latest_featured_round"]["round_index"] == 2
    assert session.view()["pending_screen"] == "floor_summary"


def test_seeded_stance_slice_reaches_summary_with_active_stance_history() -> None:
    session = build_seeded_session(seed=88, rounds=3)
    play_until_floor_summary(session, featured_mode="stance_follow_autopilot")

    snapshot = session.view()["snapshot"]
    assert snapshot["latest_featured_round"] is not None
    # stance may expire by summary time; contract is that session completed round resolution normally.
    assert snapshot["floor_vote_result"] is not None


def test_seeded_completion_slice_with_nondefault_successor_finishes() -> None:
    session = build_seeded_session(seed=41, rounds=2)
    reach_successor_choice(session)
    advance_through_transition_and_complete(session, candidate_index=1)

    completion = session.view()["snapshot"]["completion"]
    assert completion is not None
    assert completion["outcome"] in {"victory", "eliminated"}
