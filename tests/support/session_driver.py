from __future__ import annotations

from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundMoveAction,
    ChooseSuccessorAction,
)
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession


def play_until_floor_summary(session: FeaturedMatchWebSession) -> None:
    """Drive one seeded match slice up to the floor-summary pending screen."""
    while session.view()["decision_type"] == "FeaturedRoundDecisionState":
        session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
        session.advance()

    if session.view()["decision_type"] != "FloorVoteDecisionState":
        raise AssertionError("Expected floor-vote decision after featured rounds")

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()


def advance_through_transition_and_complete(session: FeaturedMatchWebSession) -> None:
    """Advance from successor choice to completed run using deterministic first offers."""
    if session.view()["decision_type"] != "SuccessorChoiceState":
        raise AssertionError("Expected successor-choice decision before transition")

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()  # sets civil-war transition pending screen
    session.advance()  # clears transition and presents powerup choice

    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()
