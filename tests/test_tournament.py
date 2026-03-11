import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import (
    GoldenHandshake,
    TrustDividend,
    UnityTicket,
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

    def show_floor_roster(self, floor_number, roster_entries):
        self.rosters += 1

    def choose_round_action(self, prompt):
        self.round_prompts += 1
        return prompt.suggested_move

    def show_round_result(self, result):
        self.round_results += 1

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