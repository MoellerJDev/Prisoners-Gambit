# Prisoner's Gambit

Prisoner's Gambit is a strategy roguelike built on an iterated prisoner's dilemma simulation.

You do not control a single permanent character. You control a lineage of strategies.

Each floor, a population of agents plays a full tournament. Agents are ranked, the weaker half is eliminated, and the survivors shape the next generation. If your current host dies but your lineage survives, you assume one of your descendants and continue the run.

The run has two phases:

- Ecosystem phase: your lineage competes against outside strategies
- Civil war phase: once all outsiders are gone, only your lineage remains and the surviving branches fight until one final branch is left

## Current features

- Seeded deterministic runs
- Full round-robin floor tournaments
- Featured player matches with hidden-opponent inference
- Procedurally varied strategy genomes
- Powerups that change scoring, move control, and referendum behavior
- Genome edit choices between floors
- Lineage inheritance and host succession
- Better descendant naming for player branches
- Build identity tags and descriptors
- Global floor referendum layer
- Civil war endgame
- Broad automated test coverage

## Core gameplay loop

1. Create a population of agents
2. Mark one agent as the player host
3. Run a full floor tournament
4. Rank agents by score and wins
5. Eliminate the lower portion
6. If your current host died but lineage survives, choose a successor
7. Choose 1 powerup from a set of offers
8. Choose 1 autopilot genome edit
9. Grant some AI survivors random powerups
10. Repopulate during ecosystem phase
11. Transition to civil war once all outsiders are gone
12. Continue until your lineage is destroyed or one final branch survives

## Project structure

    prisoners-gambit/
    ├── README.md
    ├── pyproject.toml
    ├── .gitignore
    ├── docs/
    │   ├── architecture.md
    │   ├── gameplay-design.md
    │   ├── powerup-design.md
    │   ├── event-model.md
    │   └── roadmap.md
    ├── src/
    │   └── prisoners_gambit/
    │       ├── __init__.py
    │       ├── __main__.py
    │       ├── app/
    │       │   ├── __init__.py
    │       │   ├── bootstrap.py
    │       │   ├── run_application.py
    │       │   └── service_container.py
    │       ├── config/
    │       │   ├── __init__.py
    │       │   ├── settings.py
    │       │   └── logging_config.py
    │       ├── core/
    │       │   ├── __init__.py
    │       │   ├── analysis.py
    │       │   ├── constants.py
    │       │   ├── events.py
    │       │   ├── genome_edits.py
    │       │   ├── interaction.py
    │       │   ├── models.py
    │       │   ├── powerups.py
    │       │   ├── scoring.py
    │       │   └── strategy.py
    │       ├── systems/
    │       │   ├── __init__.py
    │       │   ├── evolution.py
    │       │   ├── genome_offers.py
    │       │   ├── offers.py
    │       │   ├── population.py
    │       │   ├── progression.py
    │       │   └── tournament.py
    │       ├── content/
    │       │   ├── __init__.py
    │       │   ├── archetypes.py
    │       │   ├── genome_edit_templates.py
    │       │   ├── names.py
    │       │   └── powerup_templates.py
    │       ├── ui/
    │       │   ├── __init__.py
    │       │   ├── renderers.py
    │       │   ├── terminal.py
    │       │   └── view_models.py
    │       ├── adapters/
    │       │   ├── __init__.py
    │       │   ├── json_event_recorder.py
    │       │   └── logging_event_listener.py
    │       └── utils/
    │           ├── __init__.py
    │           ├── formatting.py
    │           └── random_tools.py
    ├── tests/
    │   ├── test_analysis.py
    │   ├── test_civil_war_phase.py
    │   ├── test_content_generation.py
    │   ├── test_events.py
    │   ├── test_evolution.py
    │   ├── test_genome_edits.py
    │   ├── test_lineage_rules.py
    │   ├── test_population.py
    │   ├── test_powerups.py
    │   ├── test_progression.py
    │   ├── test_regressions.py
    │   ├── test_run_application.py
    │   ├── test_scoring.py
    │   ├── test_strategy.py
    │   ├── test_tournament.py
    │   └── test_view_models.py
    └── scripts/
        ├── run_dev.sh
        └── run_dev.bat

## Installation

Create and activate a virtual environment, then install the project in editable mode.

### PowerShell

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e .[dev]

### Bash

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .[dev]

## Running the game

Run the project with:

    python -m prisoners_gambit

## Seeding runs

Runs are deterministic when given the same seed.

If no seed is provided, the game generates one automatically and prints it at the start and end of the run.

### PowerShell

    $env:PG_SEED="123456789"
    python -m prisoners_gambit

### Bash

    export PG_SEED="123456789"
    python -m prisoners_gambit

Use the printed seed to replay interesting runs.

## Useful environment variables

The game currently supports a handful of environment-driven settings.

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
- `PG_AUTO_CHOOSE_POWERUPS`
- `PG_AUTO_CHOOSE_ROUND_ACTIONS`
- `PG_AUTO_CHOOSE_GENOME_EDITS`
- `PG_AUTO_CHOOSE_FLOOR_VOTE`
- `PG_LOG_LEVEL`
- `PG_LOG_TO_CONSOLE`
- `PG_LOG_TO_FILE`
- `PG_LOG_FILE`

Example:

    $env:PG_SEED="987654321"
    $env:PG_POPULATION_SIZE="12"
    $env:PG_ROUNDS_PER_MATCH="7"
    python -m prisoners_gambit

## Current mechanical layers

### Strategy genome

Each agent has an autopilot genome with:
- first move
- response to C/C
- response to C/D
- response to D/C
- response to D/D
- noise

### Powerups

Perks can:
- alter scores
- force or redirect moves
- shape referendum outcomes
- create control-heavy or tempo-heavy builds

### Genome edits

Between floors, the player modifies the current host's autopilot in small but meaningful ways.

### Build identity

Agents are analyzed into readable tags and descriptors such as:
- Cooperative
- Aggressive
- Retaliatory
- Exploitative
- Control
- Referendum
- Consensus
- Punishing
- Precise
- Unstable

These are used to make roster reading and successor selection more meaningful.

### Referendum

Once per floor, all agents participate in a global cooperation/defection vote.

- If cooperation reaches majority or tie, cooperators get rewarded
- If defection has majority, nobody gets rewarded

### Succession

If your current host is eliminated but descendants remain, you choose which surviving branch to become next.

### Civil war

When all outsiders are gone, the game enters a final civil war between surviving branches of your own lineage.

## Testing

Run the full test suite with:

    python -m pytest -q

At the current stage, the tests cover:
- scoring
- powerups
- strategy genomes
- genome edits
- tournament logic
- evolution
- progression
- lineage transfer rules
- civil war behavior
- event model
- content generation
- view formatting
- regressions from previously discovered bugs

## Design direction

The project is moving toward a strategy roguelike where the most important decisions are not just tactical round inputs, but:

- how you shape your lineage
- which descendant you assume after death
- how you read hidden opponents from incomplete information
- whether you optimize for pairwise play, referendum play, or late civil war dominance

## Documentation

See the docs folder for more detailed design and architecture notes:

- `docs/architecture.md`
- `docs/event-model.md`
- `docs/gameplay-design.md`
- `docs/powerup-design.md`
- `docs/roadmap.md`

## Next likely features

The strongest near-term candidates are:

- clearer featured-round explanation of which perks fired
- fast-forward or stance controls for featured matches
- stronger successor comparison tools
- between-floor reroll or economy systems
- more civil-war-specific content

## Notes

This project is currently terminal-first, but the code is intentionally structured so the simulation core is not tightly coupled to the terminal UI. That should make future UI upgrades much easier.