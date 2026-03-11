# Prisoner's Gambit Architecture

## Overview

Prisoner's Gambit is a turn-based roguelike strategy game built on top of an iterated prisoner's dilemma simulation. The game combines:

- evolutionary strategy generation
- player-controlled tactical intervention
- lineage inheritance and branch succession
- perk-driven rule bending
- a two-phase run structure:
  - ecosystem survival
  - lineage civil war

The codebase is organized so that the game loop, simulation logic, content generation, and user interface can evolve independently.

## Architectural Goals

The project is structured around a few design priorities:

1. Keep the simulation core independent from the terminal UI
2. Allow future migration to a richer UI without rewriting game rules
3. Make run logic testable without interactive input
4. Keep content expansion easy:
   - new perks
   - new genome edits
   - new archetypes
   - new run phases
5. Support deterministic seeded runs for debugging and replay

## Top-Level Structure

### `src/prisoners_gambit/app`
Application orchestration.

This layer wires the systems together and owns the high-level run loop.

Important files:
- `bootstrap.py`
- `service_container.py`
- `run_application.py`

Responsibilities:
- load settings
- resolve run seed
- build services
- start the run
- coordinate progression across floors
- handle lineage succession and phase changes

### `src/prisoners_gambit/config`
Environment-driven configuration and logging setup.

Responsibilities:
- parse settings from environment variables
- define runtime tuning knobs
- configure logging behavior

### `src/prisoners_gambit/core`
Pure game-domain types and logic.

This layer defines the vocabulary of the game.

Important concepts:
- `Agent`
- `StrategyGenome`
- `Powerup`
- `RoundContext`
- `ReferendumContext`
- interaction models
- scoring primitives
- derived build identity analysis

This layer should avoid depending on UI concerns.

### `src/prisoners_gambit/systems`
Simulation engines and mechanical subsystems.

Important systems:
- `TournamentEngine`
- `EvolutionEngine`
- `ProgressionEngine`
- offer generation systems

Responsibilities:
- match execution
- featured matches
- referendum resolution
- floor scaling
- survivor selection
- repopulation and offspring generation

### `src/prisoners_gambit/content`
Static or semi-static game content.

Examples:
- archetypes
- names
- perk templates
- genome edit templates

This layer is where content breadth should grow over time.

### `src/prisoners_gambit/ui`
Presentation layer.

Currently this is terminal-focused, but the interfaces are designed so other front ends can be added later.

Responsibilities:
- render floor summaries
- render roster information
- collect player choices
- show successor selection
- display phase transitions and run results

### `src/prisoners_gambit/adapters`
External-facing or auxiliary integrations.

Examples:
- logging event listener
- JSON event recording

### `src/prisoners_gambit/utils`
Small cross-cutting helpers.

Examples:
- formatting helpers
- random utilities

## Core Domain Model

### Agent

An `Agent` is the fundamental actor in the simulation.

Key fields:
- `name`
- `genome`
- `public_profile`
- `powerups`
- `score`
- `wins`
- `is_player`
- `lineage_id`
- `lineage_depth`

An agent can represent:
- the current active player host
- a surviving descendant branch
- an outsider strategy in the ecosystem

### StrategyGenome

A genome represents the agent's baseline strategy.

It consists of:
- `first_move`
- response table for:
  - `(C, C)`
  - `(C, D)`
  - `(D, C)`
  - `(D, D)`
- `noise`

This gives each agent a compact reactive policy.

### Powerups

Powerups modify game behavior through structured hooks, rather than ad hoc branching.

A perk may:
- affect the owner's move
- affect the opponent's move
- alter score outcomes
- alter referendum vote behavior
- alter referendum rewards

Contradictions are resolved deterministically through directive priority.

### Build Identity

Build identity is a derived layer that interprets an agent's genome and perks into readable tags and a descriptor.

Examples:
- Cooperative
- Aggressive
- Retaliatory
- Exploitative
- Referendum
- Control
- Punishing
- Defensive

This system exists for readability and player decision support, not for simulation.

## Run Loop

At a high level, a run proceeds like this:

1. Create initial population
2. Identify the player lineage
3. Run a floor tournament
4. Rank agents
5. Eliminate the bottom portion
6. Transfer control if the current host dies but lineage survives
7. Check whether the outside ecosystem has been eliminated
8. If still in ecosystem phase:
   - offer perk
   - offer genome edit
   - grant some AI perks
   - repopulate from survivors
9. If in civil war:
   - do not repopulate
   - keep cutting the lineage down until one branch remains
10. End with elimination or full lineage victory

## Phase Model

### Phase 1: Ecosystem Survival

The player's lineage competes against outsider agents.

Characteristics:
- standard floor progression
- repopulation occurs
- outside agents still exist
- the player is trying to keep the lineage alive while building power

### Phase 2: Civil War

Triggered when only the player lineage remains.

Characteristics:
- no repopulation
- surviving lineage branches fight each other
- succession remains possible if the active host dies
- only one branch can win the run

This second phase is what gives the game its strongest identity.

## Tournament Model

Each floor consists of:

- pairwise matches across the population
- some featured matches involving the active player host
- one floor referendum

### Standard Matches
These are resolved fully by genomes and perks.

### Featured Matches
These expose round-by-round decisions to the player.

The player sees:
- masked opponent label
- round history
- autopilot recommendation
- roster hints from known candidate identities

### Referendum
Once per floor, all agents cast a global cooperation or defection vote.

Rules:
- if cooperation reaches majority or tie, cooperators gain reward
- if defection has majority, nobody gains anything

This adds a population-level axis beyond pairwise optimization.

## Evolution Model

After a floor:
- agents are ranked
- survivors are selected
- offspring are generated from survivors

Player-lineage descendants receive:
- preserved lineage id
- increased mutation pressure
- inherited perks
- lineage naming

This causes the lineage to branch more aggressively over time.

## Determinism and Seeding

Runs are intended to be replayable.

Rules:
- every run has a concrete seed
- if none is provided, one is generated at startup
- the resolved seed is shown at the start and end of the run

Seeded determinism is important for:
- debugging
- regression testing
- run sharing
- balancing

## Event Model Integration

The application emits events as the run progresses.

These support:
- structured logging
- future replay tools
- analytics
- alternate front ends

Examples:
- run started
- survivors selected
- powerup selected
- genome edit selected
- successor selected
- civil war started
- run completed

## UI Boundary

The terminal UI is intentionally thin.

The simulation should not depend on:
- `print`
- `input`
- terminal formatting

Instead, the renderer interface handles:
- displaying information
- collecting decisions
- showing transitions and results

This keeps the path open for:
- richer terminal UX
- graphical desktop client
- web front end

## Testing Strategy

The project uses layered tests:

- unit tests for scoring, strategy, genome edits, powerups
- system tests for tournament, progression, evolution
- lineage and civil war rules tests
- regression tests for previously discovered bugs
- view model tests for stable text formatting

The goal is to catch both:
- logic bugs
- integration mismatches between systems

## Near-Term Architectural Priorities

The next likely structural improvements are:

- richer successor-screen information
- action pacing tools for featured matches
- economy / reroll system between floors
- saveable run transcripts or replay logs
- more formal separation of run phases into explicit phase objects

## Summary

Prisoner's Gambit is architected as a deterministic, testable simulation core with a modular front end and content layer. The most important design choice is treating the player as a lineage rather than a single body, which allows the game to evolve from a simple prisoner's dilemma tournament into a strategy roguelike with inheritance, succession, and civil war.