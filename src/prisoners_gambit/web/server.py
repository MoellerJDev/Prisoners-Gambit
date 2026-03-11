from __future__ import annotations

import dataclasses
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

_log = logging.getLogger(__name__)

_stance_options_default: tuple[str, ...] = next(
    (f.default for f in dataclasses.fields(FeaturedRoundDecisionState) if f.name == "stance_options"),  # type: ignore[assignment]
    (),
)
_ROUND_STANCE_OPTIONS = set(_stance_options_default)
_ROUND_STANCES_REQUIRING_ROUNDS = ROUND_STANCES_REQUIRING_ROUNDS
_MAX_REQUEST_BODY_BYTES = 16 * 1024  # JSON action payloads are tiny; cap bodies to reject malformed or abusive requests early.


HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>Prisoner's Gambit Web Prototype</title>
  <style>
    :root {
      --bg:#0a0f17;
      --bg-alt:#0f1623;
      --panel:#171f2d;
      --panel-2:#202b3e;
      --text:#eaf0ff;
      --muted:#9eb0d3;
      --border:#31425e;
      --accent:#87bfff;
      --branch:#c4a5ff;
      --powerup:#ffd37f;
      --genome:#83e0cb;
      --effect:#f8a5ff;
      --good:#89ef96;
      --danger:#ff8b90;
      --warn:#ffd08b;
      --shadow:0 14px 34px rgba(0,0,0,.35);
    }
    * { box-sizing:border-box; }
    body {
      margin:0;
      color:var(--text);
      font-family:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background:
        radial-gradient(1400px 700px at 20% -200px, rgba(132,169,255,.14), transparent 70%),
        radial-gradient(1200px 600px at 100% 0, rgba(180,120,255,.12), transparent 65%),
        linear-gradient(180deg, var(--bg), var(--bg-alt));
      min-height:100vh;
    }
    .wrap { max-width:1200px; margin:0 auto; padding:22px; }
    .header-title { margin:0 0 4px; letter-spacing:.4px; }
    .sub { color:var(--muted); margin-bottom:14px; }
    .grid { display:grid; grid-template-columns:1.35fr 1fr; gap:14px; }
    .panel {
      background:linear-gradient(180deg, color-mix(in oklab, var(--panel), black 3%), var(--panel-2));
      border:1px solid var(--border);
      border-radius:12px;
      padding:14px;
      box-shadow:var(--shadow);
      position:relative;
      overflow:hidden;
    }
    .panel::after {
      content:"";
      position:absolute;
      inset:0;
      background:linear-gradient(140deg, rgba(255,255,255,.04), transparent 40%);
      pointer-events:none;
    }
    h3 { margin:0 0 10px; font-size:12px; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); }
    .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .pill {
      border:1px solid var(--border);
      background:#111a2a;
      border-radius:999px;
      padding:5px 10px;
      color:var(--muted);
      font-size:13px;
    }
    .token {
      display:inline-flex;
      align-items:center;
      gap:6px;
      font-size:12px;
      border-radius:999px;
      border:1px solid;
      padding:4px 9px;
      background:#101726;
    }
    .token.branch { border-color:color-mix(in oklab, var(--branch), #000 40%); color:var(--branch); }
    .token.powerup { border-color:color-mix(in oklab, var(--powerup), #000 40%); color:var(--powerup); }
    .token.genome { border-color:color-mix(in oklab, var(--genome), #000 40%); color:var(--genome); }
    .token.effect { border-color:color-mix(in oklab, var(--effect), #000 40%); color:var(--effect); }

    .btn {
      border:1px solid var(--border);
      border-radius:9px;
      padding:8px 12px;
      cursor:pointer;
      background:#1b2639;
      color:var(--text);
      transition:transform .12s ease, border-color .15s ease, background .15s ease;
    }
    .btn:hover { transform:translateY(-1px); border-color:var(--accent); background:#24334d; }
    .btn:active { transform:translateY(0); }

    .kv { display:grid; grid-template-columns:180px 1fr; row-gap:7px; column-gap:10px; }
    .muted { color:var(--muted); }
    .list { margin:0; padding-left:18px; }
    .list li { margin-bottom:6px; }
    .list.tight li { margin-bottom:3px; }

    .scoreline { font-size:20px; font-weight:700; }
    .scoreline .good { color:var(--good); }
    .scoreline .danger { color:var(--danger); }
    .good{ color:var(--good); }
    .danger{ color:var(--danger); }
    .warn{ color:var(--warn); }

    .fx-item {
      border-left:3px solid var(--effect);
      padding-left:9px;
      margin:6px 0;
      color:var(--muted);
      animation:reveal .22s ease;
    }
    .panel-enter { animation:panel-enter .22s ease; }
    .score-pop { animation:score-pop .35s ease; }

    pre {
      margin:0;
      background:#0b111c;
      border:1px solid var(--border);
      border-radius:8px;
      padding:10px;
      max-height:220px;
      overflow:auto;
      font-size:12px;
      color:#ccdbfb;
    }

    @keyframes reveal { from { opacity:0; transform:translateY(4px);} to {opacity:1; transform:translateY(0);} }
    @keyframes panel-enter { from { opacity:0; transform:translateY(6px);} to {opacity:1; transform:translateY(0);} }
    @keyframes score-pop { 0%{transform:scale(1);} 40%{transform:scale(1.06);} 100%{transform:scale(1);} }

    @media (prefers-reduced-motion: reduce) {
      .fx-item, .panel-enter, .score-pop, .btn { animation:none; transition:none; }
    }

    @media(max-width:960px){ .grid { grid-template-columns:1fr; } }
  </style>
</head>
<body>
<div class='wrap'>
  <h1 class='header-title'>Prisoner's Gambit</h1>
  <div class='sub'>Full-run web prototype with typed decisions and atmospheric table-style UI.</div>

  <div class='panel panel-enter'>
    <div class='row'>
      <button class='btn' onclick='startRun()'>Start Run</button>
      <button class='btn' onclick='advanceFlow()'>Continue Screen</button>
      <span id='status' class='pill'>status: not_started</span>
      <span id='phase' class='pill'>phase: -</span>
      <span id='floor' class='pill'>floor: -</span>
      <span id='activeStance' class='pill'>stance: none</span>
    </div>
  </div>

  <div class='grid'>
    <div class='panel panel-enter'>
      <h3>Current Decision</h3>
      <div id='decisionType' class='muted'>No decision yet.</div>
      <div id='decisionView' class='kv muted' style='margin-top:10px;'>Start run to begin.</div>
      <div id='actions' class='row' style='margin-top:10px;'></div>
      <div id='pending' class='warn' style='margin-top:8px;'></div>
    </div>

    <div class='panel panel-enter'>
      <h3>Latest Round Result</h3>
      <div id='roundResult' class='muted'>No rounds resolved yet.</div>
      <div id='roundEffects' class='muted' style='margin-top:10px;'></div>
    </div>

    <div class='panel panel-enter'>
      <h3>Floor Referendum</h3>
      <div id='voteResult' class='muted'>No vote yet.</div>
    </div>

    <div class='panel panel-enter'>
      <h3>Floor Summary</h3>
      <ul id='floorSummary' class='list muted'><li>No summary yet.</li></ul>
    </div>

    <div class='panel panel-enter'>
      <h3>Successor Options</h3>
      <ul id='successors' class='list muted'><li>No successor choice active.</li></ul>
    </div>

    <div class='panel panel-enter'>
      <h3>Run Completion</h3>
      <div id='completion' class='muted'>Run in progress.</div>
    </div>
  </div>

  <div class='panel panel-enter' style='margin-top:14px;'>
    <h3>Raw State</h3>
    <pre id='stateJson'>{}</pre>
  </div>
</div>
<script>
let latest = null;
let previousTotals = null;

function escapeHtml(s){ const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; }
function moveLabel(v){ return v === 0 ? 'C' : 'D'; }
function effectToken(label){ return `<span class='token effect'>✦ ${escapeHtml(label)}</span>`; }
function branchToken(label){ return `<span class='token branch'>⎇ ${escapeHtml(label)}</span>`; }
function powerupToken(label){ return `<span class='token powerup'>⚡ ${escapeHtml(label)}</span>`; }
function genomeToken(label){ return `<span class='token genome'>🧬 ${escapeHtml(label)}</span>`; }

function renderDecision(data){
  const decision = data.decision;
  const t = data.decision_type;
  const actions = document.getElementById('actions');
  actions.innerHTML = '';
  document.getElementById('decisionType').textContent = t ? `Decision: ${t}` : 'No active decision.';
  if (!decision) {
    document.getElementById('decisionView').innerHTML = 'No active decision.';
    return;
  }

  if (t === 'FeaturedRoundDecisionState') {
    const p = decision.prompt;
    document.getElementById('decisionView').innerHTML = `
      <div>Opponent</div><div>${branchToken(p.masked_opponent_label)}</div>
      <div>Round</div><div>${p.round_index + 1}/${p.total_rounds}</div>
      <div>Score</div><div class='scoreline'>You <span class='good'>${p.my_match_score}</span> : <span class='danger'>${p.opp_match_score}</span> Opp</div>
      <div>Suggested</div><div>${effectToken(`Autopilot recommends ${moveLabel(p.suggested_move)}`)}</div>`;
    actions.innerHTML = `
      <button class='btn' onclick="sendAction({type:'manual_move', move:'C'})">Cooperate</button>
      <button class='btn' onclick="sendAction({type:'manual_move', move:'D'})">Defect</button>
      <button class='btn' onclick="sendAction({type:'autopilot_round'})">Autopilot Round</button>
      <button class='btn' onclick="sendAction({type:'set_round_stance', stance:'cooperate_until_betrayed'})">C until betrayed</button>
      <button class='btn' onclick="sendAction({type:'set_round_stance', stance:'defect_until_punished'})">D until punished</button>
      <button class='btn' onclick="sendStanceN('follow_autopilot_for_n_rounds')">Autopilot N</button>
      <button class='btn' onclick="sendStanceN('lock_last_manual_move_for_n_rounds')">Lock last N</button>`;
    return;
  }

  if (t === 'FloorVoteDecisionState') {
    const p = decision.prompt;
    document.getElementById('decisionView').innerHTML = `
      <div>Floor</div><div>${p.floor_number} (${escapeHtml(p.floor_label)})</div>
      <div>Suggested Vote</div><div>${effectToken(`Model suggests ${moveLabel(p.suggested_vote)}`)}</div>
      <div>Floor Score</div><div>${p.current_floor_score}</div>
      <div>Powerups</div><div>${(p.powerups || []).map(powerupToken).join(' ') || 'none'}</div>`;
    actions.innerHTML = `
      <button class='btn' onclick="sendAction({type:'manual_vote', vote:'C'})">Vote Cooperate</button>
      <button class='btn' onclick="sendAction({type:'manual_vote', vote:'D'})">Vote Defect</button>
      <button class='btn' onclick="sendAction({type:'autopilot_vote'})">Autopilot Vote</button>`;
    return;
  }

  if (t === 'PowerupChoiceState') {
    document.getElementById('decisionView').innerHTML = `<div>Floor</div><div>${decision.floor_number}</div><div>Offers</div><div>${decision.offers.length}</div>`;
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = 'btn';
      btn.innerHTML = `${idx + 1}. ${powerupToken(offer.name)}`;
      btn.onclick = () => sendAction({type:'choose_powerup', offer_index: idx});
      actions.appendChild(btn);
    });
    return;
  }

  if (t === 'GenomeEditChoiceState') {
    document.getElementById('decisionView').innerHTML = `
      <div>Floor</div><div>${decision.floor_number}</div>
      <div>Current Genome</div><div>${genomeToken(decision.current_summary)}</div>`;
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = 'btn';
      btn.innerHTML = `${idx + 1}. ${genomeToken(offer.name)}`;
      btn.onclick = () => sendAction({type:'choose_genome_edit', offer_index: idx});
      actions.appendChild(btn);
    });
    return;
  }

  if (t === 'SuccessorChoiceState') {
    document.getElementById('decisionView').innerHTML = `<div>Floor</div><div>${decision.floor_number}</div><div>Candidates</div><div>${decision.candidates.length}</div>`;
    decision.candidates.forEach((candidate, idx) => {
      const btn = document.createElement('button');
      btn.className = 'btn';
      btn.innerHTML = `${idx + 1}. ${branchToken(candidate.name)} (${candidate.score}/${candidate.wins})`;
      btn.onclick = () => sendAction({type:'choose_successor', candidate_index: idx});
      actions.appendChild(btn);
    });
  }
}

function renderRoundEffects(round) {
  const root = document.getElementById('roundEffects');
  if (!round) {
    root.innerHTML = '';
    return;
  }
  const modifiers = round.breakdown?.score_adjustments || [];
  const modifierLines = modifiers.length
    ? modifiers.map(entry => `<div class='fx-item'>${powerupToken(entry.source)} → You ${entry.player_delta >= 0 ? '+' : ''}${entry.player_delta}, Opp ${entry.opponent_delta >= 0 ? '+' : ''}${entry.opponent_delta}</div>`).join('')
    : `<div class='fx-item muted'>No score modifiers this round.</div>`;
  root.innerHTML = `
    <div class='fx-item'>${effectToken(`Directive: You ${round.player_reason}`)}</div>
    <div class='fx-item'>${effectToken(`Directive: Opp ${round.opponent_reason}`)}</div>
    ${modifierLines}`;
}

function renderSnapshot(snapshot){
  document.getElementById('phase').textContent = `phase: ${snapshot.current_phase || '-'}`;
  document.getElementById('floor').textContent = `floor: ${snapshot.current_floor || '-'}`;

  const stance = snapshot.active_featured_stance;
  document.getElementById('activeStance').textContent = stance
    ? `stance: ${stance.stance} (${stance.rounds_remaining ?? '∞'})`
    : 'stance: none';

  const round = snapshot.latest_featured_round;
  const roundResult = document.getElementById('roundResult');
  if (round) {
    const totals = `${round.player_total}:${round.opponent_total}`;
    const deltaClass = previousTotals && previousTotals !== totals ? 'score-pop' : '';
    roundResult.className = deltaClass;
    previousTotals = totals;
    roundResult.innerHTML = `
      <div class='kv'>
        <div>Round</div><div>${round.round_index + 1}/${round.total_rounds}</div>
        <div>Moves</div><div>You ${moveLabel(round.player_move)} vs Opp ${moveLabel(round.opponent_move)}</div>
        <div>Round Delta</div><div><span class='good'>${round.player_delta >= 0 ? '+' : ''}${round.player_delta}</span> / <span class='danger'>${round.opponent_delta >= 0 ? '+' : ''}${round.opponent_delta}</span></div>
        <div>Match Total</div><div class='scoreline'><span class='good'>${round.player_total}</span> : <span class='danger'>${round.opponent_total}</span></div>
      </div>`;
  } else {
    roundResult.className = 'muted';
    roundResult.textContent = 'No rounds resolved yet.';
  }
  renderRoundEffects(round);

  const vote = snapshot.floor_vote_result;
  document.getElementById('voteResult').innerHTML = vote
    ? `${effectToken(`Vote ${moveLabel(vote.player_vote)}`)} — cooperators ${vote.cooperators}, defectors ${vote.defectors}, reward <span class='good'>+${vote.player_reward}</span>`
    : 'No vote yet.';

  const summary = snapshot.floor_summary?.entries || [];
  document.getElementById('floorSummary').innerHTML = summary.length
    ? summary.map(entry => `<li>${branchToken(entry.name)} <span class='muted'>${escapeHtml(entry.descriptor)}</span> · score <span class='good'>${entry.score}</span> · wins ${entry.wins}</li>`).join('')
    : '<li>No summary yet.</li>';

  const successors = snapshot.successor_options?.candidates || [];
  document.getElementById('successors').innerHTML = successors.length
    ? successors.map(candidate => `<li>${branchToken(candidate.name)} · ${genomeToken(candidate.genome_summary)} · score ${candidate.score} / wins ${candidate.wins}</li>`).join('')
    : '<li>No successor choice active.</li>';

  const completion = snapshot.completion;
  document.getElementById('completion').innerHTML = completion
    ? `${effectToken(completion.outcome.toUpperCase())} on floor ${completion.floor_number} as ${branchToken(completion.player_name)}`
    : 'Run in progress.';

  const pending = latest?.pending_message ? `${latest.pending_screen}: ${latest.pending_message}` : '';
  document.getElementById('pending').textContent = pending;
}

async function refresh(){
  const response = await fetch('/api/state');
  latest = await response.json();
  document.getElementById('status').textContent = `status: ${latest.status}`;
  renderDecision(latest);
  renderSnapshot(latest.snapshot || {});
  document.getElementById('stateJson').textContent = JSON.stringify(latest, null, 2);
}

async function startRun(){ await fetch('/api/run/start', {method:'POST'}); await refresh(); }
async function advanceFlow(){ await fetch('/api/advance', {method:'POST'}); await refresh(); }
async function sendAction(payload){
  await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  await refresh();
}
async function sendStanceN(stance){
  const raw = prompt('Rounds (N):', '2');
  const rounds = Number.parseInt(raw || '0', 10);
  if (!Number.isFinite(rounds) || rounds <= 0) return;
  await sendAction({type:'set_round_stance', stance, rounds});
}
</script>
</body>
</html>
"""


class _State:
    session: FeaturedMatchWebSession | None = None
    lock = threading.RLock()


class Handler(BaseHTTPRequestHandler):
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
        if self.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/state":
            with _State.lock:
                if _State.session is None:
                    payload = {"status": "not_started", "decision": None, "decision_type": None, "snapshot": {}}
                else:
                    payload = _State.session.view()
            self._json(payload)
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        if self.path == "/api/run/start":
            with _State.lock:
                _State.session = FeaturedMatchWebSession(seed=7, rounds=3)
                _State.session.start()
                payload = _State.session.view()
            self._json(payload)
            return

        if self.path == "/api/advance":
            with _State.lock:
                if _State.session is None:
                    payload = {"error": "session not started"}
                    status = 400
                else:
                    _State.session.advance()
                    payload = _State.session.view()
                    status = 200
            self._json(payload, status=status)
            return

        if self.path != "/api/action":
            self._json({"error": "not found"}, status=404)
            return

        try:
            raw_length = self.headers.get("Content-Length", "0")
            length = int(raw_length)
            if length < 0:
                raise ValueError("Content-Length cannot be negative")
        except ValueError:
            self.close_connection = True
            self._json({"error": "invalid Content-Length"}, status=400)
            return
        if length > _MAX_REQUEST_BODY_BYTES:
            self.close_connection = True
            self._json({"error": "request body too large"}, status=413)
            return
        raw_bytes = self.rfile.read(length) if length else b"{}"
        try:
            raw = raw_bytes.decode("utf-8")
            payload = json.loads(raw)
        except UnicodeDecodeError:
            self.close_connection = True
            self._json({"error": "invalid UTF-8 in request body"}, status=400)
            return
        except json.JSONDecodeError:
            self._json({"error": "invalid JSON"}, status=400)
            return
        if not isinstance(payload, dict):
            self._json({"error": "invalid action payload"}, status=400)
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

            with _State.lock:
                if _State.session is None:
                    payload = {"error": "session not started"}
                    status = 400
                else:
                    _State.session.submit_action(action)
                    _State.session.advance()
                    payload = _State.session.view()
                    status = 200
        except (ValueError, RuntimeError) as exc:
            _log.warning("Client error in /api/action: %s", exc)
            self._json({"error": "invalid request"}, status=400)
            return
        except Exception:  # noqa: BLE001
            _log.exception("Unhandled error in /api/action")
            self._json({"error": "internal server error"}, status=500)
            return

        self._json(payload, status=status)


def run_server(port: int = 8765, host: str = "127.0.0.1") -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Web slice running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
