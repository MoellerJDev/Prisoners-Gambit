# Choice and Strategy Refactor Design

## Why this document exists

The current prototype has a strong structural loop, but the between-floor choices are under-delivering on clarity and drama.

The main issues are not just "copy quality" bugs. They come from a deeper mismatch:

- the simulation thinks in tags, doctrine families, and low-level triggers
- the UI often exposes those internals directly
- the player needs sharp strategic questions, not raw simulation metadata
- several choice fields are generated independently, so they can repeat or fail to differentiate candidates
- the prisoner's dilemma layer still matters, but the game does not yet turn that into a distinctive lineage-building fantasy often enough

This document proposes a refactor that solves both layers:

1. refactor the choice presentation model so choices are readable, flavorful, and strategically distinct
2. refactor the game loop so each floor asks a more interesting dynasty-level question than "which upgrade is numerically best?"

## Current pain points

### 1. Help surfaces are not contextual

The `?` button on the Decision Details card currently routes to "Controlled Vote" even when the active decision is successor choice.

That creates two problems:

- it teaches the wrong thing at the wrong time
- it makes the UI feel like it is showing a leftover developer artifact instead of a designed explanation surface

Rule for the refactor:

- help must be contextual to the active decision, not hard-wired to one glossary term

### 2. Successor detail content is too verbose and too repetitive

Today the successor detail surface can produce output like:

- different heirs share the same "Pick for" line
- different heirs share the same "Risk" line
- the "Clue" field is a long paragraph that tries to carry future path, stability, and confidence all at once

This makes the expanded card feel flatter than it should. It reads like a dense explanation blob instead of a decisive comparison tool.

Rule for the refactor:

- every successor option should answer three different questions quickly:
  - what does this branch help me do next floor?
  - what kind of run does it push me toward?
  - what is the failure mode if I commit to it?

### 3. Powerup tags leak internal identifiers

Examples:

- `rewards_betrayal`
- inconsistent capitalization like `chaos`
- mechanical label formats like `Trigger Every round.`

These are useful authoring fields, but poor player-facing language.

Rule for the refactor:

- internal taxonomy must never be shown directly to players
- all surfaced tags should be curated labels, not debug strings

### 4. Genome edit explanations are too wordy and too abstract

Current issues:

- "Choose if..." language is verbose
- "low-noise execution" is not player language
- "drift" is conceptually useful, but the presentation is too text-heavy to support quick comparison

Rule for the refactor:

- genome edits should read like branch rewrites, not advisory paragraphs

### 5. The strategic layer is still too thin between C/D and upgrades

The game has strong ingredients:

- masked opponents
- featured inference
- referendum pressure
- lineage succession
- civil war

But the floor-to-floor build layer still too often feels like:

- play a few prisoner's dilemma rounds
- get a reward
- choose an upgrade

That is a decent skeleton, but not yet a uniquely "dynasty under pressure" strategy game.

Rule for the refactor:

- every between-floor choice should feel like committing the lineage to a doctrine, not selecting generic reward text

## Design goals

The refactor should optimize for these outcomes.

### Choice goals

1. A player should understand what a choice does in five seconds.
2. A player should feel the strategic identity of each option before reading the full detail text.
3. The detail view should deepen the choice, not restate the card with more words.
4. Every choice type should use a consistent information hierarchy.

### Strategy goals

1. The prisoner's dilemma should remain the atomic move language of the game.
2. The game should become more distinctive at the dynasty level, not by adding random complexity to each round.
3. Successor, powerup, and genome choices should all push on the same long-term strategic axis.
4. The player should be shaping a lineage doctrine, not just accumulating perks.

### Testing goals

1. Tests should validate decision structure and behavior, not freeze fragile copy phrasing.
2. Runtime tests should assert that choices are distinct in meaningful fields, not only that text exists.
3. UI presentation tests should target semantic sections and labels, not exact prose paragraphs unless the wording is intentionally locked.

## Proposed design direction

## A. Replace "details blob" with a decision brief model

All three choice types should present information in a common shape:

- Hook: the one-sentence reason to care
- Edge: what this helps you do now
- Cost: what pressure or weakness it creates
- Future: what doctrine or branch direction it commits you toward
- Confidence: how reliable the read is

The current UI does not need a full redesign to do this. The existing compact-card plus detail-surface layout can stay. What changes is the content model that feeds it.

### Shared information hierarchy

On the compact card:

- Title
- One strong strategic sentence
- Two or three curated tags
- One fit line

On the detail surface:

- short labeled rows, not a long unordered list of mixed-value facts
- rows grouped by strategic role, not by raw source field

The model should be:

```text
Why now
What it changes
What it risks
What future it builds
How confident we are
```

That shape works for successors, powerups, and genome edits.

## B. Successor choice refactor

### Current problem

Successor choice mixes together:

- identity tags
- heuristics
- long-form clue interpretation
- generic template prose

This can flatten meaningful differences.

### New successor presentation model

Each candidate should expose these player-facing fields:

- `headline`
  - short sentence that distinguishes the branch immediately
  - example: "Reliable coalition heir with weak closing tempo."
- `play_pattern`
  - how this heir tends to win
  - example: "Builds value through reciprocal loops and safe match coverage."
- `break_point`
  - where this heir loses or destabilizes
  - example: "Falls behind against explosive punish-control cousins."
- `lineage_future`
  - what kind of dynasty this pick creates
  - example: "Pushes the house toward consensus and legitimacy."
- `clue_read`
  - short clue alignment summary
  - example: "Clue support: moderate. Cooperation is reinforced; deception is under-read."
- `confidence`
  - `High`, `Medium`, or `Low`

### New successor detail layout

Instead of:

- Cause
- Pick for
- Risk
- Pitch
- Clue

Use:

- `Pattern`
- `Why now`
- `Watch out`
- `Dynasty future`
- `Clue read`

This is clearer because it maps to the player's real question:

- what kind of ruler is this?
- why am I taking them now?
- what trouble do they create later?

### Successor clue rewrite rule

The current clue paragraph should be decomposed into structured fragments:

- future path
- stability
- confidence

Those can still be generated from the same inference system, but they should be rendered as separate short lines.

Example:

Current:

`Future path: ... Stability: ... Clue confidence: ...`

Target:

- `Future: Consensus branch built on reciprocity and legitimacy.`
- `Stability: Good if trust loops hold; weak in betrayal mirrors.`
- `Confidence: Medium. Cooperation is supported, deception is not.`

### Successor differentiation rule

At least one of these fields must be unique across visible successor candidates:

- `headline`
- `play_pattern`
- `break_point`
- `lineage_future`

If two candidates produce the same values for all of those, the generator should treat that as a content bug.

## C. Powerup choice refactor

### Current problem

Powerups are mechanically rich but presented as:

- trigger text
- effect text
- raw tags
- fit hint

This exposes internal data cleanly, but not compellingly.

### New powerup framing

Powerups should be presented as tactical doctrines, not just objects.

Each powerup should expose:

- `hook`
  - short strategic fantasy
  - example: "Punish trust openings for fast tempo."
- `timing`
  - when it matters
  - example: "Opens strongest on round 1."
- `plan`
  - how to use it
  - example: "Best in lines that can force or bait cooperation."
- `cost`
  - what it neglects or risks
  - example: "Weak when the floor shifts into stable peace loops."
- `fit_label`
  - curated, flavorful, slightly directional

### Replace raw tags with curated player-facing tags

Internal tags like:

- `rewards_betrayal`
- `referendum_control`
- `final_round_payoff`

should be mapped to labels like:

- `Betrayal payoff`
- `Vote control`
- `Final-round burst`

All surfaced labels should be:

- title case
- no underscores
- no trailing periods
- consistent in tone

### Trigger/effect style guide

Instead of:

- `Trigger: Every round.`
- `Effect: Gain bonus...`

Use:

- `When: Every round`
- `Plan: Turns forced asymmetry into score`

This is shorter, more uniform, and less robotic.

### Crown-piece presentation

`Crown piece / dynasty-defining` is directionally good, but it should become a deliberate tiering concept.

Suggested label:

- `Crown move`

Suggested hover/detail explanation:

- `A house-defining pickup that can reorient your lineage plan.`

### Fit hint rewrite

The current fit labels are strong in tone:

- `Deepen house`
- `Mutate lineage`
- `Power risk`

But they need one more degree of clarity.

Keep the labels, but add a stable explanation model:

- `Deepen house`: strengthens your current doctrine
- `Mutate lineage`: crosses into a new doctrine lane
- `Power risk`: high ceiling, higher branch distortion

That keeps the flavor while removing ambiguity.

## D. Genome edit refactor

### Current problem

Genome edits are structurally important, but their presentation is too advisory and text-heavy.

Examples like:

- `Choose if you want heirs to ...`
- `low-noise execution`

read like design notes, not game decisions.

### New genome edit framing

Genome edits should be shown as branch rewrites.

Each offer should expose:

- `rewrite`
  - the behavioral change
  - example: `After betrayal: hold C -> punish with D`
- `doctrine_shift`
  - concise doctrine movement
  - example: `Shift: Trust -> Control`
- `tempo_note`
  - what pacing changes
  - example: `Tempo: earlier punish window`
- `stability_note`
  - what it gives up
  - example: `Cost: less forgiving in long peace loops`

### Replace vague terminology

Examples:

- `low-noise execution` -> `predictable line`
- `high noise` -> `chaotic line`
- `drift` -> `Shift`

Keep the underlying concept of doctrine movement, but present it in player language.

### Reduce "Choose if..." wording

Replace advisory copy with declarative strategic language.

Current:

- `Choose if you want heirs to bank value through reciprocal trust loops.`

Target:

- `Builds heirs that profit from trust loops.`

or

- `Pushes the line toward trust-loop play.`

This is shorter, less patronizing, and easier to compare.

## E. Contextual help refactor

### Problem

The current help model is term-centric. The user is often asking a phase question instead.

### New help model

The `?` on the Decision Details card should open a context brief for the active decision type:

- Successor choice:
  - what "Why now", "Watch out", "Dynasty future", and "Clue read" mean
- Powerup choice:
  - what "When", "Plan", "Cost", and "Fit" mean
- Genome edit choice:
  - what "Rewrite", "Shift", "Tempo", and "Cost" mean
- Floor vote:
  - what controlled vote means

Controlled Vote should remain in the glossary, but it should not be the default help for every decision type.

## F. The deeper game refactor: Dynasty Doctrine Commitments

The bigger design problem is that the game still has a gap between:

- round-level C/D decisions
- between-floor perk/edit selections

The game needs a stronger middle layer that turns those choices into a recognizable run identity.

### Proposal: Doctrine Commitments

Each floor, the lineage carries a visible doctrine commitment. This is not a third move choice in each round. It is a dynasty-level posture that shapes how choices are evaluated.

Examples:

- `Consensus House`
- `Control Machine`
- `Retaliation Creed`
- `Shadow Court`
- `Bloc Empire`
- `Chaos Succession`

### What commitments do

A doctrine commitment should:

- bias what successor futures feel safe
- change how powerups and genome edits are framed
- alter floor summary language
- feed civil-war pressure and dynasty identity
- create stronger strategic coherence without replacing C/D

### Why this helps

It keeps the prisoner's dilemma core intact:

- rounds are still C or D
- genomes still define reaction logic
- powerups still bend incentives

But now the player is not only asking:

- cooperate or defect?

They are also asking:

- what kind of house am I turning these choices into?

That is where the game becomes more unique.

### Commitment sources

Commitments should not be a separate menu if avoidable. They should emerge from:

- chosen successor
- chosen powerups
- chosen genome edits
- featured inference trends

The UI should surface them as the run's current doctrine arc.

### Example

If the player picks:

- a consensus heir
- trust-loop powerups
- a forgiving genome rewrite

the house should visibly become a `Consensus House`.

That should matter because:

- certain future offers deepen it
- some offers mutate away from it
- civil war recognizes it as strong in some mirrors and weak in others

This creates a clean "build fantasy" without bloating the round rules.

## G. Content generation refactor

The current generated prose is too field-by-field. It needs an intermediate presentation model.

### Proposed content pipeline

Today:

- simulation data -> raw view fields -> UI

Target:

- simulation data -> strategic presentation model -> UI

Each choice type should have a presenter that translates internal state into player-facing sections.

Suggested modules:

- `successor_choice_presenter.py`
- `powerup_choice_presenter.py`
- `genome_choice_presenter.py`
- `choice_copy.py`

These presenters should:

- normalize internal tags into surfaced labels
- guarantee differentiated fields where required
- keep copy short and structured
- make confidence and risk explicit

This is the cleanest way to improve the UX without filling core simulation code with UI prose rules.

## H. Testing refactor

The user asked for a design that anticipates major test refactors. This is necessary.

### What to stop testing directly

Avoid locking tests to:

- exact long-form prose paragraphs
- CSS-transformed casing
- brittle card text that is supposed to evolve for clarity

### What to test instead

#### Presenter tests

Add tests that validate:

- internal tags map to curated user-facing labels
- successor candidates produce differentiated strategic briefs
- powerups never surface raw underscore tags
- genome edits never surface banned phrasing like `low-noise execution`

#### Slice tests

Validate:

- the decision payload contains the structured presenter fields the UI expects
- successor clue still uses `featured_inference_context` as the source input
- contextual help type follows the active decision

#### Runtime tests

Validate:

- the active help panel changes with decision type
- choice details show the new section headers
- successor options surface distinct `Why now` or `Dynasty future` lines
- powerup tags are user-facing labels
- genome edit detail text stays concise

### Suggested regression invariants

Add explicit invariants for future copy/content work:

- no surfaced tag may contain `_`
- no surfaced powerup tag may be lowercase-only unless intentionally branded
- no decision help button may default to an unrelated glossary term
- no successor detail surface may merge future path, stability, and confidence into one raw sentence blob

## I. Delivery plan

### Phase 1: Presentation cleanup without mechanic changes

Ship first:

- contextual help refactor
- powerup label normalization
- successor clue decomposition
- genome wording cleanup
- presenter layer introduction

Goal:

- immediate UX improvement with low simulation risk

### Phase 2: Distinct strategic briefs

Ship second:

- successor differentiation rules
- powerup hook/plan/cost framing
- genome rewrite/shift/cost framing
- fit hint clarification

Goal:

- make every choice feel like a strategic commitment instead of a text block

### Phase 3: Doctrine commitment system

Ship third:

- visible dynasty doctrine state
- stronger integration between successor, powerup, genome, and civil war
- floor summaries framed around doctrine arcs

Goal:

- make the game feel uniquely about evolving a bloodline of ideas

## Summary

The current game is not missing complexity at the round level. It is missing a stronger bridge between its elegant C/D core and its lineage fantasy.

The right answer is not "make the prisoner's dilemma more complicated every turn."

The right answer is:

- keep C/D as the atomic move language
- make choices cleaner, sharper, and more strategically legible
- make the lineage doctrine visible and consequential
- ensure every between-floor choice feels like shaping a future ruler, not reading a generated tooltip

That is the refactor path most likely to make Prisoner's Gambit feel distinct, memorable, and worth mastering.
