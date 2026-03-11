# Prisoner's Gambit Gameplay Design

## High Concept

Prisoner's Gambit is a strategy roguelike built around the iterated prisoner's dilemma.

You do not play a single prisoner.

You play a lineage of strategies trying to dominate the table, survive evolutionary pressure, outlast outsiders, and ultimately outcompete your own descendants.

The game blends:
- tactical round-by-round decisions
- strategic build shaping
- evolutionary drift
- hidden-opponent deduction
- branch succession
- late-run civil war

## Core Fantasy

The player fantasy is:

I am not one body.
I am a lineage.
If one host dies, the strategy can survive elsewhere.

That makes death feel less binary and more dynastic. A run is the story of a bloodline of ideas, not just a single avatar.

## Core Loop

A run currently follows this pattern:

1. Generate a population of agents
2. Mark one agent as the active player host
3. Run a full floor tournament
4. Rank agents by score and wins
5. Eliminate the lower portion
6. If the current host dies but lineage survives, choose a successor
7. Offer a powerup
8. Offer a genome edit
9. Give some AI survivors random powerups
10. Repopulate from survivors during ecosystem phase
11. Transition into civil war when all outsiders are gone
12. Continue until the lineage is destroyed or one final branch remains

## Match Structure

Each pair of agents plays a multi-round iterated prisoner's dilemma match.

### Base payoff rules

Per round:
- if both cooperate, both gain 1 point
- if one defects and the other cooperates, the defector gains 1 point and the cooperator gains 0
- if both defect, both gain 0

This is intentionally not a classic temptation-heavy payoff matrix. The game is built around a simpler point economy and then expanded by perks.

## Floor Structure

Each floor includes:

- full round-robin pairwise play across the population
- several featured matches for the player
- one floor-wide referendum

### Featured matches

These are the primary point of direct skill expression.

During featured matches, the player sees:
- a masked opponent label
- round number
- both histories
- current match score
- an autopilot recommendation
- the floor roster of possible opponents

The player should infer who they may be facing based on:
- observed move patterns
- visible perks in the roster
- public profile
- derived build identity tags

### The roster mind game

The player is intentionally not told exactly which opponent they are facing in a featured match.

This creates a deduction layer:
- Is this the retaliatory cooperator?
- Is this the greedy opener?
- Is this the referendum manipulator?
- Is this one of my own descendants?

That uncertainty is a core part of the design.

## Autopilot and Human Input

Every agent has a genome that acts as an autopilot.

The human player is not choosing from a blank slate each round. Instead, the player is piloting on top of a built strategy.

This matters because the run is about shaping a lineage over time, not manually micromanaging every possible decision in every match.

The intended feel is:
- the genome gives identity
- the player gives tactical intervention
- perks bend rules around both

## Genome Design

Each genome currently contains:
- first move
- response when the last round was C/C
- response when the last round was C/D
- response when the last round was D/C
- response when the last round was D/D
- noise value

This produces compact but expressive strategy variation.

Example interpretations:
- cooperative retaliator
- greedy exploiter
- forgiving stabilizer
- chaotic opportunist

## Perk Design Goals

Perks should do more than just add points.

They should:
- create asymmetric incentives
- force moves
- manipulate opponents
- influence referendum outcomes
- alter timing
- create contradictions that must resolve cleanly

The perk system works best when it changes how players read situations, not just raw totals.

## Contradiction Resolution

Because some perks force actions, contradictions can happen.

The design rule is:

- higher priority directives win
- if equal highest-priority directives conflict, defection wins

This creates predictable resolution and avoids ambiguous behavior.

## Referendum System

Once per floor, all agents participate in a global cooperation/defection vote.

Rules:
- if cooperation reaches majority or tie, cooperators get a reward
- if defection has majority, nobody gets rewarded

This adds a second layer beyond pairwise optimization.

A strategy can be:
- strong in duels but weak in group behavior
- weak in duels but excellent at farming referendum value
- specialized in forcing referendum outcomes

That helps widen viable archetypes.

## Evolution and Repopulation

At the end of each ecosystem-phase floor:
- the bottom portion is eliminated
- survivors persist
- offspring are generated from survivors

Descendants inherit:
- lineage id
- lineage depth
- some perks
- a mutated genome

Player-lineage descendants mutate more aggressively than normal outsiders. This gives the lineage a better chance to diversify and survive.

## Lineage Succession

If the current host dies, the run does not immediately end.

If any descendant from the player lineage survives, the player chooses which branch to assume next.

This creates a strong strategic question:
- do I keep the stable build alive?
- do I jump into the strongest scorer?
- do I inhabit the strangest branch because it counters the field better?

Succession should feel like a major dramatic beat, not just a fail-safe.

## Naming and Branch Identity

Descendants should feel like branches, not formatting artifacts.

Player-lineage offspring use lineage naming like:
- Heir Alpha
- Heir Beta
- Heir Gamma

This improves:
- readability
- emotional attachment
- late-game civil war clarity

## Build Identity

To make branches and opponents easier to understand, agents are given interpreted tags and descriptors derived from their genome and perks.

Examples:
- Cooperative
- Aggressive
- Retaliatory
- Exploitative
- Control
- Referendum
- Consensus
- Punishing
- Unstable
- Precise

These are not separate mechanics. They are readability tools.

## Phase 1: Ecosystem Survival

In the first phase, the lineage competes against outsiders.

Goals:
- keep the lineage alive
- shape strong branches
- gather perks and edits
- outlast non-lineage agents

This phase is about expansion, adaptation, and inference.

## Phase 2: Civil War

When no outsiders remain, the game enters civil war.

In this phase:
- only lineage members remain
- repopulation stops
- surviving branches eliminate one another until one remains

This is the game's strongest thematic turn.

The meaning of victory changes:
- first you prove the lineage can dominate the ecosystem
- then you prove your chosen branch deserves to be the final form

## Win and Loss States

### Loss

You lose when no surviving agents remain in your lineage.

### Full victory

You win when your current branch is the last surviving lineage member after the civil war.

## Sources of Skill Expression

The game’s skill is meant to come from several layers at once:

### Tactical skill
Choosing when to trust or betray during featured matches.

### Deduction skill
Inferring hidden opponents from observed behavior and roster clues.

### Build skill
Choosing perks and genome edits that shape a coherent branch.

### Succession skill
Choosing the right descendant when the current host dies.

### Macro skill
Balancing pairwise efficiency against referendum incentives and long-run branch survival.

## Current Strengths of the Design

The current design already has:
- a clear strategic identity
- hidden-opponent mind games
- evolutionary replayability
- dramatic branch succession
- a meaningful second phase

## Current Friction Points

The most likely friction areas are:
- too much repetitive featured-match input
- some build effects being hard to read in the moment
- some genome edit choices feeling too opaque
- perk interactions needing clearer explanation in results

These are presentation and pacing issues more than mechanical problems.

## Design Priorities Going Forward

The next layers should focus on:
- better pacing in featured matches
- richer branch comparison tools
- more meaningful between-floor resource decisions
- improved explanation of why score swings happened
- stronger endgame identity in civil war

## Summary

Prisoner's Gambit works best when it feels like a game about evolving ideas under pressure. The prisoner's dilemma is the substrate, but the real design goal is lineage strategy: shaping branches, surviving selection, reading hidden opponents, and deciding which descendant becomes the final face of the bloodline.