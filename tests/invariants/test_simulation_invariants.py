from __future__ import annotations

import copy
import random

from prisoners_gambit.core.interaction import ChooseSuccessorAction
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import generate_powerup_offers

from support.builders import (
    build_agent,
    build_floor_summary_state,
    build_seeded_session,
    build_successor_candidates,
    random_seed_set,
)
from support.session_driver import force_civil_war_transition, play_until_floor_summary, reach_successor_choice


def _seeded_summary_digest(seed: int) -> dict:
    session = build_seeded_session(seed=seed, rounds=2)
    play_until_floor_summary(session)
    snapshot = session.view()["snapshot"]
    return {
        "player_score": snapshot["latest_featured_round"]["player_total"],
        "opponent_score": snapshot["latest_featured_round"]["opponent_total"],
        "vote": copy.deepcopy(snapshot["floor_vote_result"]),
        "entries": [
            (entry["is_player"], entry["score"], entry["wins"])
            for entry in snapshot["floor_summary"]["entries"]
        ],
    }


def test_invariant_web_slice_is_deterministic_under_same_seed() -> None:
    for seed in (7, 21, 99, 1234):
        assert _seeded_summary_digest(seed) == _seeded_summary_digest(seed)


def test_invariant_offer_generators_respect_requested_counts() -> None:
    for count in (0, 1, 3, 6):
        powerups = generate_powerup_offers(count, random.Random(123))
        edits = generate_genome_edit_offers(count, random.Random(123))
        assert len(powerups) == count
        assert len(edits) == count
        assert all(offer.name for offer in powerups)
        assert all(offer.name for offer in edits)


def test_invariant_successor_candidate_payload_shape_across_multiple_seeds() -> None:
    required = {
        "name",
        "lineage_depth",
        "score",
        "wins",
        "branch_role",
        "branch_doctrine",
        "shaping_causes",
        "tags",
        "descriptor",
        "tradeoffs",
        "strengths",
        "liabilities",
        "attractive_now",
        "danger_later",
        "lineage_future",
        "succession_pitch",
        "succession_risk",
        "anti_score_note",
        "genome_summary",
        "powerups",
    }
    for seed in random_seed_set(base=77, size=5):
        session = build_seeded_session(seed=seed, rounds=2)
        reach_successor_choice(session)
        decision = session.view()["decision"]
        assert decision is not None
        assert len(decision["candidates"]) >= 1

        for candidate in decision["candidates"]:
            assert required.issubset(candidate.keys())
            assert isinstance(candidate["shaping_causes"], list)
            assert isinstance(candidate["tags"], list)
            assert isinstance(candidate["tradeoffs"], list)


def test_invariant_floor_summary_heir_pressure_shape_across_multiple_seeds() -> None:
    for seed in random_seed_set(base=101, size=5):
        session = build_seeded_session(seed=seed, rounds=2)
        play_until_floor_summary(session)
        summary = session.view()["snapshot"]["floor_summary"]
        heir_pressure = summary["heir_pressure"]

        assert heir_pressure is not None
        assert isinstance(heir_pressure["branch_doctrine"], str)
        assert isinstance(heir_pressure["successor_candidates"], list)
        assert isinstance(heir_pressure["future_threats"], list)

        for bucket in ("successor_candidates", "future_threats"):
            for entry in heir_pressure[bucket]:
                assert {"name", "branch_role", "shaping_causes", "score", "wins", "tags", "descriptor", "rationale"}.issubset(
                    entry.keys()
                )


def test_invariant_no_missing_required_fields_in_decision_payloads() -> None:
    required_by_state = {
        "FloorEventChoiceState": {
            "floor_number",
            "phase",
            "title",
            "summary",
            "pressure",
            "rule_text",
            "clue_reliability",
            "responses",
            "valid_actions",
        },
        "FeaturedRoundDecisionState": {"prompt", "valid_actions", "stance_options"},
        "SuccessorChoiceState": {
            "floor_number",
            "candidates",
            "current_phase",
            "lineage_doctrine",
            "threat_profile",
            "civil_war_pressure",
            "valid_actions",
        },
        "PowerupChoiceState": {"floor_number", "offers", "valid_actions"},
    }

    for seed in random_seed_set(base=144, size=4):
        session = build_seeded_session(seed=seed, rounds=1)

        first_decision = session.view()
        assert required_by_state[first_decision["decision_type"]].issubset(first_decision["decision"].keys())

        play_until_floor_summary(session)
        session.advance()
        successor = session.view()
        if successor["decision_type"] != "SuccessorChoiceState":
            force_civil_war_transition(session)
            successor = session.view()
        assert required_by_state[successor["decision_type"]].issubset(successor["decision"].keys())

        session.submit_action(ChooseSuccessorAction(candidate_index=0))
        session.advance()
        powerup = session.view()
        assert required_by_state[powerup["decision_type"]].issubset(powerup["decision"].keys())


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


def test_invariant_progression_digest_is_stable_across_repeated_runs() -> None:
    seeds = random_seed_set(base=202, size=4)
    for seed in seeds:
        first = _seeded_summary_digest(seed)
        second = _seeded_summary_digest(seed)
        third = _seeded_summary_digest(seed)
        assert first == second == third
