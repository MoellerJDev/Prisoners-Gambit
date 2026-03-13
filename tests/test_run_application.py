import random

from prisoners_gambit.app.run_application import RunApplication
from prisoners_gambit.config.settings import Settings
from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.events import EventBus
from prisoners_gambit.core.interaction import (
    FeaturedMatchPrompt,
    FeaturedRoundResult,
    FloorVotePrompt,
    FloorVoteResult,
    RosterEntry,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.evolution import EvolutionEngine
from prisoners_gambit.systems.progression import ProgressionEngine
from prisoners_gambit.systems.tournament import TournamentEngine


class StubRenderer:
    def __init__(self) -> None:
        self.headers: list[int | None] = []
        self.rosters: list[tuple[int, int]] = []
        self.floor_summaries: list[tuple[int, int]] = []
        self.featured_floor_summaries: list[list[str]] = []
        self.selected_powerups: list[str] = []
        self.selected_edits: list[str] = []
        self.round_prompts: int = 0
        self.vote_prompts: int = 0
        self.successor_choices: list[str] = []
        self.eliminated_floor: int | None = None
        self.victory: tuple[int, str] | None = None

    def show_run_header(self, seed: int | None) -> None:
        self.headers.append(seed)

    def show_floor_roster(self, floor_number: int, roster_entries: list[RosterEntry]) -> None:
        self.rosters.append((floor_number, len(roster_entries)))

    def show_floor_summary(self, floor_number: int, ranked: list[Agent]) -> None:
        self.floor_summaries.append((floor_number, len(ranked)))

    def show_floor_featured_inference_summary(self, summary: list[str]) -> None:
        self.featured_floor_summaries.append(list(summary))

    def choose_round_action(self, prompt: FeaturedMatchPrompt) -> int:
        self.round_prompts += 1
        return prompt.suggested_move if prompt.round_index % 2 == 0 else COOPERATE

    def show_round_result(self, result: FeaturedRoundResult) -> None:
        pass

    def choose_floor_vote(self, prompt: FloorVotePrompt) -> int:
        self.vote_prompts += 1
        return prompt.suggested_vote

    def show_referendum_result(self, result: FloorVoteResult) -> None:
        pass

    def choose_powerup(self, offers):
        selected = offers[0]
        self.selected_powerups.append(selected.name)
        return selected

    def choose_genome_edit(self, offers, current_summary: str):
        selected = offers[0]
        self.selected_edits.append(selected.name)
        return selected

    def show_genome_edit_applied(self, edit, new_summary: str) -> None:
        pass

    def show_phase_transition(self, title: str, message: str) -> None:
        pass

    def show_successor_selected(self, successor: Agent) -> None:
        pass

    def choose_successor(self, successors: list[Agent]) -> Agent:
        chosen = sorted(successors, key=lambda agent: (agent.score, agent.wins), reverse=True)[0]
        self.successor_choices.append(chosen.name)
        return chosen

    def show_phase_transition(self, title: str, message: str) -> None:
        pass

    def show_elimination(self, floor_number: int, seed: int) -> None:
        self.eliminated_floor = floor_number

    def show_victory(self, floor_number: int, player: Agent, seed: int) -> None:
        self.victory = (floor_number, player.name)


def test_run_application_smoke() -> None:
    settings = Settings(
        population_size=8,
        rounds_per_match=3,
        survivor_count=4,
        offers_per_floor=5,
        featured_matches_per_floor=2,
        genome_edit_offers_per_floor=3,
        floors=2,
        mutation_rate=0.1,
        descendant_mutation_bonus=1.75,
        seed=7,
        auto_choose_powerups=True,
        auto_choose_round_actions=True,
        auto_choose_genome_edits=True,
        auto_choose_floor_vote=True,
        log_to_console=False,
        log_to_file=False,
    )

    rng = random.Random(settings.seed)
    event_bus = EventBus()
    renderer = StubRenderer()

    tournament = TournamentEngine(
        base_rounds_per_match=settings.rounds_per_match,
        rng=rng,
        renderer=renderer,
        event_bus=event_bus,
    )
    evolution = EvolutionEngine(
        survivor_count=settings.survivor_count,
        mutation_rate=settings.mutation_rate,
        descendant_mutation_bonus=settings.descendant_mutation_bonus,
        rng=rng,
    )
    progression = ProgressionEngine(
        rng=rng,
        offers_per_floor=settings.offers_per_floor,
        featured_matches_per_floor=settings.featured_matches_per_floor,
    )

    app = RunApplication(
        settings=settings,
        renderer=renderer,
        event_bus=event_bus,
        tournament=tournament,
        evolution=evolution,
        progression=progression,
    )

    player = app.run()

    assert isinstance(player.powerups, list)
    assert renderer.headers == [7]
    assert len(renderer.rosters) >= 1
    assert len(renderer.floor_summaries) >= 1
    assert renderer.vote_prompts >= 1
    assert app.interaction_controller.snapshot.current_floor is not None
    assert app.interaction_controller.snapshot.current_phase is not None
    assert app.interaction_controller.snapshot.floor_summary is not None
    assert renderer.featured_floor_summaries
    assert app.interaction_controller.snapshot.floor_roster is not None
    assert app.interaction_controller.snapshot.floor_vote_result is not None
    assert renderer.selected_powerups or renderer.eliminated_floor is not None or renderer.victory is not None


class ScriptedTournament:
    def __init__(self, ranked_sequences: list[list[Agent]]) -> None:
        self.ranked_sequences = ranked_sequences
        self.call_count = 0
        self.phases: list[str] = []

    def run_floor(self, population: list[Agent], floor_number: int, floor_config, phase: str) -> list[Agent]:
        self.phases.append(phase)
        ranked = self.ranked_sequences[self.call_count]
        self.call_count += 1
        return ranked


class PassiveEvolution:
    def __init__(self, survivor_count: int) -> None:
        self.survivor_count = survivor_count

    def split_population(self, ranked: list[Agent]) -> tuple[list[Agent], list[Agent]]:
        return ranked[:self.survivor_count], ranked[self.survivor_count:]


    def split_population_civil_war(self, ranked: list[Agent]) -> tuple[list[Agent], list[Agent]]:
        survivor_count = max(1, (len(ranked) + 1) // 2)
        return ranked[:survivor_count], ranked[survivor_count:]

    def repopulate(self, survivors: list[Agent], target_size: int) -> list[Agent]:
        return list(survivors)


class PassiveProgression:
    def __init__(self) -> None:
        self.rng = random.Random(1)

    def build_floor_config(self, floor_number: int):
        class _FloorConfig:
            def __init__(self, floor_number: int) -> None:
                self.floor_number = floor_number
                self.rounds_per_match = 1
                self.ai_powerup_chance = 0.0
                self.featured_matches = 0
                self.referendum_reward = 3
                self.label = "Test Floor"

        return _FloorConfig(floor_number)

    def grant_ai_powerups(self, survivors: list[Agent], player: Agent, floor_config) -> None:
        return


def _make_agent(
    name: str,
    score: int,
    wins: int,
    is_player: bool,
    lineage_id: int | None,
    lineage_depth: int = 0,
) -> Agent:
    genome = StrategyGenome(
        first_move=COOPERATE,
        response_table={
            (COOPERATE, COOPERATE): COOPERATE,
            (COOPERATE, 1): COOPERATE,
            (1, COOPERATE): COOPERATE,
            (1, 1): COOPERATE,
        },
        noise=0.0,
    )
    agent = Agent(
        name=name,
        genome=genome,
        is_player=is_player,
        lineage_id=lineage_id,
        lineage_depth=lineage_depth,
    )
    agent.score = score
    agent.wins = wins
    return agent


def _build_transfer_test_app(
    monkeypatch,
    ranked_sequences: list[list[Agent]],
    initial_population: list[Agent],
    survivor_count: int,
) -> tuple[RunApplication, StubRenderer, ScriptedTournament]:
    import prisoners_gambit.app.run_application as run_application_module

    def fake_create_population(size: int, rng) -> list[Agent]:
        return list(initial_population)

    monkeypatch.setattr(run_application_module, "create_population", fake_create_population)

    settings = Settings(
        population_size=len(initial_population),
        survivor_count=survivor_count,
        offers_per_floor=1,
        featured_matches_per_floor=0,
        genome_edit_offers_per_floor=1,
        floors=len(ranked_sequences),
        auto_choose_powerups=True,
        auto_choose_round_actions=True,
        auto_choose_genome_edits=True,
        auto_choose_floor_vote=True,
        log_to_console=False,
        log_to_file=False,
    )

    renderer = StubRenderer()
    tournament = ScriptedTournament(ranked_sequences)
    app = RunApplication(
        settings=settings,
        renderer=renderer,
        event_bus=EventBus(),
        tournament=tournament,
        evolution=PassiveEvolution(survivor_count=survivor_count),
        progression=PassiveProgression(),
    )
    return app, renderer, tournament


def test_player_transfers_to_first_generation_descendant_when_host_is_eliminated(monkeypatch) -> None:
    player = _make_agent("You", score=1, wins=0, is_player=True, lineage_id=1, lineage_depth=0)
    child = _make_agent("You*", score=10, wins=2, is_player=False, lineage_id=1, lineage_depth=1)
    outsider = _make_agent("Bot", score=8, wins=1, is_player=False, lineage_id=None)

    ranked_floor_1 = [child, outsider, player]

    app, renderer, tournament = _build_transfer_test_app(
        monkeypatch=monkeypatch,
        ranked_sequences=[ranked_floor_1],
        initial_population=[player, child, outsider],
        survivor_count=2,
    )

    result = app.run()

    assert renderer.eliminated_floor is None
    assert renderer.successor_choices == ["You*"]
    assert result is child
    assert result.name == "You*"
    assert result.is_player is True
    assert player.is_player is False
    assert tournament.phases == ["ecosystem"]


def test_player_transfers_to_second_generation_descendant_when_only_second_generation_survives(monkeypatch) -> None:
    player = _make_agent("You", score=1, wins=0, is_player=True, lineage_id=1, lineage_depth=0)
    grandchild = _make_agent("You**", score=12, wins=3, is_player=False, lineage_id=1, lineage_depth=2)
    outsider = _make_agent("Bot", score=9, wins=1, is_player=False, lineage_id=None)

    ranked_floor_1 = [grandchild, outsider, player]

    app, renderer, tournament = _build_transfer_test_app(
        monkeypatch=monkeypatch,
        ranked_sequences=[ranked_floor_1],
        initial_population=[player, grandchild, outsider],
        survivor_count=2,
    )

    result = app.run()

    assert renderer.eliminated_floor is None
    assert renderer.successor_choices == ["You**"]
    assert result is grandchild
    assert result.name == "You**"
    assert result.is_player is True
    assert player.is_player is False
    assert tournament.phases == ["ecosystem"]


def test_player_transfers_to_any_generation_descendant_when_lineage_survives(monkeypatch) -> None:
    player = _make_agent("You", score=1, wins=0, is_player=True, lineage_id=1, lineage_depth=0)
    child = _make_agent("You*", score=3, wins=1, is_player=False, lineage_id=1, lineage_depth=1)
    grandchild = _make_agent("You**", score=6, wins=2, is_player=False, lineage_id=1, lineage_depth=2)
    deep_descendant = _make_agent("You****", score=15, wins=4, is_player=False, lineage_id=1, lineage_depth=4)
    outsider = _make_agent("Bot", score=10, wins=3, is_player=False, lineage_id=None)

    ranked_floor_1 = [deep_descendant, outsider, grandchild, child, player]

    app, renderer, tournament = _build_transfer_test_app(
        monkeypatch=monkeypatch,
        ranked_sequences=[ranked_floor_1],
        initial_population=[player, child, grandchild, deep_descendant, outsider],
        survivor_count=4,
    )

    result = app.run()

    assert renderer.eliminated_floor is None
    assert renderer.successor_choices == ["You****"]
    assert result is deep_descendant
    assert result.name == "You****"
    assert result.lineage_id == 1
    assert result.lineage_depth == 4
    assert result.is_player is True
    assert player.is_player is False
    assert tournament.phases == ["ecosystem"]


def test_player_is_eliminated_only_when_entire_lineage_is_gone(monkeypatch) -> None:
    player = _make_agent("You", score=1, wins=0, is_player=True, lineage_id=1, lineage_depth=0)
    outsider_a = _make_agent("Bot A", score=12, wins=3, is_player=False, lineage_id=None)
    outsider_b = _make_agent("Bot B", score=11, wins=2, is_player=False, lineage_id=None)

    ranked_floor_1 = [outsider_a, outsider_b, player]

    app, renderer, tournament = _build_transfer_test_app(
        monkeypatch=monkeypatch,
        ranked_sequences=[ranked_floor_1],
        initial_population=[player, outsider_a, outsider_b],
        survivor_count=2,
    )

    result = app.run()

    assert renderer.eliminated_floor == 1
    assert renderer.successor_choices == []
    assert result is player
    assert tournament.phases == ["ecosystem"]


def test_run_application_passes_phase_to_tournament_across_transition(monkeypatch) -> None:
    player = _make_agent("You", score=10, wins=2, is_player=True, lineage_id=1, lineage_depth=0)
    child = _make_agent("You*", score=9, wins=1, is_player=False, lineage_id=1, lineage_depth=1)
    outsider = _make_agent("Bot", score=1, wins=0, is_player=False, lineage_id=None, lineage_depth=0)

    ranked_floor_1 = [player, child, outsider]
    ranked_floor_2 = [child, player]

    app, _renderer, tournament = _build_transfer_test_app(
        monkeypatch=monkeypatch,
        ranked_sequences=[ranked_floor_1, ranked_floor_2],
        initial_population=[player, child, outsider],
        survivor_count=2,
    )

    app.run()

    assert tournament.phases == ["ecosystem", "civil_war"]


def test_run_application_uses_stable_house_doctrine_across_phases(monkeypatch) -> None:
    import prisoners_gambit.app.run_application as run_application_module

    player = _make_agent("You", score=10, wins=2, is_player=True, lineage_id=1, lineage_depth=0)
    child = _make_agent("You*", score=9, wins=1, is_player=False, lineage_id=1, lineage_depth=1)
    outsider = _make_agent("Bot", score=1, wins=0, is_player=False, lineage_id=None, lineage_depth=0)

    ranked_floor_1 = [player, child, outsider]
    ranked_floor_2 = [child, player]

    captured_house: list[str | None] = []

    real_generate = run_application_module.generate_powerup_offer_set

    def capture_generate(count, rng, context=None):
        captured_house.append(None if context is None else context.house_doctrine_family)
        return real_generate(count, rng, context=context)

    monkeypatch.setattr(run_application_module, "generate_powerup_offer_set", capture_generate)

    app, _renderer, tournament = _build_transfer_test_app(
        monkeypatch=monkeypatch,
        ranked_sequences=[ranked_floor_1, ranked_floor_2],
        initial_population=[player, child, outsider],
        survivor_count=2,
    )

    app.run()

    assert tournament.phases == ["ecosystem", "civil_war"]
    assert len(captured_house) >= 2
    assert len(set(captured_house)) == 1


def test_run_and_web_use_same_house_doctrine_seed_rule() -> None:
    from prisoners_gambit.systems.offers import seed_house_doctrine
    from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

    seed = 33
    expected = seed_house_doctrine(seed=seed)

    session = FeaturedMatchWebSession(seed=seed, rounds=1)
    session.start()

    assert session.view()["snapshot"]["house_doctrine_family"] == expected
