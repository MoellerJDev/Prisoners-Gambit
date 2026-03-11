from prisoners_gambit.app.interaction_controller import RunSession
from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseRoundMoveAction,
    FeaturedMatchPrompt,
    FeaturedRoundDecisionState,
    RunCompletion,
    RunSnapshot,
)


def _round_state() -> FeaturedRoundDecisionState:
    return FeaturedRoundDecisionState(
        prompt=FeaturedMatchPrompt(
            floor_number=1,
            masked_opponent_label="Unknown",
            round_index=0,
            total_rounds=3,
            my_history=[],
            opp_history=[],
            my_match_score=0,
            opp_match_score=0,
            suggested_move=COOPERATE,
            roster_entries=[],
        )
    )


def test_session_advances_to_awaiting_decision_state() -> None:
    session = RunSession()
    snap = RunSnapshot()
    session.start(snap)

    decision = _round_state()
    session.begin_decision(decision, (ChooseRoundMoveAction,), snap)

    assert session.status == "awaiting_decision"
    assert session.current_decision == decision


def test_session_submit_action_and_resume() -> None:
    session = RunSession()
    snap = RunSnapshot()
    session.start(snap)

    session.begin_decision(_round_state(), (ChooseRoundMoveAction,), snap)
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    resolved = session.resolve_current_decision(lambda _: ChooseRoundMoveAction(mode="manual_move", move=0))

    assert isinstance(resolved, ChooseRoundMoveAction)
    assert resolved.move == COOPERATE
    assert session.status == "running"
    assert session.current_decision is None


def test_session_handles_multiple_consecutive_decisions() -> None:
    session = RunSession()
    snap = RunSnapshot()
    session.start(snap)

    for _ in range(2):
        session.begin_decision(_round_state(), (ChooseRoundMoveAction,), snap)
        resolved = session.resolve_current_decision(
            lambda _: ChooseRoundMoveAction(mode="manual_move", move=COOPERATE)
        )
        assert resolved.move == COOPERATE
        assert session.status == "running"


def test_completed_session_behavior() -> None:
    session = RunSession()
    snap = RunSnapshot()
    session.start(snap)
    completion = RunCompletion(outcome="victory", floor_number=4, player_name="You", seed=1)

    session.complete(completion, snap)

    assert session.status == "completed"
    assert session.completion == completion


def test_invalid_action_rejected_for_wrong_decision_type() -> None:
    session = RunSession()
    snap = RunSnapshot()
    session.start(snap)

    session.begin_decision(_round_state(), (ChooseRoundMoveAction,), snap)

    try:
        session.submit_action(ChooseFloorVoteAction(mode="autopilot_vote"))
        assert False, "Expected ValueError for wrong action type"
    except ValueError:
        pass


def test_session_clears_stale_queued_action_when_new_decision_begins() -> None:
    session = RunSession()
    snap = RunSnapshot()
    session.start(snap)

    session.begin_decision(_round_state(), (ChooseRoundMoveAction,), snap)
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    # Starting a new decision discards the stale queued action.
    session.begin_decision(_round_state(), (ChooseFloorVoteAction,), snap)

    resolved = session.resolve_current_decision(lambda _: ChooseFloorVoteAction(mode="autopilot_vote"))
    assert isinstance(resolved, ChooseFloorVoteAction)
    assert resolved.mode == "autopilot_vote"
