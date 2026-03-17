from __future__ import annotations

import dataclasses
import json
import logging
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
    FeaturedRoundDecisionState,
    ROUND_STANCES_REQUIRING_ROUNDS,
)
from prisoners_gambit.config.settings import Settings
from prisoners_gambit.web.ui_resources import render_web_app
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

_log = logging.getLogger(__name__)

_stance_options_default: tuple[str, ...] = next(
    (f.default for f in dataclasses.fields(FeaturedRoundDecisionState) if f.name == "stance_options"),  # type: ignore[assignment]
    (),
)
_ROUND_STANCE_OPTIONS = set(_stance_options_default)
_ROUND_STANCES_REQUIRING_ROUNDS = ROUND_STANCES_REQUIRING_ROUNDS
_MAX_REQUEST_BODY_BYTES = 16 * 1024  # JSON action payloads are tiny; cap bodies to reject malformed or abusive requests early.
_PROCESS_LOCAL_SAVE_SECRET = secrets.token_bytes(32)
_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8765


def _new_web_session() -> FeaturedMatchWebSession:
    settings = Settings.from_env()
    seed = settings.seed if settings.seed is not None else secrets.randbelow(2**63)
    return FeaturedMatchWebSession(
        seed=seed,
        rounds=settings.rounds_per_match,
        survivor_count=min(settings.survivor_count, 4),
        floor_cap=settings.floors,
        mutation_rate=settings.mutation_rate,
        descendant_mutation_bonus=settings.descendant_mutation_bonus,
    )


def _current_save_secret() -> bytes:
    configured_secret = os.getenv("PG_WEB_SAVE_SECRET")
    if configured_secret:
        return configured_secret.encode("utf-8")
    # Fallback keeps integrity checks active in local/dev use, but exported save codes
    # are portable only for this process lifetime unless PG_WEB_SAVE_SECRET is shared.
    return _PROCESS_LOCAL_SAVE_SECRET


def _save_secret_mode() -> str:
    return "configured_shared_secret" if os.getenv("PG_WEB_SAVE_SECRET") else "process_local_fallback"


def _port_from_env(default_port: int = _DEFAULT_PORT) -> int:
    configured_port = os.getenv("PORT")
    if configured_port is None:
        return default_port
    try:
        parsed_port = int(configured_port)
    except ValueError:
        _log.warning("Invalid PORT value %r; falling back to %d", configured_port, default_port)
        return default_port
    if parsed_port <= 0:
        _log.warning("Non-positive PORT value %r; falling back to %d", configured_port, default_port)
        return default_port
    return parsed_port


def _parse_json_body(handler: "Handler") -> tuple[dict | None, int, dict | None]:
    try:
        raw_length = handler.headers.get("Content-Length", "0")
        length = int(raw_length)
        if length < 0:
            raise ValueError("Content-Length cannot be negative")
    except ValueError:
        handler.close_connection = True
        return None, 400, {"error": "invalid Content-Length"}
    if length > _MAX_REQUEST_BODY_BYTES:
        handler.close_connection = True
        return None, 413, {"error": "request body too large"}
    raw_bytes = handler.rfile.read(length) if length else b"{}"
    try:
        raw = raw_bytes.decode("utf-8")
        payload = json.loads(raw)
    except UnicodeDecodeError:
        handler.close_connection = True
        return None, 400, {"error": "invalid UTF-8 in request body"}
    except json.JSONDecodeError:
        return None, 400, {"error": "invalid JSON"}
    if not isinstance(payload, dict):
        return None, 400, {"error": "invalid action payload"}
    return payload, 200, None


class Handler(BaseHTTPRequestHandler):
    def _state_lock(self) -> threading.RLock:
        lock = getattr(self.server, "_prisoners_gambit_lock", None)
        if lock is None:
            lock = threading.RLock()
            setattr(self.server, "_prisoners_gambit_lock", lock)
        return lock

    def _get_session(self) -> FeaturedMatchWebSession | None:
        return getattr(self.server, "_prisoners_gambit_session", None)

    def _set_session(self, session: FeaturedMatchWebSession | None) -> None:
        setattr(self.server, "_prisoners_gambit_session", session)

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if getattr(self, "close_connection", False):
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            selected_language = parse_qs(parsed.query).get("lang", ["en"])[0]
            body = render_web_app(language=selected_language).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/state":
            with self._state_lock():
                session = self._get_session()
                if session is None:
                    payload = {"status": "not_started", "decision": None, "decision_type": None, "snapshot": {}}
                else:
                    payload = session.view()
            self._json(payload)
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        if self.path == "/api/run/start":
            with self._state_lock():
                session = _new_web_session()
                session.start()
                self._set_session(session)
                payload = session.view()
            self._json(payload)
            return

        if self.path == "/api/run/clear":
            with self._state_lock():
                self._set_session(None)
            self._json({"status": "cleared"})
            return

        if self.path == "/api/run/export":
            with self._state_lock():
                session = self._get_session()
                if session is None:
                    self._json({"error": "session not started"}, status=400)
                    return
                save_secret = _current_save_secret()
                self._json(
                    {
                        "save_code": session.export_save_code(save_secret),
                        "secret_mode": _save_secret_mode(),
                    }
                )
            return

        if self.path == "/api/run/import":
            payload, status, err = _parse_json_body(self)
            if err is not None:
                self._json(err, status=status)
                return
            try:
                save_code = payload.get("save_code")
                save_secret = _current_save_secret()
                if isinstance(save_code, str) and save_code:
                    session = FeaturedMatchWebSession.import_save_code(save_code, save_secret)
                else:
                    self._json({"error": "missing save payload"}, status=400)
                    return
            except (ValueError, TypeError, KeyError) as exc:
                _log.warning("Invalid save import payload: %s", exc)
                self._json({"error": "invalid save payload"}, status=400)
                return

            with self._state_lock():
                self._set_session(session)
                view = session.view()
            self._json(view)
            return

        if self.path == "/api/advance":
            with self._state_lock():
                session = self._get_session()
                if session is None:
                    payload = {"error": "session not started"}
                    status = 400
                else:
                    session.advance()
                    payload = session.view()
                    status = 200
            self._json(payload, status=status)
            return

        if self.path != "/api/action":
            self._json({"error": "not found"}, status=404)
            return

        payload, status, err = _parse_json_body(self)
        if err is not None:
            self._json(err, status=status)
            return
        action_type = payload.get("type")

        try:
            if action_type == "manual_move":
                move_str = payload.get("move")
                if move_str not in ("C", "D"):
                    self._json({"error": "invalid move; expected 'C' or 'D'"}, status=400)
                    return
                move = COOPERATE if move_str == "C" else DEFECT
                action = ChooseRoundMoveAction(mode="manual_move", move=move)
            elif action_type in {"autopilot_round", "autopilot_match"}:
                action = ChooseRoundAutopilotAction(mode=action_type)
            elif action_type == "set_round_stance":
                stance = payload.get("stance")
                if stance not in _ROUND_STANCE_OPTIONS:
                    self._json({"error": "invalid stance"}, status=400)
                    return
                rounds = None
                raw_rounds = payload.get("rounds")
                if raw_rounds is not None:
                    if isinstance(raw_rounds, bool):
                        self._json({"error": "invalid rounds"}, status=400)
                        return
                    if isinstance(raw_rounds, int):
                        rounds = raw_rounds
                    elif isinstance(raw_rounds, str) and raw_rounds.isdigit():
                        rounds = int(raw_rounds)
                    else:
                        self._json({"error": "invalid rounds"}, status=400)
                        return
                    if rounds <= 0:
                        self._json({"error": "invalid rounds"}, status=400)
                        return
                if stance in _ROUND_STANCES_REQUIRING_ROUNDS and rounds is None:
                    self._json({"error": "rounds required for selected stance"}, status=400)
                    return
                # Non-duration stances run until cleared; ignore any provided rounds.
                if stance not in _ROUND_STANCES_REQUIRING_ROUNDS:
                    rounds = None
                action = ChooseRoundStanceAction(
                    mode="set_round_stance",
                    stance=stance,
                    rounds=rounds,
                )
            elif action_type == "manual_vote":
                vote_raw = payload.get("vote")
                if vote_raw not in ("C", "D"):
                    self._json({"error": "invalid vote; expected 'C' or 'D'"}, status=400)
                    return
                vote = COOPERATE if vote_raw == "C" else DEFECT
                action = ChooseFloorVoteAction(mode="manual_vote", vote=vote)
            elif action_type == "autopilot_vote":
                action = ChooseFloorVoteAction(mode="autopilot_vote")
            elif action_type == "choose_powerup":
                action = ChoosePowerupAction(offer_index=int(payload.get("offer_index", -1)))
            elif action_type == "choose_genome_edit":
                action = ChooseGenomeEditAction(offer_index=int(payload.get("offer_index", -1)))
            elif action_type == "choose_successor":
                action = ChooseSuccessorAction(candidate_index=int(payload.get("candidate_index", -1)))
            else:
                self._json({"error": "invalid action"}, status=400)
                return

            with self._state_lock():
                session = self._get_session()
                if session is None:
                    payload = {"error": "session not started"}
                    status = 400
                else:
                    session.submit_action(action)
                    session.advance()
                    payload = session.view()
                    status = 200
        except (ValueError, TypeError, RuntimeError) as exc:
            _log.warning("Client error in /api/action: %s", exc)
            self._json({"error": "invalid request"}, status=400)
            return
        except Exception:  # noqa: BLE001
            _log.exception("Unhandled error in /api/action")
            self._json({"error": "internal server error"}, status=500)
            return

        self._json(payload, status=status)


def run_server(port: int = _DEFAULT_PORT, host: str = _DEFAULT_HOST) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    setattr(server, "_prisoners_gambit_session", None)
    setattr(server, "_prisoners_gambit_lock", threading.RLock())
    print(f"Web slice running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server(port=_port_from_env())
