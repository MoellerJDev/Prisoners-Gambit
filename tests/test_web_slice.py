import json
import http.client
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

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
from prisoners_gambit.core.powerups import (
    BlocPolitics,
    CoerciveControl,
    ComplianceDividend,
    GoldenHandshake,
    PanicButton,
    SpiteEngine,
    TrustDividend,
    UnityTicket,
)
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.tournament import MatchResult
from prisoners_gambit.web.server import Handler, _new_web_session, _port_from_env, run_server
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

TEST_PADDING_LENGTH = 20_000


def test_new_web_session_honors_pg_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PG_SEED", "1234")
    session = _new_web_session()

    assert session.seed == 1234


def test_new_web_session_uses_fresh_seed_without_pg_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PG_SEED", raising=False)

    first = _new_web_session()
    second = _new_web_session()

    assert first.seed != second.seed

def test_new_web_session_uses_configured_rounds_per_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PG_ROUNDS_PER_MATCH", "9")

    session = _new_web_session()

    assert session.rounds == 9


def test_featured_match_web_session_round_trip_typed_action() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=2)
    session.start()

    assert session.session.status == "awaiting_decision"
    assert session.session.current_decision is not None

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()

    view = session.view()
    assert view["snapshot"]["latest_featured_round"] is not None
    assert view["snapshot"]["latest_featured_round"]["breakdown"]["base_player_points"] >= 0


def test_web_session_featured_prompt_and_round_payload_include_inference_fields() -> None:
    session = FeaturedMatchWebSession(seed=13, rounds=3)
    session.start()

    decision = session.view()["decision"]
    assert decision is not None
    prompt = decision["prompt"]
    assert isinstance(prompt["clue_channels"], list)
    assert prompt["clue_channels"]
    assert "inference_focus" in prompt
    assert "floor_clue_log" in prompt
    assert prompt["floor_clue_log"] == []

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    round_payload = session.view()["snapshot"]["latest_featured_round"]
    assert round_payload is not None
    assert "inference_update" in round_payload
    assert round_payload["inference_update"]

    second_prompt = session.view()["decision"]["prompt"]
    assert second_prompt["floor_clue_log"]
    second_len = len(second_prompt["floor_clue_log"])

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    third_prompt = session.view()["decision"]["prompt"]
    assert len(third_prompt["floor_clue_log"]) > second_len

def test_featured_match_web_session_supports_stance_actions() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=3)
    session.start()
    session.submit_action(
        ChooseRoundStanceAction(
            mode="set_round_stance",
            stance="follow_autopilot_for_n_rounds",
            rounds=2,
        )
    )
    session.advance()
    assert session.view()["snapshot"]["active_featured_stance"] is not None


def test_featured_match_web_session_persists_match_autopilot_across_rounds() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=3)
    session.start()

    session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_match"))
    session.advance()
    assert session.view()["snapshot"]["latest_featured_round"]["round_index"] == 0
    assert session.view()["decision_type"] == "FeaturedRoundDecisionState"

    session.advance()
    assert session.view()["snapshot"]["latest_featured_round"]["round_index"] == 1
    assert session.view()["decision_type"] == "FeaturedRoundDecisionState"

    session.advance()
    assert session.view()["decision_type"] == "FloorVoteDecisionState"


def test_featured_match_web_session_clears_match_autopilot_after_manual_move() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=3)
    session.start()

    session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_match"))
    session.advance()
    assert session.should_autopilot_featured_match is True

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    assert session.should_autopilot_featured_match is False




def test_web_session_lineage_chronicle_records_major_milestones() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.snapshot.floor_summary.heir_pressure.future_threats = []
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    session.advance()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()

    chronicle = session.view()["snapshot"]["lineage_chronicle"]
    event_types = [entry["event_type"] for entry in chronicle]

    assert event_types[0] == "run_start"
    assert "floor_complete" in event_types
    assert "doctrine_pivot" in event_types
    assert "successor_pressure" in event_types
    assert "successor_choice" in event_types
    assert "phase_transition" in event_types
    assert event_types[-1] == "run_outcome"


def test_web_session_lineage_chronicle_does_not_duplicate_on_refresh_paths() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    before = list(session.view()["snapshot"]["lineage_chronicle"])
    session.view()
    session.view()
    session.view()
    after = session.view()["snapshot"]["lineage_chronicle"]

    assert after == before


def test_web_session_state_round_trip_preserves_lineage_chronicle() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=2)
    session.start()
    session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_match"))
    session.advance()

    restored = FeaturedMatchWebSession.from_serialized_state(session.serialize_state())

    assert restored.view()["snapshot"]["lineage_chronicle"] == session.view()["snapshot"]["lineage_chronicle"]




def test_web_session_floor_summary_exposes_lineage_relation_and_change_signals() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    entries = session.view()["snapshot"]["floor_summary"]["entries"]
    assert any(entry["lineage_relation"] == "host" for entry in entries)
    assert any(entry["lineage_relation"] == "kin" for entry in entries)
    assert any(entry["lineage_relation"] == "outsider" for entry in entries)
    assert all(entry["pressure_trend"] in {"rising", "falling", "steady"} for entry in entries)


def test_web_session_continuity_signals_update_across_floor_transition() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    entries = session.view()["snapshot"]["floor_summary"]["entries"]
    assert any(entry["survived_previous_floor"] for entry in entries)
    assert any(entry["continuity_streak"] >= 2 for entry in entries)
    assert any(entry["score_delta"] != 0 or entry["wins_delta"] != 0 for entry in entries)


def test_web_session_dynasty_board_exposes_central_rival_and_relation_tokens() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    board_entries = session.view()["snapshot"]["dynasty_board"]["entries"]
    assert any(entry["is_central_rival"] for entry in board_entries)
    assert all(entry["lineage_relation"] in {"host", "kin", "outsider"} for entry in board_entries)


def test_web_session_strategic_snapshot_generates_from_representative_states() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    start_snapshot = session.view()["snapshot"]["strategic_snapshot"]
    assert start_snapshot is not None
    assert start_snapshot["headline"].startswith("Host You")
    assert any(chip.startswith("Rival:") for chip in start_snapshot["chips"])

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    summary_snapshot = session.view()["snapshot"]["strategic_snapshot"]
    assert summary_snapshot is not None
    assert any(chip.startswith("Pressure:") for chip in summary_snapshot["chips"])
    assert any(line.startswith("Stability posture:") or line.startswith("Risk posture:") for line in summary_snapshot["details"])


def test_web_session_strategic_snapshot_surfaces_central_rival_floor_pressure_and_lineage_posture() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    strategic = session.view()["snapshot"]["strategic_snapshot"]
    board_entries = session.view()["snapshot"]["dynasty_board"]["entries"]
    central_rival = next(entry["name"] for entry in board_entries if entry["is_central_rival"])

    assert any(chip == f"Rival: {central_rival}" for chip in strategic["chips"])
    assert any(chip.startswith("Pressure:") and chip != "Pressure: Floor pressure unresolved" for chip in strategic["chips"])
    assert any(chip.startswith("Lineage:") and chip != "Lineage: Lineage direction forming" for chip in strategic["chips"])
    assert any(line.startswith("Central rival signal:") for line in strategic["details"])


def test_web_session_strategic_snapshot_survives_save_restore_without_progression_regression() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=2)
    session.start()
    session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_match"))
    session.advance()

    strategic_before = session.view()["snapshot"]["strategic_snapshot"]
    restored = FeaturedMatchWebSession.from_serialized_state(session.serialize_state())
    strategic_after = restored.view()["snapshot"]["strategic_snapshot"]

    assert strategic_before == strategic_after

    session.advance()
    restored.advance()
    assert restored.view() == session.view()


def test_web_session_continuity_signals_are_stable_across_intra_floor_dynasty_rebuilds() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    baseline_board = session.view()["snapshot"]["dynasty_board"]
    assert baseline_board is not None

    session._rebuild_dynasty_board()
    rebuilt_once = session.view()["snapshot"]["dynasty_board"]
    session._rebuild_dynasty_board()
    rebuilt_twice = session.view()["snapshot"]["dynasty_board"]

    assert rebuilt_once == baseline_board
    assert rebuilt_twice == baseline_board


def test_web_session_continuity_baseline_updates_only_on_new_floor_summary() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    before = session.view()["snapshot"]["floor_summary"]["entries"]
    before_by_name = {entry["name"]: entry for entry in before}

    session._rebuild_dynasty_board()
    session._rebuild_dynasty_board()
    mid = session.view()["snapshot"]["floor_summary"]["entries"]
    assert mid == before

    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    after = session.view()["snapshot"]["floor_summary"]["entries"]
    assert any(entry["survived_previous_floor"] for entry in after)
    assert any(entry["continuity_streak"] >= 2 for entry in after)

    shared = [entry for entry in after if entry["name"] in before_by_name]
    assert shared
    assert any(entry["score_delta"] == entry["score"] - before_by_name[entry["name"]]["score"] for entry in shared)


def test_web_session_new_central_rival_is_transition_based_not_rebuild_based() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    floor_one_board = session.view()["snapshot"]["dynasty_board"]["entries"]
    first_new_rivals = {entry["name"] for entry in floor_one_board if entry["is_new_central_rival"]}

    session._rebuild_dynasty_board()
    rebuilt_board = session.view()["snapshot"]["dynasty_board"]["entries"]
    rebuilt_new_rivals = {entry["name"] for entry in rebuilt_board if entry["is_new_central_rival"]}
    assert rebuilt_new_rivals == first_new_rivals

    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    floor_two_board = session.view()["snapshot"]["dynasty_board"]["entries"]
    second_new_rivals = {entry["name"] for entry in floor_two_board if entry["is_new_central_rival"]}
    assert second_new_rivals
    assert second_new_rivals != first_new_rivals


def test_web_session_dynasty_board_marks_host_and_successor_pressure_on_floor_summary() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    board_entries = session.view()["snapshot"]["dynasty_board"]["entries"]
    assert board_entries
    assert any(entry["is_current_host"] for entry in board_entries)
    assert any(entry["has_successor_pressure"] for entry in board_entries)
    assert any(entry.get("successor_pressure_cause", "").startswith("because ") for entry in board_entries if entry["has_successor_pressure"])


def test_floor_summary_lineage_doctrine_does_not_claim_no_survivors_when_lineage_entries_exist() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    floor_summary = session.view()["snapshot"]["floor_summary"]
    assert floor_summary is not None
    doctrine = floor_summary["heir_pressure"]["branch_doctrine"]
    lineage_entries = [entry for entry in floor_summary["entries"] if entry["name"] in {"You", "Cinder Branch", "Vesper Branch"}]

    assert len(lineage_entries) >= 2
    assert "no active branch survived" not in doctrine.lower()


def test_web_session_roster_continuity_reuses_branch_identities_across_ecosystem_floors() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    first_summary = session.view()["snapshot"]["floor_summary"]
    assert first_summary is not None
    first_floor_names = {entry["name"] for entry in first_summary["entries"]}

    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    second_summary = session.view()["snapshot"]["floor_summary"]
    assert second_summary is not None
    second_floor_names = {entry["name"] for entry in second_summary["entries"]}

    continuing = first_floor_names.intersection(second_floor_names)
    assert len(continuing) >= 2
    assert "Unknown Opponent" not in second_floor_names


def test_web_session_successor_candidates_derive_from_persistent_roster() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    summary = session.view()["snapshot"]["floor_summary"]
    assert summary is not None
    summary_names = {entry["name"] for entry in summary["entries"]}

    session.advance()
    successor = session.view()["decision"]
    assert successor is not None
    candidate_names = {entry["name"] for entry in successor["candidates"]}

    assert candidate_names
    assert candidate_names.issubset(summary_names)
    assert "Heir A" not in candidate_names
    assert "Heir B" not in candidate_names


def test_web_session_dynasty_board_marks_civil_war_danger_after_successor_choice() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.snapshot.floor_summary.heir_pressure.future_threats = []
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    board_entries = session.view()["snapshot"]["dynasty_board"]["entries"]
    assert board_entries
    assert any(entry["is_current_host"] for entry in board_entries)
    assert any(entry["has_civil_war_danger"] for entry in board_entries)
    assert any(entry.get("civil_war_danger_cause", "").startswith("because ") for entry in board_entries if entry["has_civil_war_danger"])




def test_web_session_dynasty_board_can_show_host_pressure_and_danger_on_same_entry() -> None:
    session = FeaturedMatchWebSession(seed=1, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    candidates = session.view()["decision"]["candidates"]
    top_candidate_index = max(range(len(candidates)), key=lambda idx: candidates[idx]["score"])
    session.snapshot.floor_summary.heir_pressure.future_threats = []
    session.submit_action(ChooseSuccessorAction(candidate_index=top_candidate_index))
    session.advance()

    board_entries = session.view()["snapshot"]["dynasty_board"]["entries"]
    host_entries = [entry for entry in board_entries if entry["is_current_host"]]
    assert host_entries
    host_entry = host_entries[0]
    assert host_entry["has_successor_pressure"] is True
    assert host_entry["has_civil_war_danger"] is True

def test_web_session_lineage_chronicle_captures_causal_pivots_without_duplication() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    chronicle = session.view()["snapshot"]["lineage_chronicle"]
    doctrine_entries = [entry for entry in chronicle if entry["event_type"] == "doctrine_pivot"]
    successor_pressure_entries = [entry for entry in chronicle if entry["event_type"] == "successor_pressure"]

    assert len(doctrine_entries) == 1
    assert doctrine_entries[0]["cause"] is not None
    assert doctrine_entries[0]["cause"].startswith("because ")
    assert len(successor_pressure_entries) == 1
    assert successor_pressure_entries[0]["cause"] is not None
    assert successor_pressure_entries[0]["cause"].startswith("because ")

def test_web_session_state_serialization_round_trip_preserves_pending_decision_and_snapshot() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=3)
    session.start()
    session.submit_action(
        ChooseRoundStanceAction(
            mode="set_round_stance",
            stance="follow_autopilot_for_n_rounds",
            rounds=2,
        )
    )
    session.advance()

    saved = session.serialize_state()
    restored = FeaturedMatchWebSession.from_serialized_state(saved)

    assert restored.view() == session.view()


def test_web_session_state_round_trip_preserves_dynasty_board() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    restored = FeaturedMatchWebSession.from_serialized_state(session.serialize_state())
    assert restored.view()["snapshot"]["dynasty_board"] == session.view()["snapshot"]["dynasty_board"]


def test_web_session_state_restore_continues_deterministically() -> None:
    session = FeaturedMatchWebSession(seed=17, rounds=3)
    session.start()
    session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_match"))
    session.advance()

    restored = FeaturedMatchWebSession.from_serialized_state(session.serialize_state())

    session.advance()
    restored.advance()
    assert restored.view() == session.view()




def test_web_session_restore_from_civil_war_transition_continues_to_civil_war_decision() -> None:
    session = FeaturedMatchWebSession(seed=31, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.snapshot.floor_summary.heir_pressure.future_threats = []
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    restored = FeaturedMatchWebSession.from_serialized_state(session.serialize_state())

    session.advance()
    restored.advance()
    assert session.view() == restored.view()
    assert restored.view()["decision_type"] == "FeaturedRoundDecisionState"

def test_web_session_state_serializes_rng_as_safe_json_data() -> None:
    session = FeaturedMatchWebSession(seed=23, rounds=3)
    session.start()

    payload = session.serialize_state()

    assert isinstance(payload["rng_state"], dict)
    assert isinstance(payload["rng_state"]["internal_state"], list)


def test_web_session_rng_continues_deterministically_after_safe_restore() -> None:
    session = FeaturedMatchWebSession(seed=29, rounds=3)
    session.start()
    session.submit_action(ChooseRoundAutopilotAction(mode="autopilot_match"))
    session.advance()

    restored = FeaturedMatchWebSession.from_serialized_state(session.serialize_state())

    for _ in range(2):
        session.advance()
        restored.advance()

    assert restored.view() == session.view()


def test_web_session_save_code_export_import_round_trip() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=2)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()

    save_code = session.export_save_code(b"test-shared-secret")
    restored = FeaturedMatchWebSession.import_save_code(save_code, b"test-shared-secret")

    assert restored.view() == session.view()


def test_web_session_rejects_tampered_save_code() -> None:
    session = FeaturedMatchWebSession(seed=13, rounds=2)
    session.start()
    save_code = session.export_save_code(b"integrity-secret")
    tampered = save_code[:-1] + ("A" if save_code[-1] != "A" else "B")

    with pytest.raises(ValueError, match="Invalid save code"):
        FeaturedMatchWebSession.import_save_code(tampered, b"integrity-secret")


def test_web_session_rejects_save_code_with_wrong_secret() -> None:
    session = FeaturedMatchWebSession(seed=13, rounds=2)
    session.start()
    save_code = session.export_save_code(b"secret-one")

    with pytest.raises(ValueError, match="Invalid save code"):
        FeaturedMatchWebSession.import_save_code(save_code, b"secret-two")


def test_web_session_rejects_malformed_save_payload() -> None:
    with pytest.raises(ValueError, match="Invalid save payload"):
        FeaturedMatchWebSession.from_serialized_state({"version": 1, "seed": 7})


def test_web_session_rejects_invalid_rng_shape() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=2)
    session.start()
    payload = session.serialize_state()
    payload["rng_state"] = "not-a-dict"

    with pytest.raises(ValueError, match="Invalid save payload"):
        FeaturedMatchWebSession.from_serialized_state(payload)


def test_featured_match_web_session_rejects_duration_stance_without_rounds() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=3)
    session.start()
    session.submit_action(
        ChooseRoundStanceAction(
            mode="set_round_stance",
            stance="follow_autopilot_for_n_rounds",
            rounds=0,
        )
    )

    with pytest.raises(ValueError, match="requires rounds > 0"):
        session.advance()


def test_web_session_advances_through_full_run_loop() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    assert session.view()["decision_type"] == "FloorVoteDecisionState"

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    assert session.view()["pending_screen"] == "floor_summary"

    session.advance()
    assert session.view()["decision_type"] == "SuccessorChoiceState"
    successor_decision = session.view()["decision"]
    assert successor_decision is not None
    assert {"current_phase", "lineage_doctrine", "threat_profile", "civil_war_pressure"}.issubset(successor_decision.keys())
    assert successor_decision["civil_war_pressure"] in {"low", "rising", "high"}

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    assert session.view()["pending_screen"] is None
    assert session.view()["snapshot"]["current_phase"] == "ecosystem"
    assert session.view()["snapshot"]["civil_war_context"] is None
    assert session.view()["decision_type"] == "PowerupChoiceState"
    floor_identity = session.view()["snapshot"]["floor_identity"]
    assert floor_identity is not None
    assert floor_identity["target_floor"] == 2
    assert floor_identity["host_name"] == session.view()["snapshot"]["dynasty_board"]["entries"][0]["name"]
    assert floor_identity["headline"].startswith(floor_identity["pressure_label"])
    assert floor_identity["dominant_pressure"]
    assert floor_identity["lineage_direction"].startswith("Doctrine path: ")
    powerup_offer = session.view()["decision"]["offers"][0]
    assert {"lineage_commitment", "doctrine_vector", "branch_identity", "tradeoff", "phase_support", "successor_pressure", "tags", "trigger", "effect", "role", "relevance_hint", "crown_hint"}.issubset(powerup_offer.keys())

    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    assert session.view()["decision_type"] == "GenomeEditChoiceState"
    genome_offer = session.view()["decision"]["offers"][0]
    assert {"lineage_commitment", "doctrine_vector", "branch_identity", "tradeoff", "phase_support", "successor_pressure", "doctrine_drift"}.issubset(genome_offer.keys())

    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()
    assert session.view()["status"] == "awaiting_decision"
    assert session.view()["snapshot"]["completion"] is None
    assert session.view()["snapshot"]["current_phase"] == "ecosystem"
    assert session.view()["snapshot"]["current_floor"] == 2
    assert session.view()["snapshot"]["floor_identity"] is not None
    assert session.view()["decision_type"] == "FeaturedRoundDecisionState"


def test_web_session_successor_choice_changes_next_floor_identity_framing() -> None:
    session_a = FeaturedMatchWebSession(seed=17, rounds=1)
    session_a.start()
    session_a.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session_a.advance()
    session_a.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session_a.advance()
    session_a.advance()
    session_a.submit_action(ChooseSuccessorAction(candidate_index=0))
    session_a.advance()
    identity_a = session_a.view()["snapshot"]["floor_identity"]

    session_b = FeaturedMatchWebSession(seed=17, rounds=1)
    session_b.start()
    session_b.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session_b.advance()
    session_b.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session_b.advance()
    session_b.advance()
    session_b.submit_action(ChooseSuccessorAction(candidate_index=1))
    session_b.advance()
    identity_b = session_b.view()["snapshot"]["floor_identity"]

    assert identity_a is not None and identity_b is not None
    assert identity_a["host_name"] != identity_b["host_name"]
    assert identity_a["headline"] != identity_b["headline"]
    assert (
        identity_a["strategic_focus"] != identity_b["strategic_focus"]
        or identity_a["pressure_reason"] != identity_b["pressure_reason"]
    )






def test_web_session_floor_identity_carries_lineage_pressure_between_floors() -> None:
    session = FeaturedMatchWebSession(seed=17, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    decision = session.view()["decision"]
    assert decision is not None
    first_candidate = decision["candidates"][0]
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    floor_identity = session.view()["snapshot"]["floor_identity"]
    assert floor_identity is not None
    assert "pressure via" in floor_identity["pressure_reason"]
    assert first_candidate["name"] in floor_identity["headline"]
    assert floor_identity["strategic_focus"].startswith("Push ")
    assert "hedge " in floor_identity["strategic_focus"]
    assert "Track clue:" in floor_identity["strategic_focus"]


def test_web_session_floor_identity_is_concise_for_mobile_readability() -> None:
    session = FeaturedMatchWebSession(seed=17, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    floor_identity = session.view()["snapshot"]["floor_identity"]
    assert floor_identity is not None
    assert len(floor_identity["pressure_reason"]) <= 80
    assert len(floor_identity["strategic_focus"]) <= 160
    assert floor_identity["pressure_reason"].count(";") == 0


def test_web_session_floor_identity_differs_by_successor_branch_pressure() -> None:
    session_a = FeaturedMatchWebSession(seed=17, rounds=1)
    session_a.start()
    session_a.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session_a.advance()
    session_a.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session_a.advance()
    session_a.advance()
    session_a.submit_action(ChooseSuccessorAction(candidate_index=0))
    session_a.advance()
    identity_a = session_a.view()["snapshot"]["floor_identity"]

    session_b = FeaturedMatchWebSession(seed=17, rounds=1)
    session_b.start()
    session_b.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session_b.advance()
    session_b.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session_b.advance()
    session_b.advance()
    session_b.submit_action(ChooseSuccessorAction(candidate_index=1))
    session_b.advance()
    identity_b = session_b.view()["snapshot"]["floor_identity"]

    assert identity_a is not None and identity_b is not None
    assert "pressure via" in identity_a["pressure_reason"]
    assert "pressure via" in identity_b["pressure_reason"]
    assert identity_a["headline"] != identity_b["headline"]
    assert identity_a["strategic_focus"] != identity_b["strategic_focus"]

def test_web_session_successor_transition_does_not_require_civil_war_when_trigger_not_met() -> None:
    session = FeaturedMatchWebSession(seed=17, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    assert session.view()["decision_type"] == "PowerupChoiceState"
    assert session.view()["snapshot"]["current_phase"] == "ecosystem"
    assert session.view()["snapshot"]["session_status"] == "awaiting_decision"
    assert session.view()["status"] != "completed"
    assert session.view()["snapshot"]["completion"] is None




def test_web_session_save_resume_persists_next_floor_transition_after_reward_resolution() -> None:
    session = FeaturedMatchWebSession(seed=17, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()

    saved = session.serialize_state()
    restored = FeaturedMatchWebSession.from_serialized_state(saved)

    assert restored.view()["status"] == "awaiting_decision"
    assert restored.view()["snapshot"]["completion"] is None
    assert restored.view()["snapshot"]["current_phase"] == "ecosystem"
    assert restored.view()["snapshot"]["current_floor"] == 2
    assert restored.view()["snapshot"]["floor_identity"] is not None
    assert restored.view()["decision_type"] == "FeaturedRoundDecisionState"

def test_web_session_pending_messages_describe_next_required_action() -> None:
    session = FeaturedMatchWebSession(seed=19, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    assert session.view()["pending_message"] == "Floor 1 complete — review successor options."

    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    assert session.view()["pending_message"] is None





def test_web_session_transition_action_label_is_contextual_for_pending_states() -> None:
    session = FeaturedMatchWebSession(seed=19, rounds=1)
    session.start()

    assert session.view()["transition_action_visible"] is False
    assert session.view()["transition_action_label"] is None

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    assert session.view()["pending_screen"] == "floor_summary"
    assert session.view()["transition_action_visible"] is True
    assert session.view()["transition_action_label"] == "Review successor options"

    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    assert session.view()["pending_screen"] is None
    assert session.view()["transition_action_visible"] is False
    assert session.view()["transition_action_label"] is None


def test_web_session_transition_action_hidden_when_decision_is_active() -> None:
    session = FeaturedMatchWebSession(seed=21, rounds=1)
    session.start()

    assert session.view()["decision_type"] == "FeaturedRoundDecisionState"
    assert session.view()["transition_action_visible"] is False
    assert session.view()["transition_action_label"] is None


def test_web_html_powerup_cards_render_trigger_effect_role_as_visible_content() -> None:
    from prisoners_gambit.web import server as web_server

    assert "const functional = [trigger, effect, role]" in web_server.HTML
    assert "`${actionTile(label, subtitle)}${functional}<span class='muted'>${powerupToken(offer.name)}</span>`" in web_server.HTML


def test_web_html_uses_contextual_transition_action_button() -> None:
    from prisoners_gambit.web import server as web_server

    assert "id='advanceBtn'" in web_server.HTML
    assert "transition_action_label" in web_server.HTML
    assert "Continue Screen" not in web_server.HTML


def test_web_html_dynasty_board_renders_all_marker_tokens_compactly() -> None:
    from prisoners_gambit.web import server as web_server

    assert "markerTokens.join(' ')" in web_server.HTML
    assert "effectToken('YOU')" in web_server.HTML
    assert "effectToken('HEIR')" in web_server.HTML
    assert "effectToken('RISK')" in web_server.HTML
    assert "NEW RIVAL" in web_server.HTML
    assert "relationToken" in web_server.HTML

def test_web_api_drives_session_without_terminal_formatting() -> None:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        req = Request(f"http://127.0.0.1:{port}/api/run/start", method="POST")
        with urlopen(req) as resp:
            started = json.loads(resp.read().decode("utf-8"))
        assert started["status"] == "awaiting_decision"
        assert started["decision_type"] == "FeaturedRoundDecisionState"

        action_body = json.dumps({"type": "manual_move", "move": "C"}).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/api/action",
            data=action_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req) as resp:
            after = json.loads(resp.read().decode("utf-8"))

        latest = after["snapshot"]["latest_featured_round"]
        assert latest is not None
        assert "Autopilot planned" not in json.dumps(latest)
    finally:
        server.shutdown()
        server.server_close()


def test_web_api_exposes_round_action_types_and_stance_options() -> None:
    session = FeaturedMatchWebSession(seed=11, rounds=2)
    session.start()

    decision = session.view()["decision"]

    assert decision["valid_actions"] == (
        "manual_move",
        "autopilot_round",
        "autopilot_match",
        "set_round_stance",
    )
    assert "cooperate_until_betrayed" in decision["stance_options"]
    assert "lock_last_manual_move_for_n_rounds" in decision["stance_options"]


def test_web_api_rejects_invalid_manual_move_payload() -> None:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        req = Request(f"http://127.0.0.1:{port}/api/run/start", method="POST")
        with urlopen(req):
            pass

        action_body = json.dumps({"type": "manual_move", "move": "X"}).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/api/action",
            data=action_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urlopen(req)
            raise AssertionError("expected HTTPError")
        except HTTPError as exc:
            body = json.loads(exc.read().decode("utf-8"))
            assert exc.code == 400
            assert body["error"] == "invalid move; expected 'C' or 'D'"
    finally:
        server.shutdown()
        server.server_close()


def test_web_api_rejects_invalid_vote_and_stance_payloads() -> None:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        req = Request(f"http://127.0.0.1:{port}/api/run/start", method="POST")
        with urlopen(req) as resp:
            state = json.loads(resp.read().decode("utf-8"))
        while state["decision_type"] != "FloorVoteDecisionState":
            if state["decision_type"] == "FeaturedRoundDecisionState":
                body = json.dumps({"type": "manual_move", "move": "C"}).encode("utf-8")
                req = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
            else:
                req = Request(f"http://127.0.0.1:{port}/api/advance", method="POST")
            with urlopen(req) as resp:
                state = json.loads(resp.read().decode("utf-8"))

        vote_body = json.dumps({"type": "manual_vote", "vote": "X"}).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/api/action",
            data=vote_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urlopen(req)
            raise AssertionError("expected HTTPError")
        except HTTPError as exc:
            body = json.loads(exc.read().decode("utf-8"))
            assert exc.code == 400
            assert body["error"] == "invalid vote; expected 'C' or 'D'"

        req = Request(f"http://127.0.0.1:{port}/api/run/start", method="POST")
        with urlopen(req):
            pass
        stance_body = json.dumps({"type": "set_round_stance", "stance": "follow_autopilot_for_n_rounds"}).encode(
            "utf-8"
        )
        req = Request(
            f"http://127.0.0.1:{port}/api/action",
            data=stance_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urlopen(req)
            raise AssertionError("expected HTTPError")
        except HTTPError as exc:
            body = json.loads(exc.read().decode("utf-8"))
            assert exc.code == 400
            assert body["error"] == "rounds required for selected stance"
    finally:
        server.shutdown()
        server.server_close()


def test_web_api_rejects_invalid_and_oversized_content_length() -> None:
    from http.server import ThreadingHTTPServer

    class Http11Handler(Handler):
        protocol_version = "HTTP/1.1"

    server = ThreadingHTTPServer(("127.0.0.1", 0), Http11Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.putrequest("POST", "/api/action")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", "abc")
        conn.putheader("Connection", "keep-alive")
        conn.endheaders()
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 400
        assert body["error"] == "invalid Content-Length"
        assert response.getheader("Connection") == "close"
        assert conn.sock is None
        conn.close()

        oversized_body = json.dumps(
            {"type": "manual_move", "move": "C", "padding": "x" * TEST_PADDING_LENGTH}
        ).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request(
            "POST",
            "/api/action",
            body=oversized_body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(oversized_body)),
                "Connection": "keep-alive",
            },
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 413
        assert body["error"] == "request body too large"
        assert response.getheader("Connection") == "close"
        assert conn.sock is None
        conn.close()
    finally:
        server.shutdown()
        server.server_close()


def test_web_root_and_json_responses_include_content_length_for_http11() -> None:
    from http.server import ThreadingHTTPServer

    class Http11Handler(Handler):
        protocol_version = "HTTP/1.1"

    server = ThreadingHTTPServer(("127.0.0.1", 0), Http11Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/", headers={"Connection": "keep-alive"})
        response = conn.getresponse()
        html = response.read()
        assert response.status == 200
        assert response.getheader("Content-Length") == str(len(html))

        conn.request("GET", "/api/state", headers={"Connection": "keep-alive"})
        response = conn.getresponse()
        payload = response.read()
        assert response.status == 200
        assert response.getheader("Content-Length") == str(len(payload))
        assert "status" in json.loads(payload.decode("utf-8"))
        conn.close()
    finally:
        server.shutdown()
        server.server_close()




def test_web_html_adds_mobile_viewport_and_touch_targets() -> None:
    from prisoners_gambit.web import server as web_server

    assert "name='viewport'" in web_server.HTML
    assert ".actions { grid-template-columns:repeat(2, minmax(0, 1fr)); gap:7px; }" in web_server.HTML
    assert ".actions .btn { min-height:56px; padding:8px 9px; }" in web_server.HTML
    assert ".controls .btn { flex:1 1 calc(50% - 10px); min-height:50px; }" in web_server.HTML


def test_web_html_mobile_layout_prioritizes_decision_context_and_reduces_clutter() -> None:
    from prisoners_gambit.web import server as web_server

    assert ".decision-actions-panel { position:sticky; top:8px; z-index:3; }" in web_server.HTML
    assert ".decision-details-panel {" in web_server.HTML
    assert "<div class='row controls action-controls'>" in web_server.HTML
    assert "<div class='row controls status-controls'>" in web_server.HTML
    assert "<details open>" in web_server.HTML
    assert "Expand raw state/debug JSON" in web_server.HTML


def test_web_html_marks_primary_actions_for_mobile_tap_focus() -> None:
    from prisoners_gambit.web import server as web_server

    assert "p.suggested_move === 0 ? 'primary-action' : ''" in web_server.HTML
    assert "p.suggested_vote === 0 ? 'primary-action' : ''" in web_server.HTML
    assert "btn.className = idx === 0 ? 'btn primary-action' : 'btn action-tile-secondary';" in web_server.HTML
    assert "function actionTile(label, meta){" in web_server.HTML
    assert "action-tile-title" in web_server.HTML


def test_web_html_prioritizes_mobile_panel_ordering() -> None:
    from prisoners_gambit.web import server as web_server

    assert "grid > .decision-actions-panel { order:1; }" in web_server.HTML
    assert "grid > .decision-details-panel { order:2; }" in web_server.HTML
    assert "grid > .result-panel { order:3; }" in web_server.HTML
    assert "grid > .floor-identity-panel { order:4; }" in web_server.HTML
    assert "panel panel-enter vote-panel panel-mobile-low" in web_server.HTML


def test_web_html_shows_floor_identity_headline_and_compact_fields() -> None:
    from prisoners_gambit.web import server as web_server

    assert "id='floorIdentityHeadline'" in web_server.HTML
    assert "<strong>Dominant pressure</strong>" in web_server.HTML
    assert "<strong>Why it matters</strong>" in web_server.HTML


def test_web_html_splits_decision_actions_from_details_panel() -> None:
    from prisoners_gambit.web import server as web_server

    assert "<div class='panel panel-enter decision-actions-panel'>" in web_server.HTML
    assert "id='actionsPrimaryLabel' class='actions-primary-label'" in web_server.HTML
    assert "<div id='actions' class='row actions'>" in web_server.HTML
    assert "<details id='advancedActions' class='advanced-actions'" in web_server.HTML
    assert "<div id='advancedActionsGrid' class='row actions actions-secondary'>" in web_server.HTML
    assert "<div class='panel panel-enter decision-details-panel'>" in web_server.HTML
    assert "<h3>Decision Details</h3>" in web_server.HTML
    assert "<div id='decisionView' class='kv muted'>" in web_server.HTML


def test_web_html_decision_details_copy_is_short_and_scannable() -> None:
    from prisoners_gambit.web import server as web_server

    assert "<div>Next pick</div>" in web_server.HTML
    assert "<div>Read on rival</div>" in web_server.HTML
    assert "<div>Recent floor notes</div>" in web_server.HTML
    assert "<ul class='list tight'>" in web_server.HTML


def test_web_html_round_decision_separates_core_actions_from_advanced_tactics() -> None:
    from prisoners_gambit.web import server as web_server

    assert "actionTile('Cooperate', 'Manual move · primary')" in web_server.HTML
    assert "actionTile('Defect', 'Manual move · primary')" in web_server.HTML
    assert "actionTile('Autopilot', `Recommended · ${moveLabel(p.suggested_move)}`)" in web_server.HTML
    assert "advancedLabel.textContent = 'Advanced tactic setup (optional)';" in web_server.HTML
    assert "actionTile('C until betrayed', 'Stance')" in web_server.HTML
    assert "actionTile('Autopilot N', 'Stance with duration')" in web_server.HTML
    assert "actionsPrimaryLabel.textContent = 'Main choice now';" in web_server.HTML


def test_web_root_contains_full_run_panels() -> None:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with urlopen(f"http://127.0.0.1:{port}/") as resp:
            html = resp.read().decode("utf-8")
        assert "Current Decision" in html
        assert "Floor Identity" in html
        assert "Floor Referendum" in html
        assert "Floor Summary" in html
        assert "Successor Options" in html
        assert "Run Completion" in html
    finally:
        server.shutdown()
        server.server_close()


def test_run_server_defaults_to_public_host(monkeypatch) -> None:
    captured = {}

    class FakeServer:
        def __init__(self, address, handler):
            captured["address"] = address
            captured["handler"] = handler

        def serve_forever(self):
            captured["served"] = True

    monkeypatch.setattr("prisoners_gambit.web.server.ThreadingHTTPServer", FakeServer)

    run_server(port=9999)

    assert captured["address"] == ("0.0.0.0", 9999)
    assert captured["handler"] is Handler
    assert captured["served"] is True


def test_port_from_env_uses_default_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("PORT", raising=False)

    assert _port_from_env() == 8765


def test_port_from_env_uses_configured_port(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "12345")

    assert _port_from_env() == 12345


def test_port_from_env_falls_back_for_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "not-a-port")

    assert _port_from_env() == 8765


def test_web_api_keeps_session_state_isolated_per_server_instance() -> None:
    from http.server import ThreadingHTTPServer

    server_a = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_b = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port_a = server_a.server_address[1]
    port_b = server_b.server_address[1]
    thread_a = threading.Thread(target=server_a.serve_forever, daemon=True)
    thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
    thread_a.start()
    thread_b.start()

    try:
        req = Request(f"http://127.0.0.1:{port_a}/api/run/start", method="POST")
        with urlopen(req) as resp:
            started = json.loads(resp.read().decode("utf-8"))
        assert started["status"] == "awaiting_decision"

        with urlopen(f"http://127.0.0.1:{port_a}/api/state") as resp:
            state_a = json.loads(resp.read().decode("utf-8"))
        with urlopen(f"http://127.0.0.1:{port_b}/api/state") as resp:
            state_b = json.loads(resp.read().decode("utf-8"))

        assert state_a["status"] == "awaiting_decision"
        assert state_b["status"] == "not_started"
        assert state_b["decision_type"] is None
    finally:
        server_a.shutdown()
        server_a.server_close()
        server_b.shutdown()
        server_b.server_close()


def test_web_api_can_export_and_import_explicit_save_state() -> None:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        req = Request(f"http://127.0.0.1:{port}/api/run/start", method="POST")
        with urlopen(req) as resp:
            started = json.loads(resp.read().decode("utf-8"))
        assert started["status"] == "awaiting_decision"

        action_body = json.dumps({"type": "manual_move", "move": "C"}).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/api/action",
            data=action_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req):
            pass

        req = Request(f"http://127.0.0.1:{port}/api/run/export", method="POST")
        with urlopen(req) as resp:
            exported = json.loads(resp.read().decode("utf-8"))
        assert exported["save_code"]
        assert exported["secret_mode"] in {"configured_shared_secret", "process_local_fallback"}

        req = Request(f"http://127.0.0.1:{port}/api/run/clear", method="POST")
        with urlopen(req):
            pass
        with urlopen(f"http://127.0.0.1:{port}/api/state") as resp:
            cleared = json.loads(resp.read().decode("utf-8"))
        assert cleared["status"] == "not_started"

        import_body = json.dumps({"save_code": exported["save_code"]}).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/api/run/import",
            data=import_body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req) as resp:
            restored = json.loads(resp.read().decode("utf-8"))
        assert restored["status"] == "awaiting_decision"
        assert restored["snapshot"]["latest_featured_round"] is not None
    finally:
        server.shutdown()
        server.server_close()


def test_web_api_rejects_malformed_import_payload_cleanly() -> None:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        bad_import = json.dumps({"state": {"version": 1, "seed": 7}}).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}/api/run/import",
            data=bad_import,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as exc_info:
            urlopen(req)

        assert exc_info.value.code == 400
        body = json.loads(exc_info.value.read().decode("utf-8"))
        assert body["error"] == "missing save payload"
    finally:
        server.shutdown()
        server.server_close()


def test_web_api_rejects_tampered_save_code_payload() -> None:
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        req = Request(f"http://127.0.0.1:{port}/api/run/start", method="POST")
        with urlopen(req):
            pass

        req = Request(f"http://127.0.0.1:{port}/api/run/export", method="POST")
        with urlopen(req) as resp:
            exported = json.loads(resp.read().decode("utf-8"))

        tampered = exported["save_code"][:-1] + ("A" if exported["save_code"][-1] != "A" else "B")
        req = Request(
            f"http://127.0.0.1:{port}/api/run/import",
            data=json.dumps({"save_code": tampered}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as exc_info:
            urlopen(req)

        body = json.loads(exc_info.value.read().decode("utf-8"))
        assert exc_info.value.code == 400
        assert body["error"] == "invalid save payload"
    finally:
        server.shutdown()
        server.server_close()


def test_web_api_export_import_portable_with_configured_shared_secret(monkeypatch) -> None:
    from http.server import ThreadingHTTPServer

    monkeypatch.setenv("PG_WEB_SAVE_SECRET", "shared-secret-for-test")
    server_a = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_b = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port_a = server_a.server_address[1]
    port_b = server_b.server_address[1]
    thread_a = threading.Thread(target=server_a.serve_forever, daemon=True)
    thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
    thread_a.start()
    thread_b.start()

    try:
        req = Request(f"http://127.0.0.1:{port_a}/api/run/start", method="POST")
        with urlopen(req):
            pass
        req = Request(f"http://127.0.0.1:{port_a}/api/run/export", method="POST")
        with urlopen(req) as resp:
            exported = json.loads(resp.read().decode("utf-8"))
        assert exported["secret_mode"] == "configured_shared_secret"

        req = Request(
            f"http://127.0.0.1:{port_b}/api/run/import",
            data=json.dumps({"save_code": exported["save_code"]}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req) as resp:
            restored = json.loads(resp.read().decode("utf-8"))
        assert restored["status"] in {"awaiting_decision", "running", "completed"}
    finally:
        server_a.shutdown()
        server_a.server_close()
        server_b.shutdown()
        server_b.server_close()


def test_web_api_export_uses_process_local_fallback_without_configured_secret(monkeypatch) -> None:
    from http.server import ThreadingHTTPServer

    monkeypatch.delenv("PG_WEB_SAVE_SECRET", raising=False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        req = Request(f"http://127.0.0.1:{port}/api/run/start", method="POST")
        with urlopen(req):
            pass
        req = Request(f"http://127.0.0.1:{port}/api/run/export", method="POST")
        with urlopen(req) as resp:
            exported = json.loads(resp.read().decode("utf-8"))
        assert exported["secret_mode"] == "process_local_fallback"
    finally:
        server.shutdown()
        server.server_close()


def _always_defect_genome() -> StrategyGenome:
    return StrategyGenome(
        first_move=DEFECT,
        response_table={(COOPERATE, COOPERATE): DEFECT, (COOPERATE, DEFECT): DEFECT, (DEFECT, COOPERATE): DEFECT, (DEFECT, DEFECT): DEFECT},
        noise=0.0,
    )


def test_web_runtime_forced_cooperation_combo_is_consumed_in_featured_round_flow() -> None:
    session = FeaturedMatchWebSession(seed=41, rounds=2)
    session.start()
    session.player.powerups = [CoerciveControl(), ComplianceDividend(bonus=1)]
    session.opponent.genome = StrategyGenome(
        first_move=COOPERATE,
        response_table={(COOPERATE, COOPERATE): DEFECT, (COOPERATE, DEFECT): DEFECT, (DEFECT, COOPERATE): DEFECT, (DEFECT, DEFECT): DEFECT},
        noise=0.0,
    )

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=DEFECT))
    session.advance()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=DEFECT))
    session.advance()

    latest = session.view()["snapshot"]["latest_featured_round"]
    assert latest is not None
    sources = [entry["source"] for entry in latest["breakdown"]["score_adjustments"]]
    assert "Coercive Control" in sources
    assert "Compliance Dividend" in sources


def test_web_runtime_locked_coop_trust_combo_is_consumed() -> None:
    session = FeaturedMatchWebSession(seed=43, rounds=1)
    session.start()
    session.player.powerups = [GoldenHandshake(), TrustDividend()]
    session.opponent.genome = _always_defect_genome()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=DEFECT))
    session.advance()

    latest = session.view()["snapshot"]["latest_featured_round"]
    assert latest is not None
    sources = [entry["source"] for entry in latest["breakdown"]["score_adjustments"]]
    assert "Trust Dividend" in sources


def test_web_runtime_retaliation_spiral_combo_is_consumed() -> None:
    session = FeaturedMatchWebSession(seed=47, rounds=3)
    session.start()
    session.player.powerups = [SpiteEngine(), PanicButton()]
    session.opponent.genome = _always_defect_genome()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=DEFECT))
    session.advance()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=DEFECT))
    session.advance()

    latest = session.view()["snapshot"]["latest_featured_round"]
    assert latest is not None
    sources = [entry["source"] for entry in latest["breakdown"]["score_adjustments"]]
    assert "Spite Engine" in sources
    assert "Panic Button" in sources


def test_web_runtime_referendum_controlled_vote_bloc_combo_is_consumed() -> None:
    session = FeaturedMatchWebSession(seed=53, rounds=1)
    session.start()
    session.player.powerups = [UnityTicket(), BlocPolitics(bonus=2)]

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    assert session.view()["decision_type"] == "FloorVoteDecisionState"

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=DEFECT))
    session.advance()

    vote_result = session.view()["snapshot"]["floor_vote_result"]
    assert vote_result is not None
    assert vote_result["player_vote"] == COOPERATE
    assert vote_result["player_reward"] >= 6


def test_web_referendum_counts_are_derived_from_branch_roster_votes() -> None:
    session = FeaturedMatchWebSession(seed=29, rounds=1)
    session.start()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    assert session.view()["decision_type"] == "FloorVoteDecisionState"

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    vote_result = session.view()["snapshot"]["floor_vote_result"]
    assert vote_result is not None
    assert vote_result["cooperators"] + vote_result["defectors"] == len(session._branch_roster)


def test_web_floor_progression_accounts_featured_and_non_featured_pairs_exactly_once() -> None:
    session = FeaturedMatchWebSession(seed=31, rounds=1)
    session.start()

    session.player.powerups = []
    for agent in session._branch_roster:
        agent.powerups = []
        agent.genome = _always_defect_genome()

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()

    call_pairs: list[frozenset[int]] = []
    expected_scores = {agent.agent_id: 0 for agent in session._branch_roster}
    expected_wins = {agent.agent_id: 0 for agent in session._branch_roster}

    # Featured pairing already resolved in the interactive rounds.
    expected_scores[session.player.agent_id] += session.player_score
    expected_scores[session.opponent.agent_id] += session.opponent_score
    if session.player_score > session.opponent_score:
        expected_wins[session.player.agent_id] += 1
    elif session.opponent_score > session.player_score:
        expected_wins[session.opponent.agent_id] += 1

    def fake_play_match(*, left, right, rounds_per_match=None):
        call_pairs.append(frozenset((left.agent_id, right.agent_id)))
        left_score = left.agent_id % 3 + 1
        right_score = right.agent_id % 2
        expected_scores[left.agent_id] += left_score
        expected_scores[right.agent_id] += right_score
        if left_score > right_score:
            expected_wins[left.agent_id] += 1
        elif right_score > left_score:
            expected_wins[right.agent_id] += 1
        return MatchResult(left_score=left_score, right_score=right_score)

    session._tournament.play_match = fake_play_match  # type: ignore[method-assign]

    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=DEFECT))
    session.advance()

    featured_pair = frozenset((session.player.agent_id, session.opponent.agent_id))
    all_pairs = {
        frozenset((left.agent_id, right.agent_id))
        for idx, left in enumerate(session._branch_roster)
        for right in session._branch_roster[idx + 1 :]
    }
    expected_non_featured_pairs = all_pairs - {featured_pair}

    assert set(call_pairs) == expected_non_featured_pairs
    assert len(call_pairs) == len(expected_non_featured_pairs)

    for agent in session._branch_roster:
        assert agent.score == expected_scores[agent.agent_id]
        assert agent.wins == expected_wins[agent.agent_id]

    assert session.opponent.score >= session.opponent_score
    assert session.opponent.wins >= 1


def test_web_session_initializes_house_doctrine_from_seed() -> None:
    session_a = FeaturedMatchWebSession(seed=41, rounds=1)
    session_b = FeaturedMatchWebSession(seed=41, rounds=1)
    session_c = FeaturedMatchWebSession(seed=42, rounds=1)

    session_a.start()
    session_b.start()
    session_c.start()

    snapshot_a = session_a.view()["snapshot"]
    snapshot_b = session_b.view()["snapshot"]
    snapshot_c = session_c.view()["snapshot"]

    assert snapshot_a["house_doctrine_family"] == snapshot_b["house_doctrine_family"]
    assert snapshot_a["house_doctrine_family"] != snapshot_c["house_doctrine_family"]
    assert snapshot_a["primary_doctrine_family"] is not None


def test_web_snapshot_surfaces_doctrine_identity_chip() -> None:
    session = FeaturedMatchWebSession(seed=21, rounds=1)
    session.start()

    chips = session.view()["snapshot"]["strategic_snapshot"]["chips"]
    assert any(str(chip).startswith("Doctrine: ") for chip in chips)


def test_web_house_doctrine_stays_stable_across_floor_progression() -> None:
    session = FeaturedMatchWebSession(seed=17, rounds=1)
    session.start()
    house = session.view()["snapshot"]["house_doctrine_family"]

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()

    assert session.view()["snapshot"]["current_floor"] == 2
    assert session.view()["snapshot"]["house_doctrine_family"] == house


def test_successor_and_chronicle_surface_doctrine_mutation_framing() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.snapshot.house_doctrine_family = "trust"
    session.snapshot.primary_doctrine_family = "control"
    session.snapshot.secondary_doctrine_family = "retaliation"

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()

    decision = session.view()["decision"]
    assert decision is not None
    assert "Doctrine status:" in str(decision.get("lineage_doctrine"))

    chronicle = session.view()["snapshot"]["lineage_chronicle"]
    doctrine_entries = [entry for entry in chronicle if entry["event_type"] in {"doctrine_pivot", "successor_pressure"}]
    assert doctrine_entries
    assert any("Doctrine status:" in entry["summary"] for entry in doctrine_entries)


def test_civil_war_context_includes_doctrine_mutation_pressure_note() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.snapshot.house_doctrine_family = "trust"
    session.snapshot.primary_doctrine_family = "control"
    session.snapshot.secondary_doctrine_family = "retaliation"

    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.snapshot.floor_summary.heir_pressure.future_threats = []
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    context = session.view()["snapshot"]["civil_war_context"]
    assert context is not None
    assert context["doctrine_pressure"]
    assert "Doctrine" in context["doctrine_pressure"][0] or "doctrine" in context["doctrine_pressure"][0]
