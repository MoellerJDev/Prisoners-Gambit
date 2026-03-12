from __future__ import annotations

"""Helpers for driving web-session milestones in deterministic tests.

These functions intentionally model common stopping points (floor summary,
successor choice, completion) so tests can assert contracts at each boundary.
"""

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
)
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession


def decision_type(session: FeaturedMatchWebSession) -> str | None:
    return session.view()["decision_type"]


def pending_screen(session: FeaturedMatchWebSession) -> str | None:
    return session.view()["pending_screen"]


def session_milestone(session: FeaturedMatchWebSession) -> str:
    """Name coarse progression points to keep contract assertions readable."""
    view = session.view()
    if view["status"] == "completed":
        return "completed"
    if view["pending_screen"] == "floor_summary":
        return "floor_summary_pending"
    if view["pending_screen"] == "civil_war_transition":
        return "civil_war_transition_pending"

    current = decision_type(session)
    milestones = {
        "FeaturedRoundDecisionState": "featured_round_decision",
        "FloorVoteDecisionState": "floor_vote_decision",
        "SuccessorChoiceState": "successor_choice_decision",
        "PowerupChoiceState": "powerup_choice_decision",
        "GenomeEditChoiceState": "genome_edit_choice_decision",
    }
    return milestones.get(current, "running")


def advance_until_decision(session: FeaturedMatchWebSession, expected: str, *, max_steps: int = 20) -> None:
    for _ in range(max_steps):
        if decision_type(session) == expected:
            return
        session.advance()
    raise AssertionError(f"Did not reach decision '{expected}' within {max_steps} steps")


def play_featured_rounds(
    session: FeaturedMatchWebSession,
    *,
    mode: str = "manual_cooperate",
    stance_rounds: int = 2,
    manual_move: int = COOPERATE,
) -> None:
    """Resolve featured rounds until floor vote using a compact action mode."""
    first_round = True
    while decision_type(session) == "FeaturedRoundDecisionState":
        if mode == "manual_cooperate":
            session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
        elif mode == "manual_defect":
            session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=DEFECT))
        elif mode == "manual_move":
            session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=manual_move))
        elif mode == "autopilot_round":
            session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_round"))
        elif mode == "autopilot_match":
            session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_match"))
        elif mode == "stance_follow_autopilot":
            if first_round:
                session.submit_action(
                    ChooseRoundStanceAction(
                        mode="set_round_stance",
                        stance="follow_autopilot_for_n_rounds",
                        rounds=stance_rounds,
                    )
                )
            else:
                session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_round"))
        else:
            raise ValueError(f"Unsupported featured-round mode: {mode}")

        session.advance()
        first_round = False


def play_until_floor_summary(
    session: FeaturedMatchWebSession,
    *,
    featured_mode: str = "manual_cooperate",
    floor_vote: int = COOPERATE,
) -> None:
    """Drive one seeded match slice up to the floor-summary pending screen."""
    play_featured_rounds(session, mode=featured_mode)

    if decision_type(session) != "FloorVoteDecisionState":
        raise AssertionError("Expected floor-vote decision after featured rounds")

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=floor_vote))
    session.advance()


def reach_successor_choice(session: FeaturedMatchWebSession, *, featured_mode: str = "manual_cooperate", floor_vote: int = COOPERATE) -> None:
    play_until_floor_summary(session, featured_mode=featured_mode, floor_vote=floor_vote)
    if session.view()["pending_screen"] != "floor_summary":
        raise AssertionError("Expected floor summary pending screen before successor choice")
    session.advance()
    if decision_type(session) != "SuccessorChoiceState":
        raise AssertionError("Expected successor-choice decision")


def advance_through_transition_and_complete(
    session: FeaturedMatchWebSession,
    *,
    candidate_index: int = 0,
    powerup_index: int = 0,
    genome_index: int = 0,
    civil_war_featured_mode: str = "manual_cooperate",
    civil_war_floor_vote: int = COOPERATE,
) -> None:
    """Advance from successor choice through civil-war floor to completed run."""
    if decision_type(session) != "SuccessorChoiceState":
        raise AssertionError("Expected successor-choice decision before transition")

    session.submit_action(ChooseSuccessorAction(candidate_index=candidate_index))
    session.advance()  # sets civil-war transition pending screen
    session.advance()  # clears transition and presents civil-war featured rounds

    play_featured_rounds(session, mode=civil_war_featured_mode)
    if decision_type(session) != "FloorVoteDecisionState":
        raise AssertionError("Expected floor vote decision in civil-war floor")

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=civil_war_floor_vote))
    session.advance()
    if pending_screen(session) != "floor_summary":
        raise AssertionError("Expected floor summary pending after civil-war floor")

    session.advance()  # clears floor summary and presents powerup choice
    session.submit_action(ChoosePowerupAction(offer_index=powerup_index))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=genome_index))
    session.advance()
