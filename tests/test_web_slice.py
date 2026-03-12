import json
import http.client
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
)
from prisoners_gambit.web.server import Handler, _port_from_env, run_server
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

TEST_PADDING_LENGTH = 20_000


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
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
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


def test_web_session_dynasty_board_marks_civil_war_danger_after_successor_choice() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    board_entries = session.view()["snapshot"]["dynasty_board"]["entries"]
    assert board_entries
    assert any(entry["is_current_host"] for entry in board_entries)
    assert any(entry["has_civil_war_danger"] for entry in board_entries)
    assert any(entry.get("civil_war_danger_cause", "").startswith("because ") for entry in board_entries if entry["has_civil_war_danger"])


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
    assert session.view()["pending_screen"] == "civil_war_transition"
    civil_war_context = session.view()["snapshot"]["civil_war_context"]
    assert civil_war_context is not None
    assert civil_war_context["scoring_rules"]
    assert session.view()["snapshot"]["floor_vote_result"] is None

    session.advance()
    assert session.view()["decision_type"] == "PowerupChoiceState"
    powerup_offer = session.view()["decision"]["offers"][0]
    assert {"lineage_commitment", "doctrine_vector", "branch_identity", "tradeoff", "phase_support", "successor_pressure"}.issubset(powerup_offer.keys())

    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    assert session.view()["decision_type"] == "GenomeEditChoiceState"
    genome_offer = session.view()["decision"]["offers"][0]
    assert {"lineage_commitment", "doctrine_vector", "branch_identity", "tradeoff", "phase_support", "successor_pressure", "doctrine_drift"}.issubset(genome_offer.keys())

    session.submit_action(ChooseGenomeEditAction(offer_index=0))
    session.advance()
    assert session.view()["status"] == "completed"
    assert session.view()["snapshot"]["completion"] is not None


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
