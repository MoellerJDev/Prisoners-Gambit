from __future__ import annotations

import copy
import random

from prisoners_gambit.core.interaction import ChooseSuccessorAction
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import generate_powerup_offers
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

from support.builders import build_agent, build_floor_summary_state, build_successor_candidates
from support.session_driver import play_until_floor_summary


def _seeded_summary_digest(seed: int) -> dict:
    session = FeaturedMatchWebSession(seed=seed, rounds=2)
    session.start()
    play_until_floor_summary(session)
    snapshot = session.view()["snapshot"]
    return {
        "player_score": snapshot["latest_featured_round"]["player_total"],
        "opponent_score": snapshot["latest_featured_round"]["opponent_total"],
        "vote": copy.deepcopy(snapshot["floor_vote_result"]),
        "entries": [
            (entry["name"], entry["score"], entry["wins"])
            for entry in snapshot["floor_summary"]["entries"]
        ],
    }


def test_invariant_web_slice_is_deterministic_under_same_seed() -> None:
    assert _seeded_summary_digest(99) == _seeded_summary_digest(99)


def test_invariant_offer_generators_respect_requested_counts() -> None:
    for count in (0, 1, 3, 6):
        powerups = generate_powerup_offers(count, random.Random(123))
        edits = generate_genome_edit_offers(count, random.Random(123))
        assert len(powerups) == count
        assert len(edits) == count
        assert all(offer.name for offer in powerups)
        assert all(offer.name for offer in edits)


def test_invariant_successor_state_has_valid_shape() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=1)
    session.start()
    play_until_floor_summary(session)
    session.advance()

    decision = session.view()["decision"]
    assert decision is not None
    assert len(decision["candidates"]) >= 1
    for candidate in decision["candidates"]:
        assert candidate["name"]
        assert candidate["lineage_depth"] >= 0
        assert isinstance(candidate["tags"], list)
        assert isinstance(candidate["tradeoffs"], list)

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    assert session.view()["snapshot"]["current_phase"] == "civil_war"


def test_invariant_floor_summary_structure_is_possible_and_consistent() -> None:
    ranked = [
        build_agent("You", is_player=True, lineage_id=1, score=12, wins=3),
        *build_successor_candidates(),
        build_agent("Outsider", lineage_id=2, score=8, wins=1),
    ]
    state = build_floor_summary_state(floor_number=3, ranked=ranked, player_lineage_id=1)

    assert state.floor_number == 3
    assert len(state.entries) == len(ranked)
    assert state.heir_pressure is not None
    assert len(state.heir_pressure.successor_candidates) <= 3
    assert len(state.heir_pressure.future_threats) <= 3
    assert all(entry.score >= 0 and entry.wins >= 0 for entry in state.entries)
