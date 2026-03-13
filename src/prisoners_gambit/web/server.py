from __future__ import annotations

import dataclasses
import json
import logging
import os
import secrets
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
_PROCESS_LOCAL_SAVE_SECRET = secrets.token_bytes(32)
_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8765


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

HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'/>
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
      padding:10px 14px;
      min-height:42px;
      min-width:42px;
      cursor:pointer;
      background:#1b2639;
      color:var(--text);
      transition:transform .12s ease, border-color .15s ease, background .15s ease;
    }
    .controls { gap:10px; }
    .controls .btn { flex:0 1 auto; }
    .action-controls { margin-bottom:8px; }
    .status-controls { gap:6px; }
    .decision-actions-panel { border-color:color-mix(in oklab, var(--accent), var(--border) 40%); }
    .decision-details-panel { border-color:color-mix(in oklab, var(--accent), var(--border) 65%); }
    .primary-action { border-color:var(--accent); background:#223553; font-weight:600; }
    .actions { gap:10px; }
    .actions .btn { flex:1 1 170px; justify-content:center; display:inline-flex; align-items:center; min-height:46px; }
    .panel-mobile-low { opacity:.98; }
    .raw-state-panel summary { cursor:pointer; color:var(--muted); margin-bottom:8px; }
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
    .floor-headline { font-size:14px; font-weight:700; margin:0 0 8px; color:var(--text); }

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

    @media(max-width:960px){
      .grid { grid-template-columns:1fr; }
      .kv { grid-template-columns:150px 1fr; }
    }

    @media(max-width:700px){
      .wrap { padding:14px 12px 18px; }
      .sub { margin-bottom:10px; font-size:14px; }
      .panel { padding:12px; border-radius:11px; }
      .controls .btn { flex:1 1 calc(50% - 10px); min-height:50px; }
      .action-controls { margin-bottom:10px; }
      .status-controls { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); width:100%; gap:6px; }
      .pill { font-size:12px; padding:6px 8px; text-align:center; }
      .kv { grid-template-columns:1fr; row-gap:4px; }
      .kv > div:nth-child(odd) { font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }
      .decision-actions-panel { position:sticky; top:8px; z-index:3; }
      .actions { margin-top:8px; gap:8px; }
      .actions .btn { flex:1 1 100%; min-height:54px; }
      .grid > .decision-actions-panel { order:1; }
      .grid > .decision-details-panel { order:2; }
      .grid > .result-panel { order:3; }
      .grid > .floor-identity-panel { order:4; }
      .grid > .summary-panel { order:5; }
      .grid > .successor-panel { order:6; }
      .grid > .vote-panel { order:7; }
      .grid > .completion-panel { order:8; }
      .grid > .dynasty-panel { order:9; }
      .grid > .chronicle-panel { order:10; }
      .grid > .panel-mobile-low { order:11; }
      .raw-state-panel details:not([open]) pre { display:none; }
      pre { max-height:180px; font-size:11px; }
    }
  </style>
</head>
<body>
<div class='wrap'>
  <h1 class='header-title'>Prisoner's Gambit</h1>
  <div class='sub'>Full-run web prototype with typed decisions and atmospheric table-style UI.</div>

  <div class='panel panel-enter'>
    <div class='row controls action-controls'>
      <button class='btn' onclick='startRun()'>Start Run</button>
      <button id='advanceBtn' class='btn primary-action' onclick='advanceFlow()' style='display:none;'>Continue to next phase</button>
      <button class='btn' onclick='exportSaveCode()'>Export Save Code</button>
      <button class='btn' onclick='importSaveCode()'>Import Save Code</button>
      <button class='btn' onclick='clearRun()'>Clear Run</button>
    </div>
    <div class='row controls status-controls'>
      <span id='status' class='pill'>status: not_started</span>
      <span id='phase' class='pill'>phase: -</span>
      <span id='floor' class='pill'>floor: -</span>
      <span id='activeStance' class='pill'>stance: none</span>
    </div>
  </div>

  <div id='resumePanel' class='panel panel-enter' style='display:none; margin-top:12px;'>
    <h3>Saved Run Found</h3>
    <div class='row'>
      <button class='btn' onclick='resumeSavedRun()'>Resume Run</button>
      <button class='btn' onclick='startNewRunFromPrompt()'>Start New Run</button>
      <button class='btn' onclick='clearSavedRun()'>Clear Saved Run</button>
    </div>
    <div id='saveNotice' class='muted' style='margin-top:8px;'></div>
  </div>

  <div class='grid'>
    <div class='panel panel-enter decision-actions-panel'>
      <h3>Current Decision</h3>
      <div id='decisionType' class='muted'>No decision yet.</div>
      <div id='actions' class='row actions' style='margin-top:10px;'></div>
      <div id='pending' class='warn' style='margin-top:8px;'></div>
    </div>

    <div class='panel panel-enter decision-details-panel'>
      <h3>Decision Details</h3>
      <div id='decisionView' class='kv muted'>Start run to begin.</div>
    </div>

    <div class='panel panel-enter result-panel'>
      <h3>Latest Round Result</h3>
      <div id='roundResult' class='muted'>No rounds resolved yet.</div>
      <div id='roundEffects' class='muted' style='margin-top:10px;'></div>
    </div>

    <div class='panel panel-enter floor-identity-panel'>
      <h3>Floor Identity</h3>
      <div id='floorIdentityHeadline' class='floor-headline muted'>No floor identity committed yet.</div>
      <ul id='floorIdentity' class='list muted'><li>No floor identity committed yet.</li></ul>
    </div>

    <div class='panel panel-enter vote-panel panel-mobile-low'>
      <h3>Floor Referendum</h3>
      <div id='voteResult' class='muted'>No vote yet.</div>
    </div>

    <div class='panel panel-enter summary-panel'>
      <h3>Floor Summary</h3>
      <ul id='floorSummary' class='list muted'><li>No summary yet.</li></ul>
    </div>

    <div class='panel panel-enter successor-panel'>
      <h3>Successor Options</h3>
      <ul id='successors' class='list muted'><li>No successor choice active.</li></ul>
    </div>

    <div class='panel panel-enter dynasty-panel panel-mobile-low'>
      <h3>Dynasty Board</h3>
      <ul id='dynastyBoard' class='list muted'><li>No lineage board yet.</li></ul>
    </div>

    <div class='panel panel-enter completion-panel'>
      <h3>Run Completion</h3>
      <div id='completion' class='muted'>Run in progress.</div>
    </div>

    <div class='panel panel-enter chronicle-panel panel-mobile-low'>
      <h3>Lineage Chronicle</h3>
      <ul id='chronicle' class='list muted'><li>No lineage events yet.</li></ul>
    </div>
  </div>

  <div class='panel panel-enter panel-mobile-low raw-state-panel' style='margin-top:14px;'>
    <h3>Raw State</h3>
    <details open>
      <summary>Expand raw state/debug JSON</summary>
      <pre id='stateJson'>{}</pre>
    </details>
  </div>
</div>
<script>
let latest = null;
let previousTotals = null;
const SAVE_STORAGE_KEY = 'prisoners_gambit_web_save_v1';
const PANEL_LIMITS = Object.freeze({
  floorLeaders: 4,
  floorHeirs: 1,
  floorThreats: 1,
  successorCards: 2,
  chronicleEntries: 4,
  rules: 2,
});

function escapeHtml(s){ const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; }
function cleanCauseLine(text){
  if (!text) return '';
  return String(text).replace(/^because\s+/i, '').trim();
}
function moveLabel(v){ return v === 0 ? 'C' : 'D'; }
function effectToken(label){ return `<span class='token effect'>✦ ${escapeHtml(label)}</span>`; }
function relationToken(relation){
  const labels = {host:'HOST', kin:'KIN', outsider:'OUT'};
  return `<span class='token branch'>${escapeHtml(labels[relation] || 'OUT')}</span>`;
}
function movementGlyph(delta){
  if (delta > 0) return `↑${delta}`;
  if (delta < 0) return `↓${Math.abs(delta)}`;
  return '→0';
}
function branchToken(label){ return `<span class='token branch'>⎇ ${escapeHtml(label)}</span>`; }
function powerupToken(label){ return `<span class='token powerup'>⚡ ${escapeHtml(label)}</span>`; }
function genomeToken(label){ return `<span class='token genome'>🧬 ${escapeHtml(label)}</span>`; }
function shortDecisionLabel(type){
  const labels = {
    FeaturedRoundDecisionState: 'Round move',
    FloorVoteDecisionState: 'Floor vote',
    PowerupChoiceState: 'Powerup choice',
    GenomeEditChoiceState: 'Genome edit',
    SuccessorChoiceState: 'Successor choice',
  };
  return labels[type] || type || 'No active decision';
}

function renderDecision(data){
  const decision = data.decision;
  const t = data.decision_type;
  const actions = document.getElementById('actions');
  actions.innerHTML = '';
  document.getElementById('decisionType').textContent = t ? `Decision: ${shortDecisionLabel(t)}` : 'No active decision.';
  if (!decision) {
    document.getElementById('decisionView').innerHTML = 'No active decision.';
    return;
  }

  if (t === 'FeaturedRoundDecisionState') {
    const p = decision.prompt;
    const clues = (p.clue_channels || []).map(c => `<li>${escapeHtml(c)}</li>`).join('') || '<li class="muted">No explicit clues.</li>';
    const floorLog = (p.floor_clue_log || []).slice(-3).map(c => `<li>${escapeHtml(c)}</li>`).join('') || '<li class="muted">No prior featured clues this floor.</li>';
    document.getElementById('decisionView').innerHTML = `
      <div>Next pick</div><div>${effectToken(`Autopilot: ${moveLabel(p.suggested_move)}`)}</div>
      <div>Round</div><div>${p.round_index + 1}/${p.total_rounds}</div>
      <div>Score</div><div class='scoreline'>You <span class='good'>${p.my_match_score}</span> : <span class='danger'>${p.opp_match_score}</span> Opp</div>
      <div>Rival</div><div>${branchToken(p.masked_opponent_label)}</div>
      <div>Read on rival</div><div>${escapeHtml(p.inference_focus || 'Pattern check')}</div>
      <div>Live clues</div><div><ul class='list tight'>${clues}</ul></div>
      <div>Recent floor notes</div><div><ul class='list tight'>${floorLog}</ul></div>`;
    actions.innerHTML = `
      <button class='btn ${p.suggested_move === 0 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_move', move:'C'})">Cooperate</button>
      <button class='btn ${p.suggested_move === 1 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_move', move:'D'})">Defect</button>
      <button class='btn primary-action' onclick="sendAction({type:'autopilot_round'})">Autopilot Round</button>
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
      <div>Next pick</div><div>${effectToken(`Autopilot: ${moveLabel(p.suggested_vote)}`)}</div>
      <div>Floor Score</div><div>${p.current_floor_score}</div>
      <div>Powerups</div><div>${(p.powerups || []).map(powerupToken).join(' ') || 'none'}</div>`;
    actions.innerHTML = `
      <button class='btn ${p.suggested_vote === 0 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_vote', vote:'C'})">Vote Cooperate</button>
      <button class='btn ${p.suggested_vote === 1 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_vote', vote:'D'})">Vote Defect</button>
      <button class='btn primary-action' onclick="sendAction({type:'autopilot_vote'})">Autopilot Vote</button>`;
    return;
  }

  if (t === 'PowerupChoiceState') {
    document.getElementById('decisionView').innerHTML = `
      <div>Choose now</div><div>Powerup card</div>
      <div>Floor</div><div>${decision.floor_number}</div>
      <div>Cards</div><div>${decision.offers.length}</div>`;
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = idx === 0 ? 'btn primary-action' : 'btn';
      const label = `${idx + 1}. ${offer.name}`;
      const commitment = offer.lineage_commitment ? `Commitment: ${offer.lineage_commitment}` : '';
      const doctrine = offer.doctrine_vector ? `Doctrine: ${offer.doctrine_vector}` : '';
      const tradeoff = offer.tradeoff ? `Tradeoff: ${offer.tradeoff}` : '';
      const pressure = offer.successor_pressure ? `Heir pressure: ${offer.successor_pressure}` : '';
      btn.innerHTML = `${powerupToken(label)}<br/><span class='muted'>${escapeHtml(commitment || doctrine)}</span>`;
      btn.title = [offer.branch_identity, commitment || doctrine, tradeoff, `Phase: ${offer.phase_support || 'both'}`, pressure].filter(Boolean).join(' | ');
      btn.onclick = () => sendAction({type:'choose_powerup', offer_index: idx});
      actions.appendChild(btn);
    });
    return;
  }

  if (t === 'GenomeEditChoiceState') {
    document.getElementById('decisionView').innerHTML = `
      <div>Choose now</div><div>Genome edit</div>
      <div>Floor</div><div>${decision.floor_number}</div>
      <div>Current build</div><div>${genomeToken(decision.current_summary)}</div>`;
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = idx === 0 ? 'btn primary-action' : 'btn';
      const label = `${idx + 1}. ${offer.name}`;
      const commitment = offer.lineage_commitment ? `Commitment: ${offer.lineage_commitment}` : '';
      const doctrine = offer.doctrine_vector ? `Doctrine: ${offer.doctrine_vector}` : '';
      const tradeoff = offer.tradeoff ? `Tradeoff: ${offer.tradeoff}` : '';
      const pressure = offer.successor_pressure ? `Heir pressure: ${offer.successor_pressure}` : '';
      const drift = offer.doctrine_drift ? `Doctrine drift: ${offer.doctrine_drift}` : '';
      btn.innerHTML = `${genomeToken(label)}<br/><span class='muted'>${escapeHtml(commitment || doctrine)}</span>`;
      btn.title = [offer.branch_identity, commitment || doctrine, tradeoff, `Phase: ${offer.phase_support || 'both'}`, pressure, drift].filter(Boolean).join(' | ');
      btn.onclick = () => sendAction({type:'choose_genome_edit', offer_index: idx});
      actions.appendChild(btn);
    });
    return;
  }

  if (t === 'SuccessorChoiceState') {
    document.getElementById('decisionView').innerHTML = `
      <div>Choose now</div><div>Next host</div>
      <div>Floor</div><div>${decision.floor_number}</div>
      <div>Candidates</div><div>${decision.candidates.length}</div>`;
    decision.candidates.forEach((candidate, idx) => {
      const btn = document.createElement('button');
      btn.className = idx === 0 ? 'btn primary-action' : 'btn';
      btn.innerHTML = `${idx + 1}. ${branchToken(candidate.name)} · ${escapeHtml(candidate.branch_role)} (${candidate.score}/${candidate.wins})`;
      btn.title = (candidate.shaping_causes || []).join('; ');
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

  const capLines = (items, limit=2) => (items || []).slice(0, limit);
  const floorIdentity = snapshot.floor_identity;
  document.getElementById('floorIdentityHeadline').textContent = floorIdentity
    ? floorIdentity.headline
    : 'No floor identity committed yet.';
  document.getElementById('floorIdentity').innerHTML = floorIdentity
    ? `
      <li><strong>Dominant pressure</strong>: ${escapeHtml(floorIdentity.dominant_pressure)}</li>
      <li><strong>Why it matters</strong>: ${escapeHtml(floorIdentity.pressure_reason)}</li>
      <li><strong>Lineage direction</strong>: ${escapeHtml(floorIdentity.lineage_direction)}</li>
      <li><strong>Focus this floor</strong>: ${escapeHtml(floorIdentity.strategic_focus)}</li>
      <li><strong>Host</strong>: ${branchToken(floorIdentity.host_name)} · F${escapeHtml(floorIdentity.target_floor)}</li>
      ${floorIdentity.key_signal ? `<li><strong>Signal carryover</strong>: ${escapeHtml(floorIdentity.key_signal)}</li>` : ''}`
    : '<li>No floor identity committed yet.</li>';

  const summary = snapshot.floor_summary?.entries || [];
  const pressure = snapshot.floor_summary?.heir_pressure;
  const featuredInference = snapshot.floor_summary?.featured_inference_summary || [];
  const civilWar = snapshot.civil_war_context;
  const successorPreview = capLines(pressure?.successor_candidates || [], PANEL_LIMITS.floorHeirs).map(entry =>
    `<li>${branchToken(entry.name)} ${escapeHtml(entry.branch_role)} · <span class='muted'>${escapeHtml((entry.shaping_causes || [entry.rationale])[0] || entry.rationale)}</span></li>`
  ).join('');
  const threatPreview = capLines(pressure?.future_threats || [], PANEL_LIMITS.floorThreats).map(entry =>
    `<li>${branchToken(entry.name)} ${escapeHtml(entry.branch_role)} · <span class='muted'>${escapeHtml((entry.shaping_causes || [entry.rationale])[0] || entry.rationale)}</span></li>`
  ).join('');
  const featuredLead = capLines(featuredInference, 1).map(line => `<li>${escapeHtml(line)}</li>`).join('') || '<li class="muted">No solid clue read this floor.</li>';
  const pressureBlock = pressure
    ? `<li><strong>Succession trend</strong>: ${escapeHtml(pressure.branch_doctrine)}</li>`
      + `<li><strong>Best heir lead</strong><ul>${successorPreview || '<li class="muted">No clear heir yet.</li>'}</ul></li>`
      + `<li><strong>Main threat</strong><ul>${threatPreview || '<li class="muted">No outside pressure spotted.</li>'}</ul></li>`
    : '';
  const civilWarBlock = civilWar
    ? `<li><strong>Conflict</strong>: ${escapeHtml(civilWar.thesis)}</li>`
      + `<li><strong>Key rules</strong><ul>${capLines(civilWar.scoring_rules || [], PANEL_LIMITS.rules).map(rule => `<li>${escapeHtml(rule)}</li>`).join('') || '<li class="muted">No active score rules.</li>'}</ul></li>`
      + `<li><strong>Main pressure</strong>: ${escapeHtml(capLines(civilWar.dangerous_branches || [], 1).join(' · ') || 'Unknown')}</li>`
    : '';
  document.getElementById('floorSummary').innerHTML = summary.length
    ? summary.slice(0, PANEL_LIMITS.floorLeaders).map(entry => {
        const continuity = entry.survived_previous_floor ? `↺F${entry.continuity_streak}` : 'new';
        const trend = entry.pressure_trend === 'rising' ? '↗' : (entry.pressure_trend === 'falling' ? '↘' : '→');
        return `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} <span class='muted'>${escapeHtml(entry.descriptor)}</span> · <span class='good'>${entry.score}</span> pts · ${movementGlyph(entry.score_delta || 0)}S ${movementGlyph(entry.wins_delta || 0)}W · ${continuity} · P${trend}</li>`;
      }).join('') + `<li><strong>Featured read</strong><ul>${featuredLead}</ul></li>` + pressureBlock + civilWarBlock
    : '<li>No summary yet.</li>';

  const successors = snapshot.successor_options?.candidates || [];
  const successorState = snapshot.successor_options;
  const successorContext = successorState
    ? `<li><strong>Why this choice matters</strong>: ${escapeHtml(successorState.current_phase || 'unknown')} phase, pressure ${escapeHtml(successorState.civil_war_pressure || 'unknown')}</li>`
      + `<li><strong>Main threats</strong>: ${escapeHtml(capLines(successorState.threat_profile || [], 2).join(', ') || 'none')}</li>`
      + `<li><strong>Clue memory</strong>: ${escapeHtml((successorState.featured_inference_summary || [])[0] || 'No clue memory this floor.')}</li>`
    : '';
  document.getElementById('successors').innerHTML = successors.length
    ? successorContext + successors.slice(0, PANEL_LIMITS.successorCards).map(candidate => {
        const topCause = (candidate.shaping_causes || [])[0] || candidate.succession_pitch;
        return `<li>${branchToken(candidate.name)} · ${escapeHtml(candidate.branch_role)} · ${candidate.score} pts<br/><span class='muted'>${escapeHtml(topCause)}</span><br/><strong>Good at:</strong> ${escapeHtml(candidate.attractive_now)}<br/><strong>Risk:</strong> ${escapeHtml(candidate.danger_later)}<br/><strong>Pick now:</strong> ${escapeHtml(candidate.succession_pitch)}<br/><strong>Clue fit:</strong> ${escapeHtml(candidate.featured_inference_context || 'No direct clue fit.')}</li>`;
      }).join('')
    : '<li>No successor choice active.</li>';

  const dynastyEntries = snapshot.dynasty_board?.entries || [];
  document.getElementById('dynastyBoard').innerHTML = dynastyEntries.length
    ? dynastyEntries.map(entry => {
        const markerTokens = [
          entry.is_current_host ? effectToken('YOU') : '',
          entry.has_successor_pressure ? effectToken('HEIR') : '',
          entry.has_civil_war_danger ? effectToken('RISK') : '',
          entry.is_central_rival ? effectToken(entry.is_new_central_rival ? 'NEW RIVAL' : 'RIVAL') : '',
        ].filter(Boolean);
        const markerCauses = [
          entry.has_successor_pressure && entry.successor_pressure_cause ? `Heir: ${escapeHtml(cleanCauseLine(entry.successor_pressure_cause))}` : '',
          entry.has_civil_war_danger && entry.civil_war_danger_cause ? `Risk: ${escapeHtml(cleanCauseLine(entry.civil_war_danger_cause))}` : '',
        ].filter(Boolean);
        const markerBlock = markerTokens.length
          ? `${markerTokens.join(' ')}${markerCauses.length ? `<br/><span class="muted">${markerCauses.slice(0, 2).join(' · ')}</span>` : ''}`
          : '<span class="muted">No active lineage pressure markers.</span>';
        const continuity = entry.survived_previous_floor ? `↺F${entry.continuity_streak}` : 'new';
        const trend = entry.pressure_trend === 'rising' ? '↗' : (entry.pressure_trend === 'falling' ? '↘' : '→');
        return `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} · ${escapeHtml(entry.role)} · score ${entry.score} (${movementGlyph(entry.score_delta || 0)}S, ${movementGlyph(entry.wins_delta || 0)}W) · ${continuity} · P${trend} · depth ${entry.lineage_depth}<br/>${markerBlock}</li>`;
      }).join('')
    : '<li>No lineage board yet.</li>';

  const completion = snapshot.completion;
  document.getElementById('completion').innerHTML = completion
    ? `${effectToken(completion.outcome.toUpperCase())} on floor ${completion.floor_number} as ${branchToken(completion.player_name)}`
    : 'Run in progress.';

  const chronicle = snapshot.lineage_chronicle || [];
  const chronicleLabels = {
    run_start: 'Run start',
    floor_complete: 'Floor end',
    doctrine_pivot: 'Doctrine shift',
    successor_pressure: 'Succession pressure',
    successor_choice: 'New host',
    phase_transition: 'Phase change',
    civil_war_round_start: 'Civil-war round',
    run_outcome: 'Run result',
  };
  document.getElementById('chronicle').innerHTML = chronicle.length
    ? chronicle.slice(-PANEL_LIMITS.chronicleEntries).reverse().map(entry => `<li><strong>${escapeHtml(chronicleLabels[entry.event_type] || entry.event_type.replaceAll('_', ' '))}</strong> · F${escapeHtml(entry.floor_number ?? '-')} · ${escapeHtml(entry.summary)}${entry.cause ? `<br/><span class='muted'>${escapeHtml(cleanCauseLine(entry.cause))}</span>` : ''}</li>`).join('')
    : '<li>No lineage events yet.</li>';

  const pending = latest?.pending_message ? `Next action: ${latest.pending_message}` : '';
  document.getElementById('pending').textContent = pending;

  const advanceBtn = document.getElementById('advanceBtn');
  const transitionLabel = latest?.transition_action_label || '';
  const transitionVisible = Boolean(latest?.transition_action_visible && transitionLabel);
  advanceBtn.style.display = transitionVisible ? 'inline-flex' : 'none';
  advanceBtn.textContent = transitionLabel || 'Continue to next phase';
}

async function refresh(){
  const response = await fetch('/api/state');
  latest = await response.json();
  document.getElementById('status').textContent = `status: ${latest.status}`;
  renderDecision(latest);
  renderSnapshot(latest.snapshot || {});
  document.getElementById('stateJson').textContent = JSON.stringify(latest, null, 2);
  await autosaveFromServer();
}

function setSaveNotice(message){
  const notice = document.getElementById('saveNotice');
  if (notice) notice.textContent = message;
}

function getSavedSaveCode(){
  const raw = localStorage.getItem(SAVE_STORAGE_KEY);
  if (!raw) return null;
  return typeof raw === 'string' && raw.length > 0 ? raw : null;
}

function setSavedSaveCode(saveCode){
  localStorage.setItem(SAVE_STORAGE_KEY, saveCode);
}

function clearSavedRun(){
  localStorage.removeItem(SAVE_STORAGE_KEY);
  document.getElementById('resumePanel').style.display = 'none';
  setSaveNotice('Saved run cleared.');
}

async function autosaveFromServer(){
  if (!latest || latest.status === 'not_started') return;
  const response = await fetch('/api/run/export', {method:'POST'});
  if (!response.ok) return;
  const payload = await response.json();
  if (payload && payload.save_code) {
    setSavedSaveCode(payload.save_code);
    setSaveNotice('Autosaved.');
  }
}

async function restoreSavedCode(saveCode){
  await fetch('/api/run/import', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({save_code: saveCode}),
  });
  await refresh();
}

async function resumeSavedRun(){
  const saveCode = getSavedSaveCode();
  if (!saveCode) {
    setSaveNotice('No saved run found.');
    return;
  }
  await restoreSavedCode(saveCode);
  document.getElementById('resumePanel').style.display = 'none';
  setSaveNotice('Run resumed.');
}

async function startNewRunFromPrompt(){
  await startRun();
  setSaveNotice('Started new run; previous save overwritten.');
  document.getElementById('resumePanel').style.display = 'none';
}

async function startRun(){ await fetch('/api/run/start', {method:'POST'}); await refresh(); }
async function clearRun(){
  await fetch('/api/run/clear', {method:'POST'});
  clearSavedRun();
  latest = null;
  previousTotals = null;
  await refresh();
}
async function advanceFlow(){ await fetch('/api/advance', {method:'POST'}); await refresh(); }
async function sendAction(payload){
  await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  await refresh();
}
async function exportSaveCode(){
  const response = await fetch('/api/run/export', {method:'POST'});
  if (!response.ok) return;
  const payload = await response.json();
  if (!payload.save_code) return;
  prompt('Copy save code:', payload.save_code);
}
async function importSaveCode(){
  const code = prompt('Paste save code:');
  if (!code) return;
  const response = await fetch('/api/run/import', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({save_code: code.trim()}),
  });
  if (!response.ok) {
    setSaveNotice('Invalid save code.');
    return;
  }
  await refresh();
}
async function sendStanceN(stance){
  const raw = prompt('Rounds (N):', '2');
  const rounds = Number.parseInt(raw || '0', 10);
  if (!Number.isFinite(rounds) || rounds <= 0) return;
  await sendAction({type:'set_round_stance', stance, rounds});
}

window.addEventListener('load', async () => {
  const saved = getSavedSaveCode();
  if (saved) {
    document.getElementById('resumePanel').style.display = 'block';
    setSaveNotice('A local autosave is available.');
    return;
  }
  await refresh();
});
</script>
</body>
</html>
"""


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
        if self.path == "/":
            body = HTML.encode("utf-8")
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
                session = FeaturedMatchWebSession(seed=7, rounds=3)
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
