# Prisoner's Gambit Roadmap

## Current State

The project now has a strong prototype foundation with:

- seeded deterministic runs
- iterative floor tournaments
- featured player matches
- powerup system with conflict resolution
- referendum layer
- genome edit choices
- lineage inheritance and takeover
- player-lineage descendant naming
- two-phase structure:
  - ecosystem survival
  - civil war
- build identity tags and descriptors
- typed interaction system with `InteractionController` and `RunSession`
- rich round breakdown with directive reasons and per-perk score adjustments
- featured match stance system (cooperate until betrayed, defect until punished, follow autopilot for N rounds, lock last manual move for N rounds)
- web prototype UI for playing featured matches through a browser
- broad automated test coverage

That is enough to say the project is beyond a toy simulation and into real game-prototype territory.

## Roadmap Philosophy

The best path forward is not to add content blindly.

The current priority order should be:

1. clarity
2. pacing
3. meaningful decisions
4. content expansion
5. presentation upgrades

The simulation already has enough mechanics that readability now matters more than raw scope.

## Phase A: Readability and Feedback

### A1. Explain why score changed ✓

Goal:
Make featured match results tell the player which perks fired and why.

Status:
**Complete.** `RoundResolutionBreakdown` now surfaces the directive resolution trace and per-perk `ScoreAdjustment` list. The view layer formats this for both the terminal and the web prototype.

### A2. Show stronger build comparison in successor selection

Goal:
Make descendant selection feel like choosing between genuinely different branches.

Possible additions:
- trait emphasis
- risk rating
- referendum strength
- control potential
- perk synergy notes

### A3. Improve floor summary readability

Goal:
Make the top of the leaderboard easier to interpret at a glance.

Potential additions:
- short identity descriptor under top agents
- clearer distinction between outsiders and lineage
- phase label reminders

## Phase B: Pacing Improvements

### B1. Featured match fast-forward ✓

Goal:
Reduce repetitive input without removing skill expression.

Status:
**Complete.** The stance system handles this:
- cooperate until betrayed
- defect until punished
- follow autopilot for N rounds
- lock last manual move for N rounds

### B2. Smarter autopilot interaction ✓

Goal:
Make it easier to use the genome as a real assistant rather than just a suggestion source.

Status:
**Complete.** The `InteractionController` supports `ChooseRoundAutopilotAction` (single-round and full-match autopilot), and `ChooseRoundStanceAction` for duration-bound behavior templates.

## Phase C: Between-Floor Economy

### C1. Reroll system

Goal:
Give the player more agency over bad offers.

Potential model:
- spend a resource to reroll powerups
- spend a resource to reroll genome edits
- maybe limit rerolls per floor

### C2. New currency or score spending

Goal:
Make score matter beyond leaderboard survival.

Potential uses:
- rerolls
- perk removal
- trait stabilization
- branch rescue effects

### C3. Tradeoff choices

Goal:
Introduce meaningful sacrifices.

Examples:
- lose score for stronger perk choice
- remove a perk to reduce instability
- weaken referendum strength to improve dueling

## Phase D: Deeper Lineage Systems

### D1. Better lineage presentation

Goal:
Make family branches feel like a true dynasty.

Potential additions:
- lineage tree summary
- branch history
- succession log
- deaths and takeovers shown as named milestones

### D2. Succession-specific mechanics

Goal:
Make branch takeover even more meaningful.

Possible mechanics:
- takeover bonuses
- inherited momentum
- branch-specific penalties
- succession perks

### D3. Civil-war specialization

Goal:
Make phase 2 feel even more distinct.

Potential additions:
- civil-war-only perks
- reduced referendum relevance
- sibling rivalry mechanics
- branch grudges or inheritance effects

## Phase E: Content Expansion

### E1. More archetypes

Goal:
Widen the strategy field.

Examples:
- referendum parasites
- false cooperators
- unstable diplomats
- hard control specialists
- anti-lineage predators

### E2. More perks

Goal:
Expand decision space without muddying the system.

Best perk directions:
- information perks
- succession perks
- civil-war perks
- economy-linked perks

### E3. More genome edit types

Goal:
Allow more interesting long-term build shaping.

Potential additions:
- multi-cell edits
- noise reshaping
- referendum tendency edits
- risk-weighted branching edits

## Phase F: Replay and Instrumentation

### F1. Save run transcripts

Goal:
Make seeded runs inspectable after the fact.

Potential contents:
- seed
- floor summaries
- picks
- succession events
- final outcome

### F2. Deterministic replay mode

Goal:
Replay a past run using:
- seed
- logged player decisions

This would be very useful for:
- debugging
- balancing
- sharing interesting runs

### F3. Better analytics

Goal:
Answer questions like:
- which perks are overperforming?
- which branches survive longest?
- what causes most player deaths?
- how often does civil war occur?

## Phase G: UI Evolution

### G1. Better terminal UX

Goal:
Improve readability before jumping to a graphical client.

Possible additions:
- spacing cleanup
- compact views
- color emphasis
- toggled detail levels

### G2. Richer non-terminal UI

Status:
**In progress.** A web prototype for featured matches is available in `web/`. It serves an interactive HTML page at `http://127.0.0.1:8765` and drives `FeaturedMatchWebSession` over JSON.

Long-term direction:
- expand web client to the full run loop
- desktop or hybrid client
- or a dedicated graphical front end

## Phase H: Balance and Design Tuning

### H1. Perk balance pass

Focus:
- control perk dominance
- referendum viability
- civil-war perk distortion
- cooperation survivability

### H2. Phase pacing balance

Focus:
- how long ecosystem phase lasts
- how often civil war happens
- how quickly civil war resolves
- whether runs overstay their welcome

### H3. Branch diversity balance

Focus:
- whether descendants become too samey
- whether mutation pressure is high enough
- whether player-lineage advantages are healthy

## Recommended Immediate Next Steps

My recommended short-term order:

1. Better successor-comparison information
2. Reroll or small economy layer
3. Civil-war-specific perk/content pass
4. Expanded web UI beyond featured match prototype
5. Saveable run transcripts or replay logs

That order improves feel before it expands complexity too much.

## Definition of a Strong Vertical Slice

A strong playable vertical slice would have:

- deterministic seeded runs
- readable build identities
- meaningful featured-match decisions
- interesting successor choices
- a distinct civil war phase
- enough pacing tools that a full run feels smooth
- a small but well-balanced perk pool

The project is already close to that.

## Long-Term Vision

Long-term, Prisoner's Gambit should feel like:
- a strategy roguelike
- a lineage survival game
- a hidden-information deduction game
- a social dilemma simulator twisted into a bloodline war

The prisoner's dilemma should remain the backbone, but the player's memory of a run should come from:
- branch succession
- near-death takeovers
- inferred opponents
- referendum gambits
- final civil-war betrayals

## Summary

The roadmap should prioritize understanding and pacing first, then deepen branch identity and between-floor decision-making, and only then broaden content aggressively. The current prototype already has enough originality to justify polishing toward a sharp vertical slice rather than endlessly expanding systems in every direction.