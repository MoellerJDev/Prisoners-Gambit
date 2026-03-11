# Prisoner's Gambit

A Python prototype for a roguelike built around iterated Prisoner's Dilemma, evolutionary opponents, player-selectable powerups, and a future-proofed architecture for richer UI support.

## Project vision

The goal is to build a game where:

- each agent has a strategy genome for making cooperate/defect decisions
- agents play repeated Prisoner's Dilemma matches against the rest of the population
- only top performers survive each floor
- the player chooses one of several powerups after each floor
- AI opponents can also accumulate powerups and mutate over time
- the run continues until the player is eliminated

This repository is meant to be a strong first-pass scaffold, not a fully balanced game.

## Design goals

- Keep core game rules separate from rendering
- Support toggleable, detailed logging
- Emit structured domain events for future GUI or replay systems
- Keep systems modular so mechanics can expand without major refactors
- Make it easy to replace the terminal UI later

## Repository layout

    src/prisoners_gambit/
      app/        # orchestration and startup
      config/     # settings and logging configuration
      core/       # domain models, rules, strategy, powerups, events
      systems/    # tournament flow, evolution, powerup offers, population generation
      content/    # enemy names, archetypes, powerup template definitions
      ui/         # renderer interfaces and terminal implementation
      adapters/   # event listeners, recorders, bridges to external layers
      utils/      # small helpers and formatting tools

    tests/        # unit and smoke tests
    docs/         # architecture notes and future design docs

## Current gameplay loop

1. Create a population of agents
2. Mark one agent as the player
3. Run a full floor tournament
4. Rank agents by score and wins
5. Eliminate the bottom portion
6. If the player survives, offer 5 powerups and let them choose 1
7. Give some AI survivors random powerups
8. Repopulate from survivors using mutated offspring
9. Continue until the player is eliminated or the run ends

## Current scoring model

This prototype currently uses the scoring model discussed earlier:

- if you defect while the opponent cooperates, you gain 1 point
- if both cooperate, both gain 1 point
- otherwise, no points are awarded

This is intentionally simple and can be changed later.

## Quick start

Create and activate a virtual environment.

On macOS/Linux:

    python -m venv .venv
    source .venv/bin/activate

On Windows:

    python -m venv .venv
    .venv\Scripts\activate

Install the package in editable mode with dev dependencies:

    pip install -e .[dev]

Run the prototype:

    python -m prisoners_gambit

Run tests:

    python -m pytest -q

## Configuration

Settings are environment-driven.

Available environment variables:

- `PG_POPULATION_SIZE`
- `PG_ROUNDS_PER_MATCH`
- `PG_SURVIVOR_COUNT`
- `PG_OFFERS_PER_FLOOR`
- `PG_FLOORS`
- `PG_MUTATION_RATE`
- `PG_SEED`
- `PG_LOG_LEVEL`
- `PG_LOG_TO_CONSOLE`
- `PG_LOG_TO_FILE`
- `PG_LOG_FILE`

Example:

    PG_SEED=7 PG_LOG_LEVEL=DEBUG PG_LOG_TO_FILE=true python -m prisoners_gambit

## Logging

Logging is meant for debugging and development, not player-facing presentation.

Important characteristics:

- detailed internal logging can be turned on or off
- console logging and file logging are configurable independently
- gameplay rendering is not driven directly by log output

This keeps the project ready for a future UI layer without tying the simulation to print statements.

## Event model

The application emits domain events through an event bus.

Examples include:

- `run_started`
- `floor_started`
- `floor_completed`
- `powerups_offered`
- `powerup_selected`
- `player_eliminated`
- `run_completed`

This event layer is important because a future UI can subscribe to these events and build:

- animated floor transitions
- match replays
- powerup selection screens
- run summaries
- charts and inspectors
- save/load and replay tools

## Architectural boundaries

### `core`

Contains the raw game domain:

- constants
- scoring rules
- strategies
- models
- powerup behavior
- domain events

### `systems`

Contains simulation services that operate on the domain:

- tournament engine
- population generation
- evolution and repopulation
- powerup offer generation
- progression rules

### `app`

Coordinates the run:

- bootstraps settings
- wires dependencies together
- orchestrates floors and player choices

### `ui`

Displays the run:

- renderer interfaces
- terminal renderer
- future GUI/web renderer implementations

### `adapters`

Bridges the game to external concerns:

- event recording
- analytics
- debug listeners
- persistence hooks

## Expansion ideas

### Short-term

- add more powerup families
- add enemy archetypes and named bosses
- add floor modifiers or acts
- add featured match summaries
- record events to JSON for replay

### Mid-term

- build a richer terminal UI
- add save/load support
- expose per-match inspection
- add balancing tools and simulation dashboards

### Long-term

- replace terminal renderer with a GUI or web app
- add relic rarity, shops, and branching paths
- add visual run history and build screens
- add challenge modes and seeded runs

## Suggested next files to expand

If you want to keep building from this scaffold, the most useful next files to touch are:

- `src/prisoners_gambit/app/run_application.py`
- `src/prisoners_gambit/systems/tournament.py`
- `src/prisoners_gambit/core/powerups.py`
- `src/prisoners_gambit/systems/offers.py`
- `src/prisoners_gambit/adapters/json_event_recorder.py`

## Notes

This repository is intentionally structured to support growth.

It is not yet:

- fully balanced
- content-rich
- graphically rendered
- save/load complete
- replay complete

But it is meant to be a good base for getting there cleanly.