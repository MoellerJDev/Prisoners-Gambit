# Testing Strategy for Prisoner's Gambit

This document defines a scalable testing architecture so correctness can be validated from CI runs without relying on manual local play.

## 1) Current coverage audit (baseline)

### Pure unit tests
- Core rules and mechanics: `tests/test_scoring.py`, `tests/test_strategy.py`, `tests/test_powerups.py`, `tests/test_genome_edits.py`, `tests/test_events.py`.
- Content and deterministic generation pieces: `tests/test_content_generation.py`, `tests/test_offer_divergence.py`.

### Interaction/controller tests
- Typed decision loop + action validation: `tests/test_interaction_controller.py`, `tests/test_run_session.py`.
- App-level flow orchestration: `tests/test_run_application.py`, `tests/test_civil_war_phase.py`.

### Rendering / view-model tests
- Terminal rendering contracts and helpers: `tests/test_terminal_renderer.py`, `tests/test_view_models.py`.

### Simulation / evolution tests
- Population and tournament machinery: `tests/test_population.py`, `tests/test_tournament.py`, `tests/test_evolution.py`, `tests/test_progression.py`, `tests/test_lineage_rules.py`.

### Successor + heir-pressure analysis tests
- Analysis helpers and successor framing: `tests/test_analysis.py`, `tests/test_successor_analysis.py`.

### Web-slice state tests
- End-to-end web decision state and API payload validation: `tests/test_web_slice.py`.

## 2) Biggest current gaps

1. **Reusable test data builders were sparse**, causing repeated ad-hoc agent/genome setup.
2. **Seeded integration slices were underrepresented** as explicit architecture (especially floor progression -> successor -> civil-war transition path checks).
3. **Regression checks were mostly fine-grained asserts** instead of structured state contract assertions at key moments.
4. **Invariant tests existed implicitly** across files, but had limited explicit coverage for shared assumptions (seed determinism, offer-count validity, state shape sanity).
5. **Testing architecture guidance was implicit**, making future growth prone to test sprawl.

## 3) Tailored testing pyramid

- **Base (many): deterministic unit tests** for core rules, state transforms, scoring, powerup/genome logic.
- **Middle (moderate): seeded integration slices** for representative run segments (single-floor progression, successor choice, phase transition).
- **Top (few): regression contract tests** for high-value serialized state snapshots (web/session boundary state, completion contract).
- **Cross-cutting invariants (small but important):** deterministic behavior under seed, valid offer counts, state shape constraints.

This balances confidence and speed: most tests stay local and deterministic, while a smaller number validate orchestration contracts.

## 4) Recommended folder organization (incremental)

- Keep existing files stable for now to avoid churn.
- Add new architecture-oriented tests in dedicated folders:
  - `tests/support/` — shared builders/fixtures/helpers.
  - `tests/integration/` — seeded run slices.
  - `tests/regression/` — structured state contract checks.
  - `tests/invariants/` — property/invariant style checks without external dependencies.

Over time, older files can be gradually migrated as they are touched.

## 5) What to test where

- **Deterministic unit tests**
  - `core/` mechanics and pure data transformations.
  - deterministic behavior of helper analyzers.
- **Seeded integration tests**
  - one-floor featured flow to floor summary.
  - successor-selection flow.
  - ecosystem -> civil-war transition.
- **Regression/golden tests**
  - structured key-state snapshots at floor-summary and completion moments.
  - avoid giant opaque dumps; assert meaningful contracts only.
- **Invariant tests**
  - same seed => same critical digest.
  - offer generators return exact requested counts.
  - successor and floor-summary state shapes remain valid.

## 6) Reusable test helpers introduced

- Agent builder (`build_agent`) for concise, deterministic agents.
- Genome builder (`build_genome`) using compact table-bit notation.
- Featured prompt builder (`build_featured_prompt`) for typed interaction tests.
- Successor candidate builder (`build_successor_candidates`) for heir/succession tests.
- Floor summary builder (`build_floor_summary_state`) with heir-pressure mapping included.
- Session-driving helpers for common seeded flows (`play_until_floor_summary`, `advance_through_transition_and_complete`).

## Contributor guidance

When adding tests:
1. Start with the smallest deterministic layer possible.
2. Use `tests/support` builders before open-coding dataclass setup.
3. Add/extend seeded integration slices for new orchestration behavior.
4. Add one regression-style structured contract assert for important state interfaces.
5. Add invariant checks when introducing new randomization or state schemas.
