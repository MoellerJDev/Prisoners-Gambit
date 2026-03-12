from __future__ import annotations

from prisoners_gambit.core.interaction import ChooseSuccessorAction
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

from support.session_driver import play_until_floor_summary


def test_seeded_floor_progression_slice_reaches_floor_summary() -> None:
    session = FeaturedMatchWebSession(seed=41, rounds=2)
    session.start()

    play_until_floor_summary(session)

    view = session.view()
    assert view["pending_screen"] == "floor_summary"
    assert view["snapshot"]["floor_summary"] is not None
    assert view["snapshot"]["floor_vote_result"] is not None


def test_seeded_successor_choice_slice_promotes_selected_candidate() -> None:
    session = FeaturedMatchWebSession(seed=41, rounds=2)
    session.start()
    play_until_floor_summary(session)

    session.advance()  # move from summary screen to successor choice
    assert session.view()["decision_type"] == "SuccessorChoiceState"

    first_candidate = session.view()["decision"]["candidates"][0]["name"]
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    view = session.view()
    assert view["pending_screen"] == "civil_war_transition"
    assert view["snapshot"]["current_phase"] == "civil_war"
    assert view["snapshot"]["current_floor"] == 2
    assert view["snapshot"]["completion"] is None
    assert session.player.name == first_candidate


def test_seeded_civil_war_transition_slice_enters_offer_phase() -> None:
    session = FeaturedMatchWebSession(seed=41, rounds=2)
    session.start()
    play_until_floor_summary(session)

    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    assert session.view()["pending_screen"] == "civil_war_transition"

    session.advance()
    view = session.view()
    assert view["pending_screen"] is None
    assert view["decision_type"] == "PowerupChoiceState"
    assert len(view["decision"]["offers"]) == 3
