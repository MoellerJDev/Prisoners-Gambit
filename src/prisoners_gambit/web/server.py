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
from prisoners_gambit.config.settings import Settings
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
    return FeaturedMatchWebSession(seed=seed, rounds=settings.rounds_per_match)


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
    .actions {
      margin-top:6px;
      display:grid;
      grid-template-columns:repeat(2, minmax(0, 1fr));
      gap:8px;
    }
    .actions .btn {
      width:100%;
      min-height:74px;
      padding:8px 10px;
      display:flex;
      flex-direction:column;
      align-items:flex-start;
      justify-content:center;
      gap:3px;
      text-align:left;
      border-radius:10px;
    }
    .action-tile-title { font-size:14px; font-weight:600; color:var(--text); line-height:1.25; }
    .action-tile-meta { font-size:12px; color:var(--muted); line-height:1.25; }
    .choice-card-effect { font-size:13px; font-weight:600; color:var(--text); line-height:1.3; }
    .choice-card-tags { display:flex; flex-wrap:wrap; gap:5px; }
    .choice-mini-tag {
      display:inline-flex;
      align-items:center;
      border:1px solid color-mix(in oklab, var(--border), #000 20%);
      border-radius:999px;
      padding:2px 8px;
      font-size:11px;
      color:var(--muted);
      background:#111b2c;
    }
    .choice-card-fit { font-size:11px; color:var(--accent); }
    .choice-card-detail {
      margin:1px 0 0;
      font-size:11px;
      color:var(--muted);
      line-height:1.25;
      max-width:100%;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }
    .choice-card-more {
      margin-top:2px;
      font-size:11px;
      color:var(--muted);
      text-transform:uppercase;
      letter-spacing:.06em;
    }
    .comparison-cards {
      margin:0;
      padding:0;
      list-style:none;
      display:grid;
      gap:8px;
    }
    .comparison-card {
      border:1px solid color-mix(in oklab, var(--border), #000 20%);
      border-radius:10px;
      background:#111a2a;
      padding:8px;
      display:grid;
      gap:5px;
    }
    .comparison-top {
      display:flex;
      justify-content:space-between;
      align-items:baseline;
      gap:8px;
      flex-wrap:wrap;
    }
    .comparison-name { font-weight:700; font-size:13px; }
    .comparison-score { font-size:12px; color:var(--muted); }
    .comparison-row { font-size:12px; line-height:1.35; color:var(--text); }
    .comparison-row .muted-label {
      color:var(--muted);
      font-weight:600;
      text-transform:uppercase;
      letter-spacing:.05em;
      font-size:10px;
      margin-right:4px;
    }
    .action-tile-secondary { border-color:color-mix(in oklab, var(--border), #000 35%); background:#172236; }
    .actions-primary-label {
      margin-top:8px;
      font-size:11px;
      color:var(--muted);
      text-transform:uppercase;
      letter-spacing:.08em;
    }
    .advanced-actions {
      margin-top:8px;
      border:1px solid color-mix(in oklab, var(--border), #000 15%);
      border-radius:10px;
      background:#101929;
      padding:8px;
    }
    .advanced-actions summary {
      cursor:pointer;
      color:var(--muted);
      font-size:12px;
      text-transform:uppercase;
      letter-spacing:.08em;
      list-style:none;
    }
    .advanced-actions summary::-webkit-details-marker { display:none; }
    .advanced-actions summary::after {
      content:'▾';
      float:right;
      transition:transform .15s ease;
    }
    .advanced-actions[open] summary::after { transform:rotate(180deg); }
    .actions-secondary {
      margin-top:8px;
      grid-template-columns:repeat(2, minmax(0, 1fr));
    }
    .panel-mobile-low { opacity:.98; }
    .onboarding-panel {
      margin:12px 0;
      border-color:color-mix(in oklab, var(--accent), var(--border) 55%);
      background:linear-gradient(180deg, #152238, #121b2c);
    }
    .onboarding-points { margin:0; padding-left:18px; color:var(--muted); }
    .onboarding-dismiss {
      margin-left:auto;
      font-size:12px;
      min-height:34px;
      padding:6px 10px;
    }
    .tab-controls { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
    .tab-btn { padding:7px 10px; border-radius:999px; background:#121b2b; color:var(--muted); font-size:12px; }
    .tab-btn.active { background:#223553; border-color:var(--accent); color:var(--text); }
    .tab-help { margin:-2px 0 9px; font-size:12px; color:var(--muted); }
    .glossary-row { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
    .help-chip {
      border:1px solid color-mix(in oklab, var(--border), #000 25%);
      border-radius:999px;
      padding:4px 8px;
      font-size:11px;
      color:var(--muted);
      background:#111a2a;
      cursor:pointer;
    }
    .help-chip:hover { color:var(--text); border-color:var(--accent); }
    .help-chip-inline {
      margin-left:6px;
      width:22px;
      min-height:22px;
      padding:0;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:999px;
      font-size:11px;
    }
    .glossary-panel {
      border:1px solid color-mix(in oklab, var(--border), #000 20%);
      border-radius:8px;
      background:#111b2d;
      padding:8px;
      color:var(--muted);
      font-size:12px;
      line-height:1.35;
      margin-bottom:8px;
    }
    .decision-helper { margin-top:8px; font-size:12px; color:var(--muted); }
    .tab-panel { display:none; }
    .tab-panel.active { display:block; }
    .contextual-panel { border-color:color-mix(in oklab, var(--accent), var(--border) 65%); }
    .contextual-title { margin:0 0 10px; font-size:12px; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); }
    .context-note { margin-top:8px; color:var(--muted); font-size:13px; }
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
    .snapshot-headline { font-size:14px; font-weight:700; margin:0 0 8px; color:var(--text); }
    .snapshot-chips { margin-bottom:8px; }

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
      .actions { grid-template-columns:repeat(2, minmax(0, 1fr)); gap:7px; }
      .actions .btn { min-height:56px; padding:8px 9px; }
      .actions-primary-label { margin-top:6px; font-size:10px; }
      .action-tile-title { font-size:13px; }
      .action-tile-meta { font-size:11px; }
      .advanced-actions { padding:6px 7px; }
      .advanced-actions summary { font-size:11px; }
      .grid > .decision-actions-panel { order:1; }
      .grid > .decision-details-panel { order:2; }
      .grid > .contextual-panel { order:3; }
      .grid > .secondary-info-panel { order:4; }
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

  <div id='onboardingPanel' class='panel panel-enter onboarding-panel' style='display:none;'>
    <div class='row' style='align-items:flex-start; gap:10px;'>
      <div>
        <h3>Quick start</h3>
        <ul class='onboarding-points'>
          <li><strong>Current Decision</strong> is where you act right now.</li>
          <li><strong>Decision Details</strong> explains the active prompt in compact form.</li>
          <li><strong>Summary</strong> explains why this floor matters; <strong>Board</strong> shows pressure shifts.</li>
          <li><strong>Chronicle</strong> tracks what changed across hosts and floors.</li>
          <li>Choice cards show <strong>effect first</strong>, with deeper tradeoffs below.</li>
        </ul>
      </div>
      <button class='btn onboarding-dismiss' onclick='dismissOnboarding()'>Got it</button>
    </div>
  </div>

  <div class='grid'>
    <div class='panel panel-enter decision-actions-panel'>
      <h3>Current Decision</h3>
      <div id='decisionType' class='muted'>No decision yet.</div>
      <div id='actionsPrimaryLabel' class='actions-primary-label'>Main choice now</div>
      <div id='phaseActionHelper' class='decision-helper'>Pick the highlighted action to keep pace.</div>
      <div id='actions' class='row actions'></div>
      <details id='advancedActions' class='advanced-actions' style='display:none;'>
        <summary id='advancedActionsLabel'>Advanced tactics</summary>
        <div id='advancedActionsGrid' class='row actions actions-secondary'></div>
      </details>
      <div id='pending' class='warn' style='margin-top:8px;'></div>
    </div>

    <div class='panel panel-enter decision-details-panel'>
      <h3>Decision Details <button class='btn help-chip-inline' onclick="toggleGlossaryTerm('controlled_vote')" title='What is controlled vote?'>?</button></h3>
      <div id='decisionView' class='kv muted'>Start run to begin.</div>
    </div>

    <div class='panel panel-enter contextual-panel'>
      <h3 id='contextualPanelTitle' class='contextual-title'>Latest Round Result</h3>
      <div id='contextRoundPanel'>
        <div id='roundResult' class='muted'>No rounds resolved yet.</div>
        <div id='roundEffects' class='muted' style='margin-top:10px;'></div>
      </div>
      <div id='contextSummaryPanel' style='display:none;'>
        <ul id='floorSummaryPrimary' class='list muted'><li>No summary yet.</li></ul>
      </div>
      <div id='contextSuccessorPanel' style='display:none;'>
        <ul id='successorsPrimary' class='list muted'><li>No successor choice active.</li></ul>
      </div>
      <div id='contextRewardPanel' style='display:none;'>
        <div id='rewardContext' class='muted'>No reward choice active.</div>
      </div>
      <div id='contextCompletionPanel' style='display:none;'>
        <div id='completion' class='muted'>Run in progress.</div>
      </div>
    </div>

    <div class='panel panel-enter secondary-info-panel panel-mobile-low'>
      <h3>Secondary Info</h3>
      <div class='tab-controls' role='tablist' aria-label='Secondary information'>
        <button class='btn tab-btn active' id='tabSummaryBtn' data-tab='summary' onclick="setSecondaryTab('summary')" role='tab' aria-selected='true'>Summary</button>
        <button class='btn tab-btn' id='tabBoardBtn' data-tab='board' onclick="setSecondaryTab('board')" role='tab' aria-selected='false'>Board</button>
        <button class='btn tab-btn' id='tabChronicleBtn' data-tab='chronicle' onclick="setSecondaryTab('chronicle')" role='tab' aria-selected='false'>Chronicle</button>
        <button class='btn tab-btn' id='tabDebugBtn' data-tab='debug' onclick="setSecondaryTab('debug')" role='tab' aria-selected='false'>Debug</button>
      </div>
      <div id='tabHelpText' class='tab-help'>Summary: why this floor matters and who is shaping it.</div>
      <div class='glossary-row'>
        <button class='help-chip' onclick="toggleGlossaryTerm('doctrine')">Doctrine ?</button>
        <button class='help-chip' onclick="toggleGlossaryTerm('heir_pressure')">Heir Pressure ?</button>
        <button class='help-chip' onclick="toggleGlossaryTerm('civil_war_danger')">Civil War Danger ?</button>
        <button class='help-chip' onclick="toggleGlossaryTerm('central_rival')">Central Rival ?</button>
        <button class='help-chip' onclick="toggleGlossaryTerm('controlled_vote')">Controlled Vote ?</button>
        <button class='help-chip' onclick="toggleGlossaryTerm('clue_fit')">Clue Fit / Memory ?</button>
        <button class='help-chip' onclick="toggleGlossaryTerm('lineage_direction')">Lineage Direction ?</button>
      </div>
      <div id='glossaryPanel' class='glossary-panel' style='display:none;'></div>

      <section id='secondaryTabSummary' class='tab-panel active' role='tabpanel'>
        <h3>Strategic Snapshot</h3>
        <div id='strategicSnapshotHeadline' class='snapshot-headline muted'>No strategic snapshot yet.</div>
        <div id='strategicSnapshotChips' class='row snapshot-chips'></div>
        <ul id='strategicSnapshotDetails' class='list muted'><li>No strategic snapshot yet.</li></ul>
        <h3 style='margin-top:10px;'>Floor Identity</h3>
        <div id='floorIdentityHeadline' class='floor-headline muted'>No floor identity committed yet.</div>
        <ul id='floorIdentity' class='list muted'><li>No floor identity committed yet.</li></ul>
        <h3 style='margin-top:10px;'>Floor Referendum</h3>
        <div id='voteResult' class='muted'>No vote yet.</div>
        <h3 style='margin-top:10px;'>Floor Summary</h3>
        <ul id='floorSummaryFull' class='list muted'><li>No summary yet.</li></ul>
        <div id='successorComparisonSection' style='display:none; margin-top:10px;'>
          <h3>Successor Comparison</h3>
          <ul id='successorComparison' class='comparison-cards muted'><li>No successor choice active.</li></ul>
        </div>
      </section>

      <section id='secondaryTabBoard' class='tab-panel' role='tabpanel'>
        <h3>Dynasty Board</h3>
        <ul id='dynastyBoard' class='list muted'><li>No lineage board yet.</li></ul>
      </section>

      <section id='secondaryTabChronicle' class='tab-panel' role='tabpanel'>
        <h3>Lineage Chronicle</h3>
        <ul id='chronicle' class='list muted'><li>No lineage events yet.</li></ul>
      </section>

      <section id='secondaryTabDebug' class='tab-panel raw-state-panel' role='tabpanel'>
        <h3>Raw State</h3>
        <details>
          <summary>Expand raw state/debug JSON</summary>
          <pre id='stateJson'>{}</pre>
        </details>
      </section>
    </div>
  </div>
</div>
<script>
let latest = null;
let previousTotals = null;
let activeSecondaryTab = 'summary';
const SAVE_STORAGE_KEY = 'prisoners_gambit_web_save_v1';
const ONBOARDING_DISMISSED_KEY = 'prisoners_gambit_onboarding_dismissed_v1';
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

function actionTile(label, meta){
  const metaText = meta ? `<span class='action-tile-meta'>${escapeHtml(meta)}</span>` : '';
  return `<span class='action-tile-title'>${escapeHtml(label)}</span>${metaText}`;
}

function compactTokenPreview(items, renderer, limit=3, emptyLabel='none'){
  const values = items || [];
  if (!values.length) return emptyLabel;
  const shown = values.slice(0, limit).map(renderer).join(' ');
  const extra = values.length - limit;
  return extra > 0 ? `${shown} <span class='choice-card-more'>+${extra} more</span>` : shown;
}

function compactEffectLine(parts){
  return (parts || []).find(part => Boolean(part && String(part).trim())) || 'Effect details in card notes.';
}

function renderCardTags(tags, limit=4){
  const values = (tags || []).filter(Boolean).slice(0, limit);
  return values.length ? `<div class='choice-card-tags'>${values.map(tag => `<span class='choice-mini-tag'>${escapeHtml(tag)}</span>`).join('')}</div>` : '';
}

function renderPowerupChoiceCard(offer, idx){
  const label = `${idx + 1}. ${offer.name}`;
  const trigger = cleanCauseLine(offer.trigger || '').replace(/^Trigger:\s*/i, '');
  const effect = cleanCauseLine(offer.effect || '').replace(/^Effect:\s*/i, '');
  const role = cleanCauseLine(offer.role || '').replace(/^Role:\s*/i, '');
  const effectLine = compactEffectLine([effect, trigger, role]);
  const fit = offer.relevance_hint || offer.crown_hint || '';
  const tagPool = [];
  if (trigger) tagPool.push(`Trigger ${trigger}`);
  if (offer.tags && offer.tags.length) tagPool.push(...offer.tags);
  if (offer.phase_support) tagPool.push(`Phase ${offer.phase_support}`);
  if (role) tagPool.push(role);
  const secondary = [offer.lineage_commitment, offer.doctrine_vector, offer.tradeoff, offer.successor_pressure]
    .filter(Boolean)
    .slice(0, 2)
    .map(line => `<div class='choice-card-detail'>${escapeHtml(line)}</div>`)
    .join('');
  return `
    <span class='action-tile-title'>${escapeHtml(label)}</span>
    <span class='choice-card-effect'>${escapeHtml(effectLine)}</span>
    ${renderCardTags(tagPool, 4)}
    ${fit ? `<span class='choice-card-fit'>Fit: ${escapeHtml(fit)}</span>` : ''}
    ${secondary}
  `;
}

function renderGenomeChoiceCard(offer, idx){
  const label = `${idx + 1}. ${offer.name}`;
  const drift = offer.doctrine_drift ? `Drift: ${offer.doctrine_drift}` : '';
  const beforeAfter = offer.lineage_commitment || offer.doctrine_vector || offer.tradeoff || 'Tuning lineage behavior toward this doctrine.';
  const tags = [offer.phase_support ? `Phase ${offer.phase_support}` : '', drift, offer.successor_pressure ? 'Heir pressure' : ''].filter(Boolean);
  return `
    <span class='action-tile-title'>${escapeHtml(label)}</span>
    <span class='choice-card-effect'>${escapeHtml(beforeAfter)}</span>
    ${renderCardTags(tags, 3)}
    ${offer.tradeoff ? `<div class='choice-card-detail'>Tradeoff: ${escapeHtml(offer.tradeoff)}</div>` : ''}
  `;
}

function renderSuccessorComparisonCard(candidate){
  const topCause = (candidate.shaping_causes || [])[0] || candidate.succession_pitch || 'No shaping cause available.';
  return `<li class='comparison-card'>
    <div class='comparison-top'>
      <span class='comparison-name'>${escapeHtml(candidate.name)} · ${escapeHtml(candidate.branch_role || 'unknown role')}</span>
      <span class='comparison-score'>${escapeHtml(candidate.score ?? '-')} score / ${escapeHtml(candidate.wins ?? '-')} wins</span>
    </div>
    <div class='comparison-row'><span class='muted-label'>Cause</span>${escapeHtml(topCause)}</div>
    <div class='comparison-row'><span class='muted-label'>Pick for</span>${escapeHtml(candidate.attractive_now || 'n/a')}</div>
    <div class='comparison-row'><span class='muted-label'>Risk</span>${escapeHtml(candidate.danger_later || 'n/a')}</div>
    <div class='comparison-row'><span class='muted-label'>Pitch</span>${escapeHtml(candidate.succession_pitch || 'n/a')}</div>
    <div class='comparison-row'><span class='muted-label'>Clue</span>${escapeHtml(candidate.featured_inference_context || 'No direct clue fit.')}</div>
  </li>`;
}

const TAB_HELP_TEXT = Object.freeze({
  summary: 'Summary: why this floor matters and who is shaping it.',
  board: 'Board: who is gaining pressure, rivalry, or civil-war danger.',
  chronicle: 'Chronicle: what changed across floors and hosts.',
  debug: 'Debug: raw state for deep inspection; secondary during play.',
});

const GLOSSARY_TERMS = Object.freeze({
  doctrine: "Doctrine is your branch's strategic tendency. It hints at what future offers and succession pressure will favor.",
  heir_pressure: 'Heir Pressure means succession momentum is building around specific branches. It tells you who is likely to matter next floor.',
  civil_war_danger: 'Civil War Danger signals that current pressure can spiral into costly conflict. Treat it as a warning about unstable succession paths.',
  central_rival: 'Central Rival marks the branch currently shaping your hardest contest. Reading this rival well improves your immediate decisions.',
  controlled_vote: 'Controlled Vote means your floor vote can be guided by your current plan, not just instincts. Use it to lock in floor-level direction.',
  clue_fit: 'Clue Fit / Memory describes how well recent evidence matches a candidate or doctrine read. Better fit means your read has practical backing.',
  lineage_direction: 'Lineage Direction summarizes where the dynasty is drifting if trends continue. It helps you decide whether to reinforce or pivot.',
});

function toggleGlossaryTerm(term){
  const panel = document.getElementById('glossaryPanel');
  if (!panel || !GLOSSARY_TERMS[term]) return;
  if (panel.dataset.term === term && panel.style.display !== 'none') {
    panel.style.display = 'none';
    panel.textContent = '';
    panel.dataset.term = '';
    return;
  }
  panel.dataset.term = term;
  panel.style.display = 'block';
  panel.textContent = GLOSSARY_TERMS[term];
}

function dismissOnboarding(){
  localStorage.setItem(ONBOARDING_DISMISSED_KEY, '1');
  const panel = document.getElementById('onboardingPanel');
  if (panel) panel.style.display = 'none';
}

function maybeShowOnboarding(){
  const dismissed = localStorage.getItem(ONBOARDING_DISMISSED_KEY) === '1';
  const panel = document.getElementById('onboardingPanel');
  if (!panel) return;
  panel.style.display = dismissed ? 'none' : 'block';
}

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

function setSecondaryTab(tab){
  activeSecondaryTab = tab;
  const tabs = ['summary', 'board', 'chronicle', 'debug'];
  tabs.forEach(name => {
    const btn = document.getElementById(`tab${name.charAt(0).toUpperCase()}${name.slice(1)}Btn`);
    const panel = document.getElementById(`secondaryTab${name.charAt(0).toUpperCase()}${name.slice(1)}`);
    const isActive = name === tab;
    if (btn) {
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    }
    if (panel) panel.classList.toggle('active', isActive);
  });
  const tabHelp = document.getElementById('tabHelpText');
  if (tabHelp) tabHelp.textContent = TAB_HELP_TEXT[tab] || TAB_HELP_TEXT.summary;
}

function updateContextualPanel(decisionType, snapshot){
  const panelTitle = document.getElementById('contextualPanelTitle');
  const sections = {
    round: document.getElementById('contextRoundPanel'),
    summary: document.getElementById('contextSummaryPanel'),
    successor: document.getElementById('contextSuccessorPanel'),
    reward: document.getElementById('contextRewardPanel'),
    completion: document.getElementById('contextCompletionPanel'),
  };
  Object.values(sections).forEach(section => {
    section.style.display = 'none';
  });

  if (snapshot?.completion) {
    panelTitle.textContent = 'Run Completion';
    sections.completion.style.display = 'block';
    return;
  }
  if (decisionType === 'SuccessorChoiceState') {
    panelTitle.textContent = 'Successor Options';
    sections.successor.style.display = 'block';
    return;
  }
  if (decisionType === 'PowerupChoiceState' || decisionType === 'GenomeEditChoiceState') {
    panelTitle.textContent = 'Reward Selection';
    sections.reward.style.display = 'block';
    return;
  }
  if (snapshot?.floor_summary?.entries?.length) {
    panelTitle.textContent = 'Floor Summary';
    sections.summary.style.display = 'block';
    return;
  }
  panelTitle.textContent = 'Latest Round Result';
  sections.round.style.display = 'block';
}

function renderDecision(data){
  const decision = data.decision;
  const t = data.decision_type;
  const actions = document.getElementById('actions');
  const actionsPrimaryLabel = document.getElementById('actionsPrimaryLabel');
  const advanced = document.getElementById('advancedActions');
  const advancedLabel = document.getElementById('advancedActionsLabel');
  const advancedGrid = document.getElementById('advancedActionsGrid');
  const phaseActionHelper = document.getElementById('phaseActionHelper');
  actions.innerHTML = '';
  actionsPrimaryLabel.textContent = 'Main choice now';
  phaseActionHelper.textContent = 'Pick the highlighted action to keep pace.';
  advancedGrid.innerHTML = '';
  advanced.open = false;
  advanced.style.display = 'none';
  document.getElementById('decisionType').textContent = t ? `Decision: ${shortDecisionLabel(t)}` : 'No active decision.';
  if (!decision) {
    actionsPrimaryLabel.textContent = '';
    phaseActionHelper.textContent = '';
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
    phaseActionHelper.textContent = 'Read clues and rival focus, then choose your move.';
    actions.innerHTML = `
      <button class='btn ${p.suggested_move === 0 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_move', move:'C'})">${actionTile('Cooperate', 'Manual move · primary')}</button>
      <button class='btn ${p.suggested_move === 1 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_move', move:'D'})">${actionTile('Defect', 'Manual move · primary')}</button>
      <button class='btn primary-action' onclick="sendAction({type:'autopilot_round'})">${actionTile('Autopilot', `Recommended · ${moveLabel(p.suggested_move)}`)}</button>`;
    advanced.style.display = 'block';
    advancedLabel.textContent = 'Advanced tactic setup (optional)';
    advancedGrid.innerHTML = `
      <button class='btn action-tile-secondary' onclick="sendAction({type:'set_round_stance', stance:'cooperate_until_betrayed'})">${actionTile('C until betrayed', 'Stance')}</button>
      <button class='btn action-tile-secondary' onclick="sendAction({type:'set_round_stance', stance:'defect_until_punished'})">${actionTile('D until punished', 'Stance')}</button>
      <button class='btn action-tile-secondary' onclick="sendStanceN('follow_autopilot_for_n_rounds')">${actionTile('Autopilot N', 'Stance with duration')}</button>
      <button class='btn action-tile-secondary' onclick="sendStanceN('lock_last_manual_move_for_n_rounds')">${actionTile('Lock last N', 'Stance with duration')}</button>`;
    return;
  }

  if (t === 'FloorVoteDecisionState') {
    actionsPrimaryLabel.textContent = 'Main choice now';
  phaseActionHelper.textContent = 'Controlled Vote lets you lock floor direction before rewards.';
    const p = decision.prompt;
    document.getElementById('decisionView').innerHTML = `
      <div>Floor</div><div>${p.floor_number} (${escapeHtml(p.floor_label)})</div>
      <div>Next pick</div><div>${effectToken(`Autopilot: ${moveLabel(p.suggested_vote)}`)}</div>
      <div>Floor Score</div><div>${p.current_floor_score}</div>
      <div>Powerups</div><div>${compactTokenPreview(p.powerups || [], powerupToken, 3, 'none')}</div>`;
    actions.innerHTML = `
      <button class='btn ${p.suggested_vote === 0 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_vote', vote:'C'})">${actionTile('Vote Cooperate', 'Manual vote · primary')}</button>
      <button class='btn ${p.suggested_vote === 1 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_vote', vote:'D'})">${actionTile('Vote Defect', 'Manual vote · primary')}</button>
      <button class='btn primary-action' onclick="sendAction({type:'autopilot_vote'})">${actionTile('Autopilot Vote', `Recommended · ${moveLabel(p.suggested_vote)}`)}</button>`;
    return;
  }

  if (t === 'PowerupChoiceState') {
    actionsPrimaryLabel.textContent = 'Choose one offer';
    phaseActionHelper.textContent = 'First line is the practical effect; tags and notes are secondary tradeoffs.';
    document.getElementById('decisionView').innerHTML = `
      <div>Choose now</div><div>Powerup card</div>
      <div>Floor</div><div>${decision.floor_number}</div>
      <div>Cards</div><div>${decision.offers.length}</div>`;
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = idx === 0 ? 'btn primary-action' : 'btn action-tile-secondary';
      const commitment = offer.lineage_commitment ? `Commitment: ${offer.lineage_commitment}` : '';
      const doctrine = offer.doctrine_vector ? `Doctrine: ${offer.doctrine_vector}` : '';
      const tradeoff = offer.tradeoff ? `Tradeoff: ${offer.tradeoff}` : '';
      const pressure = offer.successor_pressure ? `Heir pressure: ${offer.successor_pressure}` : '';
      btn.innerHTML = renderPowerupChoiceCard(offer, idx);
      btn.title = [offer.branch_identity, commitment || doctrine, tradeoff, `Phase: ${offer.phase_support || 'both'}`, pressure].filter(Boolean).join(' | ');
      btn.onclick = () => sendAction({type:'choose_powerup', offer_index: idx});
      actions.appendChild(btn);
    });
    return;
  }

  if (t === 'GenomeEditChoiceState') {
    actionsPrimaryLabel.textContent = 'Choose one offer';
    phaseActionHelper.textContent = 'First line is the practical effect; doctrine drift explains long-term tilt.';
    document.getElementById('decisionView').innerHTML = `
      <div>Choose now</div><div>Genome edit</div>
      <div>Floor</div><div>${decision.floor_number}</div>
      <div>Current build</div><div>${genomeToken(decision.current_summary)}</div>`;
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = idx === 0 ? 'btn primary-action' : 'btn action-tile-secondary';
      const commitment = offer.lineage_commitment ? `Commitment: ${offer.lineage_commitment}` : '';
      const doctrine = offer.doctrine_vector ? `Doctrine: ${offer.doctrine_vector}` : '';
      const tradeoff = offer.tradeoff ? `Tradeoff: ${offer.tradeoff}` : '';
      const pressure = offer.successor_pressure ? `Heir pressure: ${offer.successor_pressure}` : '';
      const drift = offer.doctrine_drift ? `Doctrine drift: ${offer.doctrine_drift}` : '';
      btn.innerHTML = renderGenomeChoiceCard(offer, idx);
      btn.title = [offer.branch_identity, commitment || doctrine, tradeoff, `Phase: ${offer.phase_support || 'both'}`, pressure, drift].filter(Boolean).join(' | ');
      btn.onclick = () => sendAction({type:'choose_genome_edit', offer_index: idx});
      actions.appendChild(btn);
    });
    return;
  }

  if (t === 'SuccessorChoiceState') {
    actionsPrimaryLabel.textContent = 'Choose next host';
    phaseActionHelper.textContent = 'Comparison rows map to Cause, Pick for, Risk, Pitch, and Clue fit.';
    document.getElementById('decisionView').innerHTML = `
      <div>Choose now</div><div>Next host</div>
      <div>Floor</div><div>${decision.floor_number}</div>
      <div>Candidates</div><div>${decision.candidates.length}</div>`;
    decision.candidates.forEach((candidate, idx) => {
      const btn = document.createElement('button');
      btn.className = idx === 0 ? 'btn primary-action' : 'btn action-tile-secondary';
      btn.innerHTML = `${actionTile(`${idx + 1}. ${candidate.name}`, `${candidate.branch_role} · ${candidate.score}/${candidate.wins}`)}<span class='muted'>${branchToken(candidate.name)}</span>`;
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
  const strategic = snapshot.strategic_snapshot;
  document.getElementById('strategicSnapshotHeadline').textContent = strategic?.headline || 'No strategic snapshot yet.';
  document.getElementById('strategicSnapshotChips').innerHTML = strategic
    ? (strategic.chips || []).map(chip => effectToken(chip)).join('')
    : '';
  document.getElementById('strategicSnapshotDetails').innerHTML = strategic
    ? (strategic.details || []).slice(0, 2).map(line => `<li>${escapeHtml(line)}</li>`).join('')
    : '<li>No strategic snapshot yet.</li>';

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
      <li><strong>Host</strong>: ${branchToken(floorIdentity.host_name)} · F${escapeHtml(floorIdentity.target_floor)}</li>`
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
  const floorSummaryFull = summary.length
    ? summary.slice(0, PANEL_LIMITS.floorLeaders).map(entry => {
        const continuity = entry.survived_previous_floor ? `↺F${entry.continuity_streak}` : 'new';
        const trend = entry.pressure_trend === 'rising' ? '↗' : (entry.pressure_trend === 'falling' ? '↘' : '→');
        return `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} <span class='muted'>${escapeHtml(entry.descriptor)}</span> · <span class='good'>${entry.score}</span> pts · ${movementGlyph(entry.score_delta || 0)}S ${movementGlyph(entry.wins_delta || 0)}W · ${continuity} · P${trend}</li>`;
      }).join('') + `<li><strong>Featured read</strong><ul>${featuredLead}</ul></li>` + pressureBlock + civilWarBlock
    : '<li>No summary yet.</li>';
  const floorSummaryPrimary = summary.length
    ? summary.slice(0, 2).map(entry => `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} <span class='good'>${entry.score}</span> pts · <span class='muted'>${escapeHtml(entry.descriptor)}</span></li>`).join('')
      + `<li class='context-note'>Open Summary tab for full floor context.</li>`
    : '<li>No summary yet.</li>';
  document.getElementById('floorSummaryFull').innerHTML = floorSummaryFull;
  document.getElementById('floorSummaryPrimary').innerHTML = floorSummaryPrimary;

  const successors = snapshot.successor_options?.candidates || [];
  const successorState = snapshot.successor_options;
  const successorContext = successorState
    ? `<li><strong>Why this choice matters</strong>: ${escapeHtml(successorState.current_phase || 'unknown')} phase, pressure ${escapeHtml(successorState.civil_war_pressure || 'unknown')}</li>`
      + `<li><strong>Main threats</strong>: ${escapeHtml(capLines(successorState.threat_profile || [], 2).join(', ') || 'none')}</li>`
      + `<li><strong>Clue memory</strong>: ${escapeHtml((successorState.featured_inference_summary || [])[0] || 'No clue memory this floor.')}</li>`
    : '';
  const successorPrimary = successors.length
    ? successors.slice(0, PANEL_LIMITS.successorCards).map(candidate => {
        const topCause = (candidate.shaping_causes || [])[0] || candidate.succession_pitch;
        return `<li>${branchToken(candidate.name)} · ${escapeHtml(candidate.branch_role)} · ${candidate.score} pts<br/><span class='muted'>${escapeHtml(topCause)}</span></li>`;
      }).join('') + `<li class='context-note'>Open Summary → Successor Comparison for full candidate breakdown.</li>`
    : `${successorContext}<li>No successor choice active.</li>`;
  document.getElementById('successorsPrimary').innerHTML = successorPrimary;

  const successorComparisonSection = document.getElementById('successorComparisonSection');
  const successorComparison = document.getElementById('successorComparison');
  const activeSuccessorDecision = latest?.decision_type === 'SuccessorChoiceState' ? latest?.decision : null;
  const comparisonCandidates = activeSuccessorDecision?.candidates || successors;
  if (latest?.decision_type === 'SuccessorChoiceState' && comparisonCandidates.length) {
    successorComparisonSection.style.display = 'block';
    successorComparison.innerHTML = comparisonCandidates.map(renderSuccessorComparisonCard).join('');
  } else {
    successorComparisonSection.style.display = 'none';
    successorComparison.innerHTML = '<li>No successor choice active.</li>';
  }

  const rewardContext = document.getElementById('rewardContext');
  if (latest?.decision_type === 'PowerupChoiceState') {
    rewardContext.innerHTML = `${effectToken('Powerup choice active')} Pick one offer in Current Decision. <div class='context-note'>Use Summary tab for floor-level context while choosing.</div>`;
  } else if (latest?.decision_type === 'GenomeEditChoiceState') {
    rewardContext.innerHTML = `${effectToken('Genome edit active')} Pick one genome edit in Current Decision. <div class='context-note'>Use Summary tab for floor-level context while choosing.</div>`;
  } else {
    rewardContext.textContent = 'No reward choice active.';
  }

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
        const perkPreview = compactTokenPreview(entry.visible_powerups || [], powerupToken, 2, '');
        const perkLine = perkPreview ? `<br/><span class='muted'>Perks ${perkPreview}</span>` : '';
        return `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} · ${escapeHtml(entry.role)} · score ${entry.score} (${movementGlyph(entry.score_delta || 0)}S, ${movementGlyph(entry.wins_delta || 0)}W) · ${continuity} · P${trend} · depth ${entry.lineage_depth}<br/>${markerBlock}${perkLine}</li>`;
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

  updateContextualPanel(latest?.decision_type || null, snapshot);
}

async function refresh(){
  const response = await fetch('/api/state');
  latest = await response.json();
  document.getElementById('status').textContent = `status: ${latest.status}`;
  renderDecision(latest);
  renderSnapshot(latest.snapshot || {});
  setSecondaryTab(activeSecondaryTab || 'summary');
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
  maybeShowOnboarding();
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
