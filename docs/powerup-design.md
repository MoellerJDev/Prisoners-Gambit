# Prisoner's Gambit Powerup Design

## Purpose of the Powerup System

Powerups are the main way the game bends the simple underlying dilemma into something richer.

Without perks, the game would mainly be:
- reactive genomes
- noise
- evolutionary selection

Perks introduce:
- asymmetry
- control
- tempo
- group-vote manipulation
- score distortion
- sharper identities

They are the most important content-expansion system in the game.

## Design Goals

Powerups should:

1. Change decisions, not just totals
2. Support readable identities
3. Interact with the genome layer rather than replace it
4. Create interesting contradictions
5. Be deterministic when conflicts occur
6. Support both duel-level and floor-level play

## Current Functional Categories

### Scoring perks

These change point outcomes after moves are resolved.

Examples:
- Opening Gambit
- Trust Dividend
- Spite Engine
- Compliance Dividend
- Mercy Shield

These perks reward specific interaction patterns.

### Move-control perks

These alter or force actions before scoring resolves.

Examples:
- Golden Handshake
- Coercive Control
- Counter-Intel
- Panic Button
- Last Laugh

These are the most mechanically dramatic perks because they can change the actual shape of a round.

### Referendum perks

These affect the floor-wide vote or its reward.

Examples:
- Unity Ticket
- Saboteur Bloc
- Bloc Politics

These help create builds that care about more than pairwise dueling.

## Current Perks

### Opening Gambit

Function:
Rewards early defection.

Use case:
Supports aggressive openers and tempo-based builds.

### Trust Dividend

Function:
Gives bonus value from mutual cooperation.

Use case:
Supports consensus, stabilizer, and referendum-friendly builds.

### Last Laugh

Function:
Forces defection on the final round.

Use case:
Supports endgame betrayal patterns and anti-trust closers.

### Spite Engine

Function:
Rewards retaliatory or punitive defection after being defected against.

Use case:
Supports punishing builds.

### Mercy Shield

Function:
Reduces or nullifies the payoff an opponent gets from repeated defection after betrayal.

Use case:
Supports defensive builds that blunt exploiters.

### Golden Handshake

Function:
Attempts to force cooperation on both sides early.

Use case:
Supports controlled trust openings and consensus builds.

### Coercive Control

Function:
Pushes the opponent into cooperation under specific prior conditions.

Use case:
Supports hard control and exploitation.

### Counter-Intel

Function:
Attempts to force cooperation from an opponent after they defected.

Use case:
Supports move manipulation and tempo recovery.

### Panic Button

Function:
Locks both players into defection after mutual breakdown.

Use case:
Supports collapse spirals and anti-forgiveness loops.

### Compliance Dividend

Function:
Rewards successful exploitation when the opponent is held in cooperation.

Use case:
Supports cruel control builds.

### Unity Ticket

Function:
Forces the owner's referendum vote to cooperation.

Use case:
Supports referendum builds and consensus-oriented lines.

### Saboteur Bloc

Function:
Forces the owner's referendum vote to defection.

Use case:
Supports anti-consensus and spoil strategies.

### Bloc Politics

Function:
Rewards successful cooperative referendum participation.

Use case:
Supports branch lines that care about the floor-wide economy.

## Directive Resolution Model

Move-changing perks do not directly override each other ad hoc.

Instead, they emit directives with priorities.

Priority ladder:
- Override
- Force
- Lock

Resolution rules:
- highest priority wins
- if top directives agree, use that move
- if top directives conflict, defection wins

This gives the system consistent behavior.

## Why Defection Wins Ties

Defection wins contradictory equal-priority directives because:
- it is deterministic
- it fits the theme of mistrust
- it prevents ambiguous resolution
- it creates a slightly harsh bias that players can learn around

This should remain a stable rule unless the game introduces a third action or more explicit stack logic.

## Design Principles for New Perks

### 1. Prefer stateful interaction over flat bonuses

Good:
If they defected last round, your retaliation gains bonus points.

Weaker:
Gain 1 point every round.

The first creates texture. The second mostly inflates numbers.

### 2. Perks should reinforce build identity

A perk should help the player understand what kind of branch they are building.

Good signs:
- it supports a recognizable play pattern
- it creates readable tags
- it changes how the player thinks about a matchup

### 3. Perks should not erase the genome layer

If perks completely dominate every move, genomes become irrelevant.

Perks should bend, pressure, or redirect the genome, not replace strategy identity entirely.

### 4. Global and local systems should both matter

Some perks should matter in:
- duels
- featured matches
- civil war

Others should matter in:
- referendums
- floor-wide incentives
- broader run planning

A healthy pool needs both.

## Good Future Perk Directions

### Information perks

These would affect the hidden-opponent game.

Examples:
- reveal one likely trait of the current masked opponent
- hide one of your own visible tags
- spoof a public profile or visible signal

These are very promising because they deepen deduction.

### Succession perks

These would affect lineage transition.

Examples:
- inherit an extra perk on takeover
- gain points on branch succession
- preserve a temporary effect through death

These fit the lineage fantasy very well.

### Civil-war perks

These become stronger when outsiders are gone.

Examples:
- bonus against same-lineage opponents
- stronger final-round betrayal inside civil war
- greater reward for eliminating sibling branches

These would make phase 2 even more distinct.

### Economy-linked perks

If a reroll or shop layer is added later, perks could:
- reduce reroll cost
- increase between-floor rewards
- convert referendum success into currency

## Bad Future Perk Patterns

Avoid perks that:
- give large unconditional score every round
- completely override all other systems too often
- are too hard to explain from output
- have highly specific trigger logic with weak payoff
- create hidden behavior the player cannot learn

## Readability Requirements

As the perk pool grows, the player needs to understand:
- what happened
- why it happened
- which perk mattered

That means future UI work should show:
- which perks fired in a featured round
- which directive won
- how score changed from base to modified result

Without that, strong perk systems become muddy.

## Perks and Build Identity

Perks contribute heavily to inferred identity tags.

Examples:
- Trust Dividend suggests Consensus
- Coercive Control suggests Control
- Bloc Politics suggests Referendum
- Spite Engine suggests Punishing
- Last Laugh suggests Tempo

This relationship between perks and build identity should remain strong.

## Perks and Civil War

Civil war changes how some perks feel.

Examples:
- cooperation perks may be more fragile
- late betrayal perks become more dramatic
- control perks become more targeted
- referendum perks may lose or gain value depending on population size

That means some perks may need future balancing for phase 2 specifically.

## Future Balancing Questions

Key questions to watch:
- Are control perks too dominant when stacked?
- Are referendum perks strong enough to justify taking them?
- Do endgame betrayal perks dominate civil war too hard?
- Are cooperation perks too weak without support?
- Are some perks too dependent on featured matches for value?

## Summary

The perk system is the main force that turns Prisoner's Gambit from a clean simulation into a roguelike strategy game. The best perks change how the player reads a situation, not just how many points appear. Future perk design should prioritize identity, interaction, and clarity over raw volume.