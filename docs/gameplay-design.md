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

## Core Loop Audit (Current)

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

### Which current steps actually shape heirs?

The current loop has strong heir-focused mechanics, but some are framed as maintenance instead of dynastic pressure.

| Loop step | Direct heir value today | Design issue to address |
| --- | --- | --- |
| Tournament + featured matches | Generates behavioral evidence for branch identity and field reading. | Framed mostly as score optimization, not branch testing. |
| Ranking + elimination | Applies selection pressure and creates successor stakes. | Read as generic roguelike culling pass. |
| Successor selection | Core succession decision with real strategic consequences. | Happens as a fallback moment instead of a floor-level objective. |
| Powerup + genome edit offers | Primary branch-shaping tools. | Reads like standard between-floor upgrades if not tied to successor intent. |
| AI perk grants + repopulation | Creates future threats and branch divergence. | Feels like background simulation bookkeeping. |
| Civil war transition | Pays off long-term branch planning. | Can feel abrupt if floor-by-floor threat seeding is under-emphasized. |

### Refocused floor identity

Each floor should be treated as a **breeding + evaluation stage** for future heirs:

1. **Probe the field** in featured matches to learn which archetypes are rising.
2. **Stress-test your branch** in the full tournament to reveal strengths and liabilities.
3. **Apply selection pressure** (ranking/elimination) as a lineage filter, not just a loss gate.
4. **Handle succession pressure immediately**: evaluate which surviving heir you would choose if death happened next floor.
5. **Commit branch intent** through one powerup and one genome edit chosen for successor quality, not raw tempo.
6. **Seed future threats** via AI growth + repopulation and deliberately read what kind of civil war this enables.
7. Repeat until outsiders are gone, then resolve the branch contest in civil war.

This preserves deterministic structure while changing the meaning of existing steps.

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

They are also the floor's main **lineage scouting pass**: each featured match should help answer what future heir profile is safest against the likely next-floor field.

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

### Featured match stances

To reduce repetitive input without removing skill expression, the player can set a stance for the current featured match. Available stances:

- **Cooperate until betrayed** — cooperate each round until the opponent defects, then defect
- **Defect until punished** — defect each round until the opponent retaliates with defection, then cooperate
- **Follow autopilot for N rounds** — delegate to the genome suggestion for a fixed number of rounds
- **Lock last manual move for N rounds** — hold the most recent manual choice for a fixed number of rounds

Any manual move overrides the active stance immediately.

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

## Round Breakdown and Score Transparency

After each featured round, the player sees a breakdown that shows:

- the genome's intended move for each side before directives applied
- which directives fired and the final move they produced
- the base payoff
- each perk's score adjustment, labeled by source
- the final point totals for both sides

This makes perk effects explicit rather than hidden. A player can always answer: "Why did my score change by that amount?"

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

To make divergence appear earlier, player-lineage offspring also receive a deterministic branch-focus push (safe, ruthless, unstable, or referendum-oriented). This is intentionally limited and tuned so branches diverge in recognizable directions rather than pure noise.

Design intent: repopulation is not filler content. It is the mechanism that turns this floor's choices into next floor's succession dilemma.

## Lineage Succession

If the current host dies, the run does not immediately end.

If any descendant from the player lineage survives, the player chooses which branch to assume next.

This creates a strong strategic question:
- do I keep the stable build alive?
- do I jump into the strongest scorer?
- do I inhabit the strangest branch because it counters the field better?

Succession should feel like a major dramatic beat, not just a fail-safe.

Refocus rule: even when the current host survives, the player should evaluate each floor as if succession might happen on the next one.

This keeps pressure on the three key questions:
- what kind of branch am I creating?
- what kind of future threat am I enabling?
- what successor would I want if I died next floor?

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
- some build effects still needing better live explanation in the terminal
- some genome edit choices feeling too opaque
- succession comparison not yet rich enough

The round breakdown and stance system address the pacing and transparency concerns that were most acute. The remaining friction is about presentation depth more than mechanical problems.

## Design Priorities Going Forward

The next layers should focus on:
- richer branch comparison tools that foreground successor readiness
- between-floor choices framed as heir-shaping commitments, not maintenance
- stronger floor summaries that explain which future threats were created
- stronger endgame identity in civil war
- expanded web UI beyond the featured match prototype

## Summary

Prisoner's Gambit works best when it feels like a game about evolving ideas under pressure. The prisoner's dilemma is the substrate, but the real design goal is lineage strategy: shaping branches, surviving selection, reading hidden opponents, and deciding which descendant becomes the final face of the bloodline.
