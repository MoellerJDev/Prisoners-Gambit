from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.dynasty import DynastyState
from prisoners_gambit.core.powerups import RoundContext
from prisoners_gambit.systems.floor_events import (
    FLOOR_EVENTS,
    ActiveFloorEvent,
    apply_match_event_bonus,
    apply_referendum_event_bonus,
    choose_floor_event_response,
    generate_floor_event,
    preferred_round_move,
    preferred_vote,
    response_commitment_modifier,
)


def _active_event(template_key: str, response_index: int) -> ActiveFloorEvent:
    template = next(template for template in FLOOR_EVENTS if template.key == template_key)
    return choose_floor_event_response(
        ActiveFloorEvent(floor_number=1, phase="ecosystem", template=template),
        response_index=response_index,
    )


def test_floor_event_response_match_bonus_shapes_the_whole_floor() -> None:
    active_event = _active_event("public_unrest", response_index=1)
    context = RoundContext(
        round_index=0,
        total_rounds=1,
        my_history=[],
        opp_history=[],
        planned_move=DEFECT,
        opp_planned_move=COOPERATE,
    )

    _, player_bonus = apply_match_event_bonus(
        active_event,
        owner_is_player=True,
        my_move=DEFECT,
        opp_move=COOPERATE,
        context=context,
        my_points=0,
    )
    _, rival_bonus = apply_match_event_bonus(
        active_event,
        owner_is_player=False,
        my_move=DEFECT,
        opp_move=COOPERATE,
        context=context,
        my_points=0,
    )

    assert player_bonus == rival_bonus
    assert player_bonus > 0


def test_floor_event_response_referendum_bonus_shapes_the_whole_floor() -> None:
    active_event = _active_event("public_unrest", response_index=1)

    _, player_bonus = apply_referendum_event_bonus(
        active_event,
        owner_is_player=True,
        my_vote=DEFECT,
        cooperation_prevailed=False,
        current_reward=0,
    )
    _, rival_bonus = apply_referendum_event_bonus(
        active_event,
        owner_is_player=False,
        my_vote=DEFECT,
        cooperation_prevailed=False,
        current_reward=0,
    )

    assert player_bonus == rival_bonus
    assert player_bonus > 0


def test_floor_event_response_commitment_penalizes_playing_against_declared_line() -> None:
    active_event = _active_event("trade_summit", response_index=0)

    aligned = response_commitment_modifier(
        active_event,
        round_history=[COOPERATE],
        final_vote=COOPERATE,
    )
    misaligned = response_commitment_modifier(
        active_event,
        round_history=[DEFECT],
        final_vote=DEFECT,
    )

    assert aligned.legitimacy_delta == 0
    assert aligned.cohesion_delta == 0
    assert misaligned.legitimacy_delta == -2
    assert misaligned.cohesion_delta == -1


def test_floor_event_catalog_expanded_and_keeps_three_response_tradeoffs() -> None:
    assert len(FLOOR_EVENTS) == 8
    assert {template.key for template in FLOOR_EVENTS} >= {"embargo_shock", "oath_tribunal"}
    assert all(len(template.responses) == 3 for template in FLOOR_EVENTS)


def test_stable_line_streak_biases_late_floor_events_toward_counter_pressure() -> None:
    class CapturingRng:
        def __init__(self) -> None:
            self.weights: dict[str, float] = {}

        def choices(self, templates, weights, k=1):
            self.weights = {template.key: weight for template, weight in zip(templates, weights, strict=True)}
            return [templates[0]]

    baseline_rng = CapturingRng()
    pressure_rng = CapturingRng()
    state = DynastyState()

    generate_floor_event(
        baseline_rng,
        floor_number=5,
        phase="ecosystem",
        dynasty_state=state,
        previous_event_key=None,
        stable_line_streak=0,
    )
    generate_floor_event(
        pressure_rng,
        floor_number=5,
        phase="ecosystem",
        dynasty_state=state,
        previous_event_key=None,
        stable_line_streak=4,
    )

    assert pressure_rng.weights["intelligence_leak"] > baseline_rng.weights["intelligence_leak"]
    assert pressure_rng.weights["border_raid"] > baseline_rng.weights["border_raid"]
    assert pressure_rng.weights["embargo_shock"] > baseline_rng.weights["embargo_shock"]
    assert pressure_rng.weights["oath_tribunal"] > baseline_rng.weights["oath_tribunal"]
    assert pressure_rng.weights["trade_summit"] == baseline_rng.weights["trade_summit"]


def test_preferred_round_and_vote_helpers_reflect_selected_response() -> None:
    stable_event = _active_event("trade_summit", response_index=0)
    aggressive_event = _active_event("oath_tribunal", response_index=1)

    assert preferred_round_move(None) is None
    assert preferred_vote(None) is None
    assert preferred_round_move(stable_event) == COOPERATE
    assert preferred_vote(stable_event) == COOPERATE
    assert preferred_round_move(aggressive_event) == DEFECT
    assert preferred_vote(aggressive_event) == DEFECT
