import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import (
    OpeningGambit,
    CounterIntel,
    CoerciveControl,
    ComplianceDividend,
    DirectivePriority,
    GoldenHandshake,
    MoveDirective,
    Powerup,
    LastLaugh,
    TrustDividend,
    UnityTicket,
    BlocPolitics,
)
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.progression import FloorConfig
from prisoners_gambit.systems.tournament import TournamentEngine


class StubRenderer:
    def __init__(self) -> None:
        self.last_referendum = None
        self.round_prompts = 0
        self.round_results = 0
        self.floor_votes = 0
        self.rosters = 0
        self.last_round_result = None
        self.prompts = []

    def show_floor_roster(self, floor_number, roster_entries):
        self.rosters += 1

    def choose_round_action(self, prompt):
        self.round_prompts += 1
        self.prompts.append(prompt)
        return prompt.suggested_move

    def show_round_result(self, result):
        self.round_results += 1
        self.last_round_result = result

    def choose_floor_vote(self, prompt):
        self.floor_votes += 1
        return prompt.suggested_vote

    def show_referendum_result(self, result):
        self.last_referendum = result

    def show_run_header(self, seed):
        pass

    def show_floor_summary(self, floor_number, ranked):
        pass

    def choose_powerup(self, offers):
        return offers[0]

    def choose_genome_edit(self, offers, current_summary):
        return offers[0]

    def show_genome_edit_applied(self, edit, new_summary):
        pass

    def choose_successor(self, successors):
        return successors[0]

    def show_successor_selected(self, successor):
        pass

    def show_elimination(self, floor_number):
        pass

    def show_victory(self, floor_number, player):
        pass


class StubInteractionController:
    def __init__(self) -> None:
        self.latest_round_result = None
        self.floor_vote_result = None
        self.floor_vote_prompts = 0

    def set_floor_roster(self, floor_number, roster_entries):
        pass

    def can_auto_resolve_featured_round(self):
        return False

    def choose_round_move(self, state):
        return state.prompt.suggested_move

    def set_latest_round_result(self, result):
        self.latest_round_result = result

    def reset_featured_match_autopilot(self):
        pass

    def choose_floor_vote(self, state):
        self.floor_vote_prompts += 1
        return state.prompt.suggested_vote

    def set_floor_vote_result(self, result):
        self.floor_vote_result = result


def static_agent(name: str, move: int, *, is_player: bool = False, lineage_id: int | None = None) -> Agent:
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
    return Agent(name=name, genome=genome, is_player=is_player, lineage_id=lineage_id)




def patterned_agent(
    name: str,
    *,
    first_move: int,
    cc: int,
    cd: int,
    dc: int,
    dd: int,
    is_player: bool = False,
    lineage_id: int | None = None,
) -> Agent:
    genome = StrategyGenome(
        first_move=first_move,
        response_table={
            (COOPERATE, COOPERATE): cc,
            (COOPERATE, DEFECT): cd,
            (DEFECT, COOPERATE): dc,
            (DEFECT, DEFECT): dd,
        },
        noise=0.0,
    )
    return Agent(name=name, genome=genome, is_player=is_player, lineage_id=lineage_id)


def make_floor_config(
    *,
    floor_number: int = 1,
    rounds_per_match: int = 2,
    ai_powerup_chance: float = 0.25,
    featured_matches: int = 1,
    referendum_reward: int = 3,
    label: str = "Opening Tables",
) -> FloorConfig:
    return FloorConfig(
        floor_number=floor_number,
        rounds_per_match=rounds_per_match,
        ai_powerup_chance=ai_powerup_chance,
        featured_matches=featured_matches,
        referendum_reward=referendum_reward,
        label=label,
    )


def test_play_match_scores_are_accumulated_correctly() -> None:
    cooperator = static_agent("Cooperator", COOPERATE)
    defector = static_agent("Defector", DEFECT)

    engine = TournamentEngine(base_rounds_per_match=3, rng=random.Random(1))
    result = engine.play_match(cooperator, defector, rounds_per_match=3)

    assert result.left_score == 0
    assert result.right_score == 3


def test_play_match_uses_base_rounds_when_rounds_override_not_provided() -> None:
    cooperator = static_agent("Cooperator", COOPERATE)
    defector = static_agent("Defector", DEFECT)

    engine = TournamentEngine(base_rounds_per_match=4, rng=random.Random(1))
    result = engine.play_match(cooperator, defector)

    assert result.left_score == 0
    assert result.right_score == 4


def test_play_match_applies_move_directives_before_scoring() -> None:
    attacker = static_agent("Attacker", DEFECT)
    defender = static_agent("Defender", DEFECT)
    attacker.powerups.append(GoldenHandshake())

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1))
    result = engine.play_match(attacker, defender, rounds_per_match=1)

    assert result.left_score == 1
    assert result.right_score == 1


def test_run_floor_ranks_population_by_score_then_wins() -> None:
    renderer = StubRenderer()
    agents = [
        Agent(
            name="You",
            genome=StrategyGenome(
                first_move=COOPERATE,
                response_table={
                    (COOPERATE, COOPERATE): COOPERATE,
                    (COOPERATE, DEFECT): COOPERATE,
                    (DEFECT, COOPERATE): COOPERATE,
                    (DEFECT, DEFECT): COOPERATE,
                },
                noise=0.0,
            ),
            is_player=True,
            lineage_id=1,
        ),
        static_agent("Cooperator B", COOPERATE),
        static_agent("Defector", DEFECT),
    ]

    engine = TournamentEngine(base_rounds_per_match=2, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=2, featured_matches=1)

    ranked = engine.run_floor(
        population=agents,
        floor_number=1,
        floor_config=floor_config,
    )

    assert len(ranked) == 3
    assert ranked[0].score >= ranked[1].score >= ranked[2].score


def test_run_floor_shows_roster_when_player_exists() -> None:
    renderer = StubRenderer()
    agents = [
        static_agent("You", COOPERATE, is_player=True, lineage_id=1),
        static_agent("A", COOPERATE),
        static_agent("B", DEFECT),
    ]

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=1)

    engine.run_floor(agents, floor_number=1, floor_config=floor_config)

    assert renderer.rosters == 1


def test_featured_matches_prompt_player_for_each_round() -> None:
    renderer = StubRenderer()
    agents = [
        static_agent("You", COOPERATE, is_player=True, lineage_id=1),
        static_agent("A", COOPERATE),
        static_agent("B", DEFECT),
    ]

    engine = TournamentEngine(base_rounds_per_match=3, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=3, featured_matches=1)

    engine.run_floor(agents, floor_number=1, floor_config=floor_config)

    assert renderer.round_prompts == 3
    assert renderer.round_results == 3


def test_referendum_rewards_cooperators_when_they_reach_majority() -> None:
    renderer = StubRenderer()
    you = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    you.powerups.append(TrustDividend())

    ally = static_agent("Ally", COOPERATE)
    dissenter = static_agent("Dissenter", DEFECT)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=1, referendum_reward=3)

    ranked = engine.run_floor([you, ally, dissenter], floor_number=1, floor_config=floor_config)

    final_you = next(agent for agent in ranked if agent.is_player)
    assert final_you.score >= 3
    assert renderer.last_referendum is not None
    assert renderer.last_referendum.cooperation_prevailed is True


def test_referendum_gives_no_reward_when_defection_has_majority() -> None:
    renderer = StubRenderer()
    you = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    defector_a = static_agent("A", DEFECT)
    defector_b = static_agent("B", DEFECT)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=1, referendum_reward=4)

    ranked = engine.run_floor([you, defector_a, defector_b], floor_number=1, floor_config=floor_config)

    final_you = next(agent for agent in ranked if agent.is_player)
    assert renderer.last_referendum is not None
    assert renderer.last_referendum.cooperation_prevailed is False
    assert renderer.last_referendum.player_reward == 0
    assert final_you.score >= 0


def test_unity_ticket_changes_player_referendum_outcome() -> None:
    renderer = StubRenderer()
    you = static_agent("You", DEFECT, is_player=True, lineage_id=1)
    you.powerups.append(UnityTicket())

    ally = static_agent("Ally", COOPERATE)
    dissenter = static_agent("Dissenter", DEFECT)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=1, referendum_reward=3)

    engine.run_floor([you, ally, dissenter], floor_number=1, floor_config=floor_config)

    assert renderer.last_referendum is not None
    assert renderer.last_referendum.player_vote == COOPERATE


def test_run_floor_resets_scores_and_wins_before_playing() -> None:
    renderer = StubRenderer()
    a = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    b = static_agent("B", DEFECT)
    c = static_agent("C", COOPERATE)

    a.score = 999
    a.wins = 999
    b.score = 999
    b.wins = 999
    c.score = 999
    c.wins = 999

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=1)

    ranked = engine.run_floor([a, b, c], floor_number=1, floor_config=floor_config)

    for agent in ranked:
        assert agent.score < 999
        assert agent.wins < 999


def test_featured_round_breakdown_no_directives_has_no_score_modifiers() -> None:
    renderer = StubRenderer()
    you = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    opp = static_agent("Opp", COOPERATE)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(2), renderer=renderer)
    engine.play_featured_player_match(
        player=you,
        opponent=opp,
        rounds_per_match=1,
        floor_number=1,
        roster_entries=[],
        masked_opponent_label="Unknown Opponent 1",
    )

    assert renderer.last_round_result is not None
    assert renderer.last_round_result.breakdown.player_directives.reason == "base"
    assert renderer.last_round_result.breakdown.opponent_directives.reason == "base"
    assert renderer.last_round_result.breakdown.score_adjustments == []


def test_featured_round_breakdown_tracks_single_winning_directive() -> None:
    renderer = StubRenderer()
    you = static_agent("You", DEFECT, is_player=True, lineage_id=1)
    opp = static_agent("Opp", COOPERATE)
    opp.powerups.append(CounterIntel())

    engine = TournamentEngine(base_rounds_per_match=2, rng=random.Random(1), renderer=renderer)
    engine.play_featured_player_match(
        player=you,
        opponent=opp,
        rounds_per_match=2,
        floor_number=1,
        roster_entries=[],
        masked_opponent_label="Unknown Opponent 1",
    )

    assert renderer.last_round_result is not None
    assert renderer.last_round_result.breakdown.player_directives.reason == "Counter-Intel@200"
    assert renderer.last_round_result.player_move == COOPERATE


class ForceCooperate(Powerup):
    name = "Force C"

    def self_move_directives(self, *, owner, opponent, context):
        return [MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source=self.name)]


class ForceDefect(Powerup):
    name = "Force D"

    def self_move_directives(self, *, owner, opponent, context):
        return [MoveDirective(move=DEFECT, priority=DirectivePriority.FORCE, source=self.name)]


class AlwaysBonus(Powerup):
    def __init__(self, name: str, bonus: int) -> None:
        self.name = name
        self.bonus = bonus

    def on_score(self, *, owner, opponent, my_move, opp_move, my_points, opp_points, context):
        return my_points + self.bonus, opp_points


def test_featured_round_breakdown_conflicting_equal_priority_directives_defect() -> None:
    renderer = StubRenderer()
    you = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    you.powerups.extend([ForceCooperate(), ForceDefect()])
    opp = static_agent("Opp", COOPERATE)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)
    engine.play_featured_player_match(
        player=you,
        opponent=opp,
        rounds_per_match=1,
        floor_number=1,
        roster_entries=[],
        masked_opponent_label="Unknown Opponent 1",
    )

    assert renderer.last_round_result is not None
    assert renderer.last_round_result.player_reason == "conflict@200->D"
    assert renderer.last_round_result.player_move == DEFECT


def test_featured_round_breakdown_tracks_multiple_score_powerups() -> None:
    renderer = StubRenderer()
    you = static_agent("You", DEFECT, is_player=True, lineage_id=1)
    you.powerups.append(AlwaysBonus(name="Player Bonus", bonus=2))
    opp = static_agent("Opp", COOPERATE)
    opp.powerups.append(AlwaysBonus(name="Opponent Bonus", bonus=1))

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)
    engine.play_featured_player_match(
        player=you,
        opponent=opp,
        rounds_per_match=1,
        floor_number=1,
        roster_entries=[],
        masked_opponent_label="Unknown Opponent 1",
    )

    assert renderer.last_round_result is not None
    adjustments = renderer.last_round_result.breakdown.score_adjustments
    assert len(adjustments) == 2
    assert adjustments[0].source == "Player Bonus"
    assert adjustments[0].player_delta == 2
    assert adjustments[1].source == "Opponent Bonus"
    assert adjustments[1].opponent_delta == 1


def test_featured_round_result_reaches_interaction_controller_without_renderer() -> None:
    controller = StubInteractionController()
    you = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    opp = static_agent("Opp", DEFECT)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(2), interaction_controller=controller)
    engine.play_featured_player_match(
        player=you,
        opponent=opp,
        rounds_per_match=1,
        floor_number=1,
        roster_entries=[],
        masked_opponent_label="Unknown Opponent 1",
    )

    assert controller.latest_round_result is not None
    assert controller.latest_round_result.breakdown.final_player_points >= 0


def test_referendum_uses_interaction_controller_without_renderer() -> None:
    controller = StubInteractionController()
    agents = [
        static_agent("You", COOPERATE, is_player=True, lineage_id=1),
        static_agent("A", COOPERATE),
        static_agent("B", DEFECT),
    ]

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), interaction_controller=controller)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=0)

    engine.run_floor(agents, floor_number=1, floor_config=floor_config)

    assert controller.floor_vote_prompts == 1
    assert controller.floor_vote_result is not None

def test_civil_war_phase_disables_referendum_flow() -> None:
    renderer = StubRenderer()
    player = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    rival = static_agent("Rival", DEFECT, lineage_id=1)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(2), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=0, referendum_reward=99)

    engine.run_floor([player, rival], floor_number=2, floor_config=floor_config, phase="civil_war")

    assert renderer.last_referendum is None
    assert renderer.floor_votes == 0


def test_civil_war_grants_rivalry_bonus_for_same_lane_winners() -> None:
    enforcer = static_agent("Enforcer", DEFECT, lineage_id=1)
    enforcer.powerups.append(OpeningGambit(bonus=1))

    rival = static_agent("Rival", DEFECT, lineage_id=1)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(3))
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=0)

    ranked = engine.run_floor([enforcer, rival], floor_number=2, floor_config=floor_config, phase="civil_war")

    assert ranked[0].name == "Enforcer"
    assert ranked[0].score >= 2


def test_featured_prompt_floor_log_accumulates_round_to_round_within_match() -> None:
    renderer = StubRenderer()
    you = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    opponent = static_agent("A", DEFECT)
    opponent.public_profile = "Doctrinal hardliner"
    opponent.powerups.append(CounterIntel())
    agents = [you, opponent, static_agent("B", COOPERATE)]

    engine = TournamentEngine(base_rounds_per_match=2, rng=random.Random(1), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=2, featured_matches=1)

    engine.run_floor(agents, floor_number=1, floor_config=floor_config)

    assert len(renderer.prompts) == 2
    first, second = renderer.prompts
    assert first.clue_channels
    assert any("Profile signal" in clue for clue in first.clue_channels)
    assert any("Known powerups" in clue for clue in first.clue_channels)
    assert first.floor_clue_log == []
    assert second.floor_clue_log
    assert second.inference_focus is not None


def test_featured_prompt_floor_log_carries_across_featured_matches_on_same_floor() -> None:
    renderer = StubRenderer()
    you = static_agent("You", COOPERATE, is_player=True, lineage_id=1)
    opponent_a = static_agent("A", DEFECT)
    opponent_b = static_agent("B", DEFECT)
    opponent_c = static_agent("C", COOPERATE)

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(2), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=2)

    engine.run_floor([you, opponent_a, opponent_b, opponent_c], floor_number=1, floor_config=floor_config)

    # Two featured matches, one round each -> two prompts.
    assert len(renderer.prompts) == 2
    first_match_prompt, second_match_prompt = renderer.prompts
    assert first_match_prompt.round_index == 0
    assert first_match_prompt.floor_clue_log == []
    assert second_match_prompt.round_index == 0
    assert second_match_prompt.floor_clue_log

    floor_clues = engine.consume_last_floor_clue_log()
    assert floor_clues
    assert any("Floor learning" in line for line in floor_clues)



def test_live_match_flow_generates_forced_cooperation_event_for_control_payoffs() -> None:
    controller = patterned_agent(
        "Controller",
        first_move=DEFECT,
        cc=DEFECT,
        cd=DEFECT,
        dc=DEFECT,
        dd=DEFECT,
    )
    rival = patterned_agent(
        "Rival",
        first_move=COOPERATE,
        cc=DEFECT,
        cd=DEFECT,
        dc=DEFECT,
        dd=DEFECT,
    )
    controller.powerups.extend([CoerciveControl(), ComplianceDividend(bonus=1)])

    engine = TournamentEngine(base_rounds_per_match=2, rng=random.Random(7))
    result = engine.play_match(controller, rival, rounds_per_match=2)

    assert result.left_score == 7
    assert result.right_score == 0


def test_live_match_flow_generates_locked_mutual_coop_event_for_trust_payoff() -> None:
    anchor = static_agent("Anchor", DEFECT)
    rival = static_agent("Rival", DEFECT)
    anchor.powerups.extend([GoldenHandshake(), TrustDividend()])

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(3))
    result = engine.play_match(anchor, rival, rounds_per_match=1)

    assert result.left_score == 3
    assert result.right_score == 1


def test_featured_live_flow_triggers_final_round_betrayal_cashout() -> None:
    renderer = StubRenderer()
    closer = static_agent("Closer", COOPERATE, is_player=True, lineage_id=1)
    target = static_agent("Target", COOPERATE)
    closer.powerups.append(LastLaugh(bonus=2))

    engine = TournamentEngine(base_rounds_per_match=2, rng=random.Random(11), renderer=renderer)
    player_score, opponent_score = engine.play_featured_player_match(
        player=closer,
        opponent=target,
        rounds_per_match=2,
        floor_number=1,
        roster_entries=[],
        masked_opponent_label="Unknown",
        floor_clue_log=[],
    )

    assert player_score == 4
    assert opponent_score == 1


def test_live_referendum_flow_generates_controlled_vote_bloc_combo() -> None:
    renderer = StubRenderer()
    player = static_agent("You", DEFECT, is_player=True, lineage_id=1)
    ally = static_agent("Ally", COOPERATE)
    player.powerups.extend([UnityTicket(), BlocPolitics(bonus=2)])

    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(5), renderer=renderer)
    floor_config = make_floor_config(rounds_per_match=1, featured_matches=0, referendum_reward=3)

    engine.run_floor([player, ally], floor_number=1, floor_config=floor_config)

    assert renderer.last_referendum is not None
    assert renderer.last_referendum.player_vote == COOPERATE
    assert renderer.last_referendum.player_reward == 7
