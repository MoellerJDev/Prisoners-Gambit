import random, pytest
from types import SimpleNamespace

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import (
    MoveDirective,
    TrustDividend,
    DirectivePriority,
    resolve_move,
)
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.progression import ProgressionEngine
from prisoners_gambit.systems.tournament import TournamentEngine


def make_agent(name: str, move: int, *, is_player: bool = False) -> Agent:
    return Agent(
        name=name,
        genome=StrategyGenome(
            first_move=move,
            response_table={
                (COOPERATE, COOPERATE): move,
                (COOPERATE, DEFECT): move,
                (DEFECT, COOPERATE): move,
                (DEFECT, DEFECT): move,
            },
            noise=0.0,
        ),
        is_player=is_player,
        lineage_id=1 if is_player else None,
    )


def test_clone_preserves_parameterized_powerup_values() -> None:
    perk = TrustDividend(bonus=4)
    clone = perk.clone()

    assert clone is not perk
    assert clone.bonus == 4


def test_referendum_tie_counts_as_cooperation_prevailing() -> None:
    class StubRenderer:
        def __init__(self):
            self.last_referendum = None

        def show_floor_roster(self, floor_number, roster_entries): pass
        def choose_round_action(self, prompt): return prompt.suggested_move
        def show_round_result(self, result): pass
        def choose_floor_vote(self, prompt): return prompt.suggested_vote
        def show_referendum_result(self, result): self.last_referendum = result
        def show_run_header(self, seed): pass
        def show_floor_summary(self, floor_number, ranked): pass
        def choose_powerup(self, offers): return offers[0]
        def choose_genome_edit(self, offers, current_summary): return offers[0]
        def show_genome_edit_applied(self, edit, new_summary): pass
        def choose_successor(self, successors): return successors[0]
        def show_successor_selected(self, successor): pass
        def show_elimination(self, floor_number): pass
        def show_victory(self, floor_number, player): pass

    renderer = StubRenderer()
    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), renderer=renderer)

    you = make_agent("You", COOPERATE, is_player=True)
    ally = make_agent("Ally", COOPERATE)
    dissenter = make_agent("Dissenter", DEFECT)
    saboteur = make_agent("Saboteur", DEFECT)

    floor_config = SimpleNamespace(
        floor_number=1,
        rounds_per_match=1,
        ai_powerup_chance=0.0,
        featured_matches=1,
        referendum_reward=3,
        label="Test Floor",
    )

    engine.run_floor([you, ally, dissenter, saboteur], floor_number=1, floor_config=floor_config)

    assert renderer.last_referendum is not None
    assert renderer.last_referendum.cooperation_prevailed is True


def test_featured_matches_never_exceed_available_opponents() -> None:
    class StubRenderer:
        def __init__(self):
            self.round_prompts = 0

        def show_floor_roster(self, floor_number, roster_entries): pass
        def choose_round_action(self, prompt):
            self.round_prompts += 1
            return prompt.suggested_move
        def show_round_result(self, result): pass
        def choose_floor_vote(self, prompt): return prompt.suggested_vote
        def show_referendum_result(self, result): pass
        def show_run_header(self, seed): pass
        def show_floor_summary(self, floor_number, ranked): pass
        def choose_powerup(self, offers): return offers[0]
        def choose_genome_edit(self, offers, current_summary): return offers[0]
        def show_genome_edit_applied(self, edit, new_summary): pass
        def choose_successor(self, successors): return successors[0]
        def show_successor_selected(self, successor): pass
        def show_elimination(self, floor_number): pass
        def show_victory(self, floor_number, player): pass

    renderer = StubRenderer()
    engine = TournamentEngine(base_rounds_per_match=2, rng=random.Random(1), renderer=renderer)

    population = [
        make_agent("You", COOPERATE, is_player=True),
        make_agent("A", COOPERATE),
        make_agent("B", DEFECT),
    ]

    floor_config = SimpleNamespace(
        floor_number=1,
        rounds_per_match=2,
        ai_powerup_chance=0.0,
        featured_matches=99,
        referendum_reward=3,
        label="Test Floor",
    )

    engine.run_floor(population, floor_number=1, floor_config=floor_config)

    assert renderer.round_prompts == 4  # two available opponents * two rounds each


def test_conflicting_highest_priority_directives_always_resolve_to_defect() -> None:
    directives = [
        MoveDirective(move=COOPERATE, priority=DirectivePriority.LOCK, source="A"),
        MoveDirective(move=DEFECT, priority=DirectivePriority.LOCK, source="B"),
        MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source="C"),
    ]

    resolved, reason = resolve_move(COOPERATE, directives)

    assert resolved == DEFECT
    assert "conflict" in reason


def test_ai_powerup_chance_cap_regression() -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    assert engine.build_floor_config(10_000).ai_powerup_chance == pytest.approx(0.75)
