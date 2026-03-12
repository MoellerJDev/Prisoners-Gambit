import random
from types import SimpleNamespace

from prisoners_gambit.app.run_application import RunApplication
from prisoners_gambit.config.settings import Settings
from prisoners_gambit.core.events import EventBus
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.strategy import StrategyGenome


def make_agent(
    name: str,
    *,
    score: int,
    wins: int,
    is_player: bool,
    lineage_id: int | None,
    lineage_depth: int = 0,
) -> Agent:
    agent = Agent(
        name=name,
        genome=StrategyGenome(
            first_move=0,
            response_table={
                (0, 0): 0,
                (0, 1): 0,
                (1, 0): 0,
                (1, 1): 0,
            },
            noise=0.0,
        ),
        is_player=is_player,
        lineage_id=lineage_id,
        lineage_depth=lineage_depth,
    )
    agent.score = score
    agent.wins = wins
    return agent


class StubRenderer:
    def __init__(self) -> None:
        self.transitions: list[str] = []
        self.successor_choices: list[str] = []
        self.victory: tuple[int, str] | None = None
        self.eliminated_floor: int | None = None

    def show_run_header(self, seed): pass
    def show_floor_roster(self, floor_number, roster_entries): pass
    def show_floor_summary(self, floor_number, ranked): pass
    def choose_round_action(self, prompt): return prompt.suggested_move
    def show_round_result(self, result): pass
    def choose_floor_vote(self, prompt): return prompt.suggested_vote
    def show_referendum_result(self, result): pass
    def choose_powerup(self, offers): return offers[0]
    def choose_genome_edit(self, offers, current_summary): return offers[0]
    def show_genome_edit_applied(self, edit, new_summary): pass

    def show_phase_transition(self, title: str, message: str) -> None:
        self.transitions.append(title)

    def choose_successor(self, successors):
        chosen = sorted(successors, key=lambda agent: (agent.score, agent.wins), reverse=True)[0]
        self.successor_choices.append(chosen.name)
        return chosen

    def show_successor_selected(self, successor): pass

    def show_elimination(self, floor_number, seed):
        self.eliminated_floor = floor_number

    def show_victory(self, floor_number, player, seed):
        self.victory = (floor_number, player.name)


class ScriptedTournament:
    def __init__(self, ranked_sequences):
        self.ranked_sequences = ranked_sequences
        self.call_count = 0

    def run_floor(self, population, floor_number, floor_config, phase="ecosystem"):
        ranked = self.ranked_sequences[self.call_count]
        self.call_count += 1
        return ranked


class PassiveEvolution:
    def __init__(self, survivor_count: int):
        self.survivor_count = survivor_count

    def split_population(self, ranked):
        return ranked[: self.survivor_count], ranked[self.survivor_count :]

    def split_population_civil_war(self, ranked):
        survivor_count = max(1, (len(ranked) + 1) // 2)
        return ranked[:survivor_count], ranked[survivor_count:]

    def repopulate(self, survivors, target_size):
        return list(survivors)


class PassiveProgression:
    def __init__(self):
        self.rng = random.Random(1)

    def build_floor_config(self, floor_number: int):
        return SimpleNamespace(
            floor_number=floor_number,
            rounds_per_match=1,
            ai_powerup_chance=0.0,
            featured_matches=0,
            referendum_reward=3,
            label="Test Floor",
        )

    def grant_ai_powerups(self, survivors, player, floor_config):
        return


def build_app(monkeypatch, initial_population, ranked_sequences, survivor_count):
    import prisoners_gambit.app.run_application as run_application_module

    def fake_create_population(size, rng):
        return list(initial_population)

    monkeypatch.setattr(run_application_module, "create_population", fake_create_population)

    settings = Settings(
        population_size=len(initial_population),
        survivor_count=survivor_count,
        offers_per_floor=1,
        featured_matches_per_floor=0,
        genome_edit_offers_per_floor=1,
        floors=10,
        auto_choose_powerups=True,
        auto_choose_round_actions=True,
        auto_choose_genome_edits=True,
        auto_choose_floor_vote=True,
        log_to_console=False,
        log_to_file=False,
    )

    renderer = StubRenderer()
    app = RunApplication(
        settings=settings,
        renderer=renderer,
        event_bus=EventBus(),
        tournament=ScriptedTournament(ranked_sequences),
        evolution=PassiveEvolution(survivor_count=survivor_count),
        progression=PassiveProgression(),
    )
    return app, renderer


def test_civil_war_begins_when_outsiders_are_gone(monkeypatch) -> None:
    player = make_agent("You", score=10, wins=2, is_player=True, lineage_id=1)
    child = make_agent("Heir Alpha", score=9, wins=1, is_player=False, lineage_id=1, lineage_depth=1)
    outsider = make_agent("Bot", score=2, wins=0, is_player=False, lineage_id=None)

    ranked_floor_1 = [player, child, outsider]
    ranked_floor_2 = [child, player]

    app, renderer = build_app(
        monkeypatch,
        [player, child, outsider],
        [ranked_floor_1, ranked_floor_2],
        survivor_count=2,
    )

    result = app.run()

    assert "Lineage Judgment: Civil War" in renderer.transitions
    assert result is player or result is child
    assert renderer.victory is not None


def test_civil_war_can_end_with_successor_transfer(monkeypatch) -> None:
    player = make_agent("You", score=10, wins=2, is_player=True, lineage_id=1)
    child = make_agent("Heir Alpha", score=9, wins=1, is_player=False, lineage_id=1, lineage_depth=1)
    grandchild = make_agent("Heir Beta", score=12, wins=3, is_player=False, lineage_id=1, lineage_depth=2)
    outsider = make_agent("Bot", score=1, wins=0, is_player=False, lineage_id=None)

    ranked_floor_1 = [grandchild, child, player, outsider]
    ranked_floor_2 = [grandchild, child, player]
    ranked_floor_3 = [grandchild, child]

    app, renderer = build_app(
        monkeypatch,
        [player, child, grandchild, outsider],
        [ranked_floor_1, ranked_floor_2, ranked_floor_3],
        survivor_count=3,
    )

    result = app.run()

    assert "Lineage Judgment: Civil War" in renderer.transitions
    assert renderer.successor_choices
    assert result is grandchild or result is child


def test_immediate_full_victory_if_only_one_lineage_member_remains_after_ecosystem_phase(monkeypatch) -> None:
    player = make_agent("You", score=10, wins=2, is_player=True, lineage_id=1)
    outsider = make_agent("Bot", score=1, wins=0, is_player=False, lineage_id=None)

    ranked_floor_1 = [player, outsider]

    app, renderer = build_app(
        monkeypatch,
        [player, outsider],
        [ranked_floor_1],
        survivor_count=1,
    )

    result = app.run()

    assert "Lineage Judgment: Civil War" in renderer.transitions
    assert result is player
    assert renderer.victory is not None
