import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.offer_views import to_powerup_offer_view
from prisoners_gambit.core.powerups import (
    ALL_POWERUP_TYPES,
    BlocPolitics,
    CoerciveControl,
    ComplianceDividend,
    ConcordatProtocol,
    CounterIntel,
    derive_referendum_combo_events,
    derive_round_combo_events,
    DirectivePriority,
    GoldenHandshake,
    LastLaugh,
    MercyShield,
    MoveDirective,
    OpeningGambit,
    PanicButton,
    ReferendumContext,
    REFERENDUM_EVENT_CONTROLLED_VOTE,
    REFERENDUM_EVENT_COOP_BLOC_WIN,
    ROUND_EVENT_BETRAYAL_INTO_COOP,
    ROUND_EVENT_FINAL_ROUND_BETRAYAL,
    ROUND_EVENT_FORCED_OPPONENT_COOP,
    ROUND_EVENT_LOCKED_MUTUAL_COOP,
    ROUND_EVENT_MUTUAL_DEFECTION_SPIRAL,
    ROUND_EVENT_RETALIATION_TRIGGERED,
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
        combo_events=(ROUND_EVENT_RETALIATION_TRIGGERED,),
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
        combo_events=(ROUND_EVENT_BETRAYAL_INTO_COOP, ROUND_EVENT_FINAL_ROUND_BETRAYAL),
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

    assert my_points == 4
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

    context = ReferendumContext(floor_number=2, total_agents=10, current_floor_score=12, combo_events=(REFERENDUM_EVENT_COOP_BLOC_WIN,))
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

def test_last_laugh_adds_final_round_bonus_when_opponent_cooperates() -> None:
    owner = static_agent("Closer", DEFECT)
    opponent = static_agent("Opponent", COOPERATE)
    perk = LastLaugh(bonus=2)

    context = RoundContext(
        round_index=2,
        total_rounds=3,
        my_history=[COOPERATE, COOPERATE],
        opp_history=[COOPERATE, COOPERATE],
        planned_move=DEFECT,
        opp_planned_move=COOPERATE,
        combo_events=(ROUND_EVENT_FINAL_ROUND_BETRAYAL,),
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


def test_compliance_dividend_rewards_recovered_control_after_betrayal() -> None:
    owner = static_agent("Owner", DEFECT)
    opponent = static_agent("Opponent", COOPERATE)
    perk = ComplianceDividend(bonus=2)

    context = RoundContext(
        round_index=2,
        total_rounds=3,
        my_history=[COOPERATE, DEFECT],
        opp_history=[COOPERATE, DEFECT],
        planned_move=DEFECT,
        opp_planned_move=COOPERATE,
        combo_events=(ROUND_EVENT_BETRAYAL_INTO_COOP, ROUND_EVENT_RETALIATION_TRIGGERED),
    )

    my_points, _ = perk.on_score(
        owner=owner,
        opponent=opponent,
        my_move=DEFECT,
        opp_move=COOPERATE,
        my_points=1,
        opp_points=0,
        context=context,
    )

    assert my_points == 4


def test_powerups_expose_synergy_keywords_for_offer_reasoning() -> None:
    for powerup_type in ALL_POWERUP_TYPES:
        keywords = powerup_type().keywords
        assert keywords
        assert all(keyword == keyword.strip() and keyword == keyword.lower() for keyword in keywords)

    assert "creates_force" in CoerciveControl().keywords
    assert "rewards_force" in ComplianceDividend().keywords
    assert "referendum_control" in UnityTicket().keywords


def test_control_lane_anchor_and_payoff_stack() -> None:
    owner = static_agent("Controller", DEFECT)
    opponent = static_agent("Target", COOPERATE)
    owner.powerups.extend([CoerciveControl(), ComplianceDividend(bonus=2)])

    context = RoundContext(
        round_index=1,
        total_rounds=3,
        my_history=[COOPERATE],
        opp_history=[DEFECT],
        planned_move=DEFECT,
        opp_planned_move=COOPERATE,
        combo_events=(ROUND_EVENT_BETRAYAL_INTO_COOP, ROUND_EVENT_FORCED_OPPONENT_COOP, ROUND_EVENT_RETALIATION_TRIGGERED),
    )

    my_points, opp_points = owner.powerups[1].on_score(
        owner=owner,
        opponent=opponent,
        my_move=DEFECT,
        opp_move=COOPERATE,
        my_points=1,
        opp_points=0,
        context=context,
    )

    assert my_points == 5
    assert opp_points == 0


def test_trust_lane_streak_pays_more_than_single_proc() -> None:
    owner = static_agent("Coalition", COOPERATE)
    opponent = static_agent("Ally", COOPERATE)
    perk = TrustDividend()

    context = RoundContext(
        round_index=2,
        total_rounds=4,
        my_history=[COOPERATE, COOPERATE],
        opp_history=[COOPERATE, COOPERATE],
        planned_move=COOPERATE,
        opp_planned_move=COOPERATE,
        combo_events=(ROUND_EVENT_LOCKED_MUTUAL_COOP,),
    )

    my_points, _ = perk.on_score(
        owner=owner,
        opponent=opponent,
        my_move=COOPERATE,
        opp_move=COOPERATE,
        my_points=1,
        opp_points=1,
        context=context,
    )

    assert my_points == 3


def test_referendum_lane_anchor_and_amplifier_stack() -> None:
    owner = static_agent("Whip", COOPERATE)
    owner.powerups.extend([UnityTicket(), TrustDividend(), BlocPolitics(bonus=2)])
    context = ReferendumContext(floor_number=3, total_agents=10, current_floor_score=12, combo_events=(REFERENDUM_EVENT_CONTROLLED_VOTE, REFERENDUM_EVENT_COOP_BLOC_WIN))

    reward = 2
    for perk in owner.powerups:
        reward = perk.on_referendum_reward(
            owner=owner,
            my_vote=COOPERATE,
            cooperation_prevailed=True,
            current_reward=reward,
            context=context,
        )

    assert reward == 6


def test_retaliation_spiral_anchor_payoff_and_amplifier_stack() -> None:
    owner = static_agent("Spiral", DEFECT)
    opponent = static_agent("Rival", DEFECT)
    owner.powerups.extend([SpiteEngine(), MercyShield(), PanicButton()])

    context = RoundContext(
        round_index=2,
        total_rounds=4,
        my_history=[COOPERATE, DEFECT],
        opp_history=[DEFECT, DEFECT],
        planned_move=DEFECT,
        opp_planned_move=DEFECT,
        combo_events=(ROUND_EVENT_RETALIATION_TRIGGERED, ROUND_EVENT_MUTUAL_DEFECTION_SPIRAL),
    )

    my_points, opp_points = 1, 1
    for perk in owner.powerups:
        my_points, opp_points = perk.on_score(
            owner=owner,
            opponent=opponent,
            my_move=DEFECT,
            opp_move=DEFECT,
            my_points=my_points,
            opp_points=opp_points,
            context=context,
        )

    assert my_points == 5
    assert opp_points == 0


def test_opening_betrayal_bridges_into_last_laugh_cashout() -> None:
    owner = static_agent("Closer", DEFECT)
    opponent = static_agent("Victim", COOPERATE)
    owner.powerups.extend([OpeningGambit(), LastLaugh(bonus=2)])

    context = RoundContext(
        round_index=2,
        total_rounds=3,
        my_history=[DEFECT, COOPERATE],
        opp_history=[COOPERATE, COOPERATE],
        planned_move=DEFECT,
        opp_planned_move=COOPERATE,
        combo_events=(ROUND_EVENT_FINAL_ROUND_BETRAYAL,),
    )

    my_points, _ = owner.powerups[1].on_score(
        owner=owner,
        opponent=opponent,
        my_move=DEFECT,
        opp_move=COOPERATE,
        my_points=1,
        opp_points=0,
        context=context,
    )

    assert my_points == 4


def test_offer_view_exposes_powerup_role_in_branch_identity_and_tags() -> None:
    offer = to_powerup_offer_view(CoerciveControl(), relevance_hint="Build fit")

    assert offer.branch_identity is not None and "(anchor)" in offer.branch_identity
    assert offer.tags is not None and "anchor" in offer.tags and "creates_force" in offer.tags
    assert offer.trigger is not None and offer.trigger.startswith("Trigger:")
    assert offer.effect is not None and offer.effect.startswith("Effect:")
    assert offer.role == "Role: anchor."
    assert offer.relevance_hint == "Build fit"


def test_round_combo_events_detect_forced_and_final_betrayal() -> None:
    context = RoundContext(
        round_index=2,
        total_rounds=3,
        my_history=[DEFECT, COOPERATE],
        opp_history=[COOPERATE, DEFECT],
        planned_move=DEFECT,
        opp_planned_move=DEFECT,
    )
    events = derive_round_combo_events(
        context=context,
        my_move=DEFECT,
        opp_move=COOPERATE,
        my_directives=[],
        opp_directives=[MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source="x")],
    )

    assert ROUND_EVENT_FORCED_OPPONENT_COOP in events
    assert ROUND_EVENT_BETRAYAL_INTO_COOP in events
    assert ROUND_EVENT_FINAL_ROUND_BETRAYAL in events


def test_referendum_combo_events_detect_controlled_bloc_win() -> None:
    events = derive_referendum_combo_events(
        base_vote=DEFECT,
        final_vote=COOPERATE,
        directives=[MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source="Unity Ticket")],
        cooperation_prevailed=True,
    )

    assert REFERENDUM_EVENT_CONTROLLED_VOTE in events
    assert REFERENDUM_EVENT_COOP_BLOC_WIN in events


def test_crown_powerup_offer_view_exposes_crown_hint() -> None:
    offer = to_powerup_offer_view(ConcordatProtocol(), relevance_hint="Power risk")

    assert offer.crown_hint == "Crown piece · dynasty-defining"
