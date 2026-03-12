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
from prisoners_gambit.web.server import Handler, run_server
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


def test_run_server_defaults_to_loopback_host(monkeypatch) -> None:
    captured = {}

    class FakeServer:
        def __init__(self, address, handler):
            captured["address"] = address
            captured["handler"] = handler

        def serve_forever(self):
            captured["served"] = True

    monkeypatch.setattr("prisoners_gambit.web.server.ThreadingHTTPServer", FakeServer)

    run_server(port=9999)

    assert captured["address"] == ("127.0.0.1", 9999)
    assert captured["handler"] is Handler
    assert captured["served"] is True


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
