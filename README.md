# Prisoner's Gambit

Prisoner's Gambit is a strategy roguelike built around repeated prisoner's dilemma tournaments.

You do **not** play one permanent character. You play a **lineage**. If your current host is eliminated but your branch survives, you continue as a descendant.

---

## What a run feels like

Each floor has two big layers:

1. **Featured matches (you make decisions)**
   - You get masked opponents (`Unknown Opponent N`) and decide actions round-by-round.
   - You can manually play a move, follow autopilot, or use stances to automate behavior for a few rounds.

2. **Full floor tournament (everyone plays everyone)**
   - After featured decisions, all agents resolve a full round-robin tournament.
   - Rankings are computed from score (with wins as tiebreak support in summaries).
   - The bottom portion is eliminated.

Between floors you:
- pick 1 powerup,
- pick 1 genome edit,
- continue with survivors (or choose a successor if your host died).

Design intent: this is not just upkeep. Each floor should leave you asking what branch you are cultivating, what future threat landscape you are creating, and which successor you would want if your host died on the next floor.

The run starts in the **ecosystem phase** (your lineage vs outsiders), then transitions to **civil war** once outsiders are gone (your surviving branches fight until one remains).

---

## Quick start

### 1) Create and activate a virtual environment

#### Bash

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

#### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

### 2) Run the game

```bash
python -m prisoners_gambit
```

If you prefer not to install first, a local fallback is:

```bash
PYTHONPATH=src python -m prisoners_gambit
```

---

## Tutorial: your first terminal run

When a run starts, you'll see:
- the run seed,
- a floor roster with visible descriptors,
- featured matches with masked opponents,
- per-round breakdowns (planned moves, directive reasons, payoff modifiers).

During featured rounds, you will typically choose between:
- manual **Cooperate** or **Defect**,
- stance controls (short-term behavioral locks),
- autopilot-driven options.

After featured matches, you vote in a floor referendum, then see floor results, including a future-successor pressure readout (branch doctrine, likely heirs, and emerging threats), eliminations, and post-floor choices (powerup + genome edit).

Genome edit offers now include stronger doctrine pivots (safe/ruthless/unstable) so branch divergence appears earlier in a run.

### Deterministic replay

Use a seed to replay a run:

```bash
PG_SEED=123456789 python -m prisoners_gambit
```

PowerShell:

```powershell
$env:PG_SEED="123456789"
python -m prisoners_gambit
```

---

## Autoplay mode (great for smoke tests)

If you want to verify a full flow without manual input:

```bash
PG_SEED=20260311 \
PG_FLOORS=3 \
PG_AUTO_CHOOSE_POWERUPS=1 \
PG_AUTO_CHOOSE_ROUND_ACTIONS=1 \
PG_AUTO_CHOOSE_GENOME_EDITS=1 \
PG_AUTO_CHOOSE_FLOOR_VOTE=1 \
python -m prisoners_gambit
```

This is useful for quickly validating installs or sharing reproducible outcomes.

---

## Web prototype (new UI)

A browser-based prototype is included for the decision flow.

Start it with:

```bash
PYTHONPATH=src python -m prisoners_gambit.web.server
```

If `python` is not available in your shell, use:

```bash
PYTHONPATH=src python3 -m prisoners_gambit.web.server
```

Then open:

- `http://127.0.0.1:8765`

### Web UI walkthrough

1. Click **Start Run**.
2. In **Current Decision**, choose available actions (manual move / stance / offers / edits / successor).
3. Use **Continue Screen** when a non-decision panel is pending.
4. Track updates in:
   - **Latest Round Result**,
   - **Floor Referendum**,
   - **Floor Summary**,
   - **Run Completion**,
   - **Raw State** JSON panel.

The web prototype is a full-run decision surface over typed state/actions, but it is still a prototype UI rather than a complete production client.

---

## Key environment variables

### Core run configuration
- `PG_SEED`
- `PG_POPULATION_SIZE`
- `PG_ROUNDS_PER_MATCH`
- `PG_SURVIVOR_COUNT`
- `PG_OFFERS_PER_FLOOR`
- `PG_FEATURED_MATCHES_PER_FLOOR`
- `PG_GENOME_EDIT_OFFERS_PER_FLOOR`
- `PG_FLOORS`
- `PG_MUTATION_RATE`
- `PG_DESCENDANT_MUTATION_BONUS`

### Auto-choice helpers
- `PG_AUTO_CHOOSE_POWERUPS`
- `PG_AUTO_CHOOSE_ROUND_ACTIONS`
- `PG_AUTO_CHOOSE_GENOME_EDITS`
- `PG_AUTO_CHOOSE_FLOOR_VOTE`

### Logging
- `PG_LOG_LEVEL`
- `PG_LOG_TO_CONSOLE`
- `PG_LOG_TO_FILE`
- `PG_LOG_FILE`

---

## Why keep a tiny architecture map?

A giant tree dump is noisy in a gameplay-first README, but a **minimal map** helps contributors quickly find behavior:

- `src/prisoners_gambit/app/` — run orchestration and interaction flow
- `src/prisoners_gambit/core/` — models, scoring, interaction contracts
- `src/prisoners_gambit/systems/` — tournaments, evolution, progression logic
- `src/prisoners_gambit/ui/` — terminal rendering/view models
- `src/prisoners_gambit/web/` — web prototype server + web slice
- `tests/` — regression and system behavior coverage

If you're only here to play, you can ignore this section.

---

## Current status

Implemented and actively exercised in tests:
- deterministic seeded runs,
- full floor tournaments,
- masked featured matches with typed decision states,
- powerup + genome edit progression,
- lineage succession,
- referendum layer,
- ecosystem-to-civil-war transition,
- terminal UI and web prototype flows.
