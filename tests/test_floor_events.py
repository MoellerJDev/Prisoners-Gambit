from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.powerups import RoundContext
from prisoners_gambit.systems.floor_events import (
    FLOOR_EVENTS,
    ActiveFloorEvent,
    apply_match_event_bonus,
    apply_referendum_event_bonus,
    choose_floor_event_response,
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
