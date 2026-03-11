import json
import threading
from urllib.request import Request, urlopen

from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
)
from prisoners_gambit.web.server import Handler
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession


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

    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()
    assert session.view()["pending_screen"] == "civil_war_transition"

    session.advance()
    assert session.view()["decision_type"] == "PowerupChoiceState"

    session.submit_action(ChoosePowerupAction(offer_index=0))
    session.advance()
    assert session.view()["decision_type"] == "GenomeEditChoiceState"

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
