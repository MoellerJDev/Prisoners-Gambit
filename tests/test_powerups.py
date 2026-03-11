import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import (
    BlocPolitics,
    CoerciveControl,
    ComplianceDividend,
    CounterIntel,
    DirectivePriority,
    GoldenHandshake,
    LastLaugh,
    MercyShield,
    MoveDirective,
    OpeningGambit,
    PanicButton,
    ReferendumContext,
    RoundContext,
    SaboteurBloc,
    SpiteEngine,
    TrustDividend,
    UnityTicket,
    resolve_move,
)
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.tournament import TournamentEngine


def static_agent(name: str, move: int) -> Agent:
    genome = StrategyGenome(
        first_move=move,
        response_table={
            (COOPERATE, COOPERATE): move,
            (COOPERATE, DEFECT): move,
            (DEFECT, COOPERATE): move,
            (DEFECT, DEFECT): move,
        },
        noise=0.0,
    )
    return Agent(name=name, genome=genome)


def test_opening_gambit_adds_bonus() -> None:
    attacker = static_agent("Attacker", DEFECT)
    defender = static_agent("Defender", COOPERATE)
    attacker.powerups.append(OpeningGambit())

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1))
    result = engine.play_match(attacker, defender, rounds_per_match=1)

    assert result.left_score == 2
    assert result.right_score == 0


def test_last_laugh_forces_final_defect() -> None:
    agent = static_agent("Closer", COOPERATE)
    agent.powerups.append(LastLaugh())

    context = RoundContext(
        round_index=2,
        total_rounds=3,
        my_history=[COOPERATE, COOPERATE],
        opp_history=[COOPERATE, COOPERATE],
        planned_move=COOPERATE,
        opp_planned_move=COOPERATE,
    )

    directives = agent.powerups[0].self_move_directives(owner=agent, opponent=agent, context=context)
    resolved, _ = resolve_move(COOPERATE, directives)

    assert resolved == DEFECT


def test_last_laugh_does_not_trigger_before_final_round() -> None:
    agent = static_agent("Closer", COOPERATE)
    agent.powerups.append(LastLaugh())

    context = RoundContext(
        round_index=1,
        total_rounds=3,
        my_history=[COOPERATE],
        opp_history=[COOPERATE],
        planned_move=COOPERATE,
        opp_planned_move=COOPERATE,
    )

    directives = agent.powerups[0].self_move_directives(owner=agent, opponent=agent, context=context)
    resolved, reason = resolve_move(COOPERATE, directives)

    assert resolved == COOPERATE
    assert reason == "base"


def test_trust_dividend_rewards_mutual_cooperation() -> None:
    friendly = static_agent("Friendly", COOPERATE)
    ally = static_agent("Ally", COOPERATE)
    friendly.powerups.append(TrustDividend())

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1))
    result = engine.play_match(friendly, ally, rounds_per_match=1)

    assert result.left_score == 2
    assert result.right_score == 1


def test_spite_engine_rewards_retaliatory_defection() -> None:
    owner = static_agent("Owner", DEFECT)
    opponent = static_agent("Opponent", COOPERATE)
    owner.powerups.append(SpiteEngine(bonus=2))

    context = RoundContext(
        round_index=1,
        total_rounds=3,
        my_history=[COOPERATE],
        opp_history=[DEFECT],
        planned_move=DEFECT,
        opp_planned_move=COOPERATE,
    )

    my_points, opp_points = owner.powerups[0].on_score(
        owner=owner,
        opponent=opponent,
        my_move=DEFECT,
        opp_move=COOPERATE,
        my_points=1,
        opp_points=0,
        context=context,
    )

    assert my_points == 3
    assert opp_points == 0


def test_mercy_shield_zeroes_opponent_points_after_recent_betrayal() -> None:
    owner = static_agent("Owner", COOPERATE)
    opponent = static_agent("Opponent", DEFECT)
    owner.powerups.append(MercyShield())

    context = RoundContext(
        round_index=1,
        total_rounds=3,
        my_history=[COOPERATE],
        opp_history=[DEFECT],
        planned_move=COOPERATE,
        opp_planned_move=DEFECT,
    )

    my_points, opp_points = owner.powerups[0].on_score(
        owner=owner,
        opponent=opponent,
        my_move=COOPERATE,
        opp_move=DEFECT,
        my_points=0,
        opp_points=1,
        context=context,
    )

    assert my_points == 0
    assert opp_points == 0


def test_golden_handshake_forces_both_players_to_cooperate_on_round_one() -> None:
    owner = static_agent("Owner", DEFECT)
    opponent = static_agent("Opponent", DEFECT)
    perk = GoldenHandshake()

    context = RoundContext(
        round_index=0,
        total_rounds=3,
        my_history=[],
        opp_history=[],
        planned_move=DEFECT,
        opp_planned_move=DEFECT,
    )

    self_directives = perk.self_move_directives(owner=owner, opponent=opponent, context=context)
    opp_directives = perk.opponent_move_directives(owner=owner, opponent=opponent, context=context)

    self_resolved, _ = resolve_move(DEFECT, self_directives)
    opp_resolved, _ = resolve_move(DEFECT, opp_directives)

    assert self_resolved == COOPERATE
    assert opp_resolved == COOPERATE


def test_coercive_control_forces_opponent_to_repeat_cooperation_after_exploitation() -> None:
    owner = static_agent("Owner", DEFECT)
    opponent = static_agent("Opponent", COOPERATE)
    perk = CoerciveControl()

    context = RoundContext(
        round_index=1,
        total_rounds=3,
        my_history=[DEFECT],
        opp_history=[COOPERATE],
        planned_move=COOPERATE,
        opp_planned_move=DEFECT,
    )

    directives = perk.opponent_move_directives(owner=owner, opponent=opponent, context=context)
    resolved, _ = resolve_move(DEFECT, directives)

    assert resolved == COOPERATE


def test_counter_intel_forces_opponent_toward_cooperation_after_they_defected() -> None:
    owner = static_agent("Owner", COOPERATE)
    opponent = static_agent("Opponent", DEFECT)
    perk = CounterIntel()

    context = RoundContext(
        round_index=1,
        total_rounds=3,
        my_history=[COOPERATE],
        opp_history=[DEFECT],
        planned_move=COOPERATE,
        opp_planned_move=DEFECT,
    )

    directives = perk.opponent_move_directives(owner=owner, opponent=opponent, context=context)
    resolved, _ = resolve_move(DEFECT, directives)

    assert resolved == COOPERATE


def test_panic_button_locks_both_players_into_defection_after_mutual_defection() -> None:
    owner = static_agent("Owner", COOPERATE)
    opponent = static_agent("Opponent", COOPERATE)
    perk = PanicButton()

    context = RoundContext(
        round_index=1,
        total_rounds=3,
        my_history=[DEFECT],
        opp_history=[DEFECT],
        planned_move=COOPERATE,
        opp_planned_move=COOPERATE,
    )

    self_directives = perk.self_move_directives(owner=owner, opponent=opponent, context=context)
    opp_directives = perk.opponent_move_directives(owner=owner, opponent=opponent, context=context)

    self_resolved, _ = resolve_move(COOPERATE, self_directives)
    opp_resolved, _ = resolve_move(COOPERATE, opp_directives)

    assert self_resolved == DEFECT
    assert opp_resolved == DEFECT


def test_compliance_dividend_rewards_successful_exploitation() -> None:
    owner = static_agent("Owner", DEFECT)
    opponent = static_agent("Opponent", COOPERATE)
    perk = ComplianceDividend(bonus=2)

    context = RoundContext(
        round_index=0,
        total_rounds=1,
        my_history=[],
        opp_history=[],
        planned_move=DEFECT,
        opp_planned_move=COOPERATE,
    )

    my_points, opp_points = perk.on_score(
        owner=owner,
        opponent=opponent,
        my_move=DEFECT,
        opp_move=COOPERATE,
        my_points=1,
        opp_points=0,
        context=context,
    )

    assert my_points == 3
    assert opp_points == 0


def test_unity_ticket_forces_referendum_cooperation() -> None:
    agent = static_agent("Voter", DEFECT)
    agent.powerups.append(UnityTicket())

    context = ReferendumContext(floor_number=1, total_agents=8, current_floor_score=0)
    directives = agent.powerups[0].self_referendum_directives(owner=agent, context=context)
    resolved, _ = resolve_move(DEFECT, directives)

    assert resolved == COOPERATE


def test_saboteur_bloc_forces_referendum_defection() -> None:
    agent = static_agent("Voter", COOPERATE)
    agent.powerups.append(SaboteurBloc())

    context = ReferendumContext(floor_number=1, total_agents=8, current_floor_score=0)
    directives = agent.powerups[0].self_referendum_directives(owner=agent, context=context)
    resolved, _ = resolve_move(COOPERATE, directives)

    assert resolved == DEFECT


def test_bloc_politics_adds_bonus_when_cooperation_prevailed_and_owner_cooperated() -> None:
    agent = static_agent("Voter", COOPERATE)
    perk = BlocPolitics(bonus=3)

    context = ReferendumContext(floor_number=2, total_agents=10, current_floor_score=12)
    reward = perk.on_referendum_reward(
        owner=agent,
        my_vote=COOPERATE,
        cooperation_prevailed=True,
        current_reward=4,
        context=context,
    )

    assert reward == 7


def test_bloc_politics_does_not_add_bonus_when_owner_defected() -> None:
    agent = static_agent("Voter", DEFECT)
    perk = BlocPolitics(bonus=3)

    context = ReferendumContext(floor_number=2, total_agents=10, current_floor_score=12)
    reward = perk.on_referendum_reward(
        owner=agent,
        my_vote=DEFECT,
        cooperation_prevailed=True,
        current_reward=4,
        context=context,
    )

    assert reward == 4


def test_conflicting_directives_resolve_to_defect() -> None:
    directives = [
        MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source="A"),
        MoveDirective(move=DEFECT, priority=DirectivePriority.FORCE, source="B"),
    ]
    resolved, reason = resolve_move(COOPERATE, directives)

    assert resolved == DEFECT
    assert "conflict" in reason


def test_higher_priority_directive_beats_lower_priority_directive() -> None:
    directives = [
        MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source="Lower"),
        MoveDirective(move=DEFECT, priority=DirectivePriority.LOCK, source="Higher"),
    ]
    resolved, reason = resolve_move(COOPERATE, directives)

    assert resolved == DEFECT
    assert "Higher" in reason


def test_identical_highest_priority_directives_preserve_shared_move() -> None:
    directives = [
        MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source="A"),
        MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source="B"),
        MoveDirective(move=DEFECT, priority=DirectivePriority.OVERRIDE, source="Low"),
    ]
    resolved, reason = resolve_move(DEFECT, directives)

    assert resolved == COOPERATE
    assert "A" in reason or "B" in reason