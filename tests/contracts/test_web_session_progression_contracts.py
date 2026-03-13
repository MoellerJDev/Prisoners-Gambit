from __future__ import annotations

import pytest

from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import (
    ChoosePowerupAction,
    ChooseRoundMoveAction,
    ChooseSuccessorAction,
)
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

from support.session_driver import (
    advance_through_transition_and_complete,
    decision_type,
    pending_screen,
    reach_successor_choice,
    session_milestone,
)


def _decision_sequence_to_floor_summary(session: FeaturedMatchWebSession) -> list[str]:
    sequence: list[str] = [session_milestone(session)]
    while decision_type(session) == "FeaturedRoundDecisionState":
        session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
        session.advance()
        sequence.append(session_milestone(session))

    assert decision_type(session) == "FloorVoteDecisionState"
    from prisoners_gambit.core.interaction import ChooseFloorVoteAction

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    sequence.append(session_milestone(session))
    return sequence


def test_contract_featured_round_to_floor_summary_transition_order() -> None:
    session = FeaturedMatchWebSession(seed=21, rounds=2)
    session.start()

    sequence = _decision_sequence_to_floor_summary(session)

    assert sequence[0] == "featured_round_decision"
    assert "floor_vote_decision" in sequence
    assert sequence[-1] == "floor_summary_pending"
    assert pending_screen(session) == "floor_summary"
    snapshot = session.view()["snapshot"]
    assert snapshot["latest_featured_round"] is not None
    assert snapshot["floor_vote_result"] is not None
    assert snapshot["floor_summary"] is not None


def test_contract_successor_transition_then_offer_flow() -> None:
    session = FeaturedMatchWebSession(seed=21, rounds=2)
    session.start()
    reach_successor_choice(session)

    assert session_milestone(session) == "successor_choice_decision"
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    assert session_milestone(session) == "powerup_choice_decision"
    assert pending_screen(session) is None
    assert session.view()["snapshot"]["current_phase"] == "ecosystem"
    assert decision_type(session) == "PowerupChoiceState"


def test_contract_completion_flow_semantics() -> None:
    session = FeaturedMatchWebSession(seed=21, rounds=2)
    session.start()
    reach_successor_choice(session)
    session.snapshot.floor_summary.heir_pressure.future_threats = []

    advance_through_transition_and_complete(session, candidate_index=0)

    view = session.view()
    completion = view["snapshot"]["completion"]
    assert view["status"] == "completed"
    assert session_milestone(session) == "completed"
    assert completion is not None
    assert completion["outcome"] in {"victory", "eliminated"}
    assert completion["floor_number"] == view["snapshot"]["current_floor"]


def test_contract_rejects_wrong_action_type_for_current_state() -> None:
    session = FeaturedMatchWebSession(seed=21, rounds=2)
    session.start()

    with pytest.raises(ValueError, match="Invalid action type"):
        session.submit_action(ChooseSuccessorAction(candidate_index=0))


def test_contract_rejects_wrong_state_action_submission_after_transition() -> None:
    session = FeaturedMatchWebSession(seed=21, rounds=2)
    session.start()
    reach_successor_choice(session)
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    assert decision_type(session) == "PowerupChoiceState"
    with pytest.raises(ValueError, match="Invalid action type"):
        session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
