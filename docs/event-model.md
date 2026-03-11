# Prisoner's Gambit Event Model

## Overview

Prisoner's Gambit uses an internal event bus to publish structured run events as the simulation progresses.

The event model exists to support:

- logging
- debugging
- future replay tools
- analytics
- alternate renderers or observers
- cleaner separation between systems

The event system is intentionally lightweight.

## Core Concepts

### Event

An event has:
- a name
- a payload

Example event shape, expressed descriptively:
An event named `powerup_selected` might include a payload with:
- floor: 4
- player: Heir Alpha
- powerup: Trust Dividend

### EventBus

The bus supports subscribers that listen for:
- a specific event name
- all events using a wildcard

This allows both targeted behavior and broad observability.

## Why Events Matter Here

The game has many moving parts:
- tournament resolution
- referendum outcomes
- survivor selection
- lineage succession
- civil war transition
- run completion

Without an event stream, observing run behavior would require invasive coupling or log scraping. Events provide a cleaner model.

## Current Event Types

### run_started

Published when a run begins.

Typical payload:
- seed
- player

Purpose:
- identify the run
- anchor downstream logs or replay data

### floor_started

Published when a floor begins.

Typical payload:
- floor
- label
- population
- rounds_per_match
- featured_matches
- referendum_reward

Purpose:
- record floor configuration
- support future run summaries

### floor_completed

Published when a floor ends.

Typical payload:
- floor
- label
- top_agent
- top_score

Purpose:
- summarize results
- track leaderboard progression

### floor_referendum_resolved

Published after the floor referendum.

Typical payload:
- floor
- cooperators
- defectors
- cooperation_prevailed

Purpose:
- capture global voting outcomes
- support balance inspection for referendum mechanics

### survivors_selected

Published after survivor elimination logic.

Typical payload:
- floor
- survivors
- eliminated
- ecosystem_phase

Purpose:
- record population cuts
- support lineage tracing

### powerups_offered

Published when perk offers are generated for the player.

Typical payload:
- floor
- offers

Purpose:
- inspect content generation
- debug offer quality

### powerup_selected

Published when the player takes a perk.

Typical payload:
- floor
- player
- powerup

Purpose:
- reconstruct build progression
- compare run outcomes by choices

### genome_edit_selected

Published when the player chooses a genome edit.

Typical payload:
- floor
- player
- edit

Purpose:
- track build drift over time

### player_successor_selected

Published when the current host dies and control transfers to another branch.

Typical payload:
- floor
- successor
- lineage_id

Purpose:
- mark one of the most important transitions in a run
- enable lineage-based replay summaries

### player_lineage_eliminated

Published when the last surviving member of the player lineage is gone.

Typical payload:
- floor
- lineage_id

Purpose:
- mark true defeat condition

### civil_war_started

Published when all outsiders are gone and only the lineage remains.

Typical payload:
- floor
- lineage_members

Purpose:
- mark the start of phase 2
- segment run data into ecosystem vs civil war

### run_completed

Published when the run ends in victory or controlled completion.

Typical payload:
- final_floor
- player
- seed

Purpose:
- close out the run
- support replay and result indexing

## Event Publishing Locations

### Application Layer

`RunApplication` publishes major progression and run-lifecycle events:
- run started
- survivors selected
- player successor selected
- civil war started
- run completed
- lineage eliminated

### Tournament Layer

`TournamentEngine` publishes floor-level events:
- floor started
- referendum resolved
- floor completed

This split is intentional:
- systems publish what they own
- orchestration publishes cross-system state transitions

## Subscriber Types

### Logging Subscribers

The current main subscriber is a logging listener.

It consumes events and writes them to logs in a structured way.

### Future Subscribers

The event model is designed so future listeners can be added for:
- JSON run recording
- replay exports
- debug dashboards
- statistics aggregation
- alternate UI synchronization

## Event Design Principles

### 1. Events should describe facts, not commands

Good:
- powerup_selected
- civil_war_started

Bad:
- do_phase_transition
- grant_reward_now

Events should report what happened.

### 2. Payloads should be compact but useful

Payloads should contain enough information to understand the event without dumping huge object graphs.

### 3. Names should be stable

Tests and tools may rely on event names, so renaming events casually is a bad idea.

### 4. Events should align to meaningful transitions

Do not emit events for every tiny internal step unless that step is meaningful to:
- logging
- analysis
- replay
- debugging

## Potential Future Event Types

A few event types that may be useful later:

### featured_round_resolved

Potential payload:
- floor
- masked opponent
- round index
- chosen move
- opponent move
- score delta

Use case:
- full replay reconstruction

### ai_powerup_granted

Potential payload:
- floor
- recipient
- powerup

Use case:
- debugging runaway AI strength

### civil_war_completed

Potential payload:
- floor
- winner
- remaining lineage count

Use case:
- clearer end-state reporting

### economy_spent

For a future reroll or shop system.

Potential payload:
- floor
- player
- currency type
- amount
- purpose

## Replay Potential

The event system is the foundation for a future replay layer.

A replayable run would ideally combine:
- seed
- player decisions
- event stream

In a deterministic build, that could reconstruct much of the run without needing full snapshots every step.

## Testing the Event Model

Tests should verify:
- named subscribers receive matching events only
- wildcard subscribers receive all events
- event order is preserved
- payloads pass through unchanged

This protects the event bus from subtle regressions.

## Summary

The event model provides structured observability for Prisoner's Gambit. It keeps logging and diagnostics decoupled from game systems and lays the groundwork for replay tools, analytics, and future UI layers.