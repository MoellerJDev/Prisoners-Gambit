import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import TrustDividend
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.evolution import EvolutionEngine


def make_agent(
    name: str,
    *,
    lineage_id: int | None = None,
    lineage_depth: int = 0,
    first_move: int = COOPERATE,
) -> Agent:
    genome = StrategyGenome(
        first_move=first_move,
        response_table={
            (COOPERATE, COOPERATE): COOPERATE,
            (COOPERATE, DEFECT): COOPERATE,
            (DEFECT, COOPERATE): COOPERATE,
            (DEFECT, DEFECT): COOPERATE,
        },
        noise=0.0,
    )
    return Agent(
        name=name,
        genome=genome,
        lineage_id=lineage_id,
        lineage_depth=lineage_depth,
    )


def test_split_population_returns_expected_groups() -> None:
    agents = [make_agent(f"Agent {i}") for i in range(6)]
    for index, agent in enumerate(agents):
        agent.score = 100 - index

    ranked = sorted(agents, key=lambda agent: agent.score, reverse=True)

    engine = EvolutionEngine(
        survivor_count=3,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    survivors, eliminated = engine.split_population(ranked)

    assert len(survivors) == 3
    assert len(eliminated) == 3
    assert survivors[0].name == "Agent 0"
    assert eliminated[-1].name == "Agent 5"


def test_repopulate_restores_target_population_size() -> None:
    survivors = [make_agent("A"), make_agent("B")]

    engine = EvolutionEngine(
        survivor_count=2,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    next_population = engine.repopulate(survivors=survivors, target_size=5)

    assert len(next_population) == 5
    assert next_population[0].name == "A"
    assert next_population[1].name == "B"
    assert any(agent.name.endswith("*") for agent in next_population[2:])


def test_descendant_line_keeps_lineage_and_depth() -> None:
    survivors = [make_agent("You", lineage_id=1)]

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    next_population = engine.repopulate(survivors=survivors, target_size=2)

    child = next_population[1]
    assert child.lineage_id == 1
    assert child.lineage_depth == 1


def test_offspring_inherit_up_to_three_powerups() -> None:
    parent = make_agent("Parent", lineage_id=1)
    parent.is_player = True
    parent.powerups.extend([
        TrustDividend(bonus=1),
        TrustDividend(bonus=2),
        TrustDividend(bonus=3),
        TrustDividend(bonus=4),
    ])

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    next_population = engine.repopulate([parent], target_size=2)
    child = next_population[1]

    assert len(child.powerups) == 3
    assert [powerup.bonus for powerup in child.powerups[:2]] == [1, 2]


def test_player_lineage_offspring_gets_doctrine_pressure_powerup() -> None:
    parent = make_agent("Parent", lineage_id=1)
    parent.is_player = True

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    next_population = engine.repopulate([parent], target_size=2)
    child = next_population[1]

    assert len(child.powerups) <= 1
    assert child.genome is not parent.genome


def test_player_lineage_divergence_uses_active_player_lineage_not_hardcoded_id() -> None:
    parent = make_agent("PlayerHost", lineage_id=42)
    parent.is_player = True

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.2,
        descendant_mutation_bonus=1.75,
        rng=random.Random(2),
    )

    next_population = engine.repopulate([parent], target_size=2)
    child = next_population[1]

    assert child.lineage_id == 42
    assert child.name != "PlayerHost*"


def test_offspring_receive_cloned_powerups_not_same_instances() -> None:
    parent = make_agent("Parent", lineage_id=1)
    parent.powerups.append(TrustDividend(bonus=2))

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    next_population = engine.repopulate([parent], target_size=2)
    child = next_population[1]

    assert child.powerups[0] is not parent.powerups[0]
    assert child.powerups[0].name == parent.powerups[0].name


def test_repopulate_preserves_survivor_order_at_front() -> None:
    survivors = [make_agent("A"), make_agent("B"), make_agent("C")]

    engine = EvolutionEngine(
        survivor_count=3,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(2),
    )

    next_population = engine.repopulate(survivors=survivors, target_size=5)

    assert next_population[:3] == survivors


def test_descendant_bonus_can_change_offspring_genome_more_aggressively() -> None:
    parent = make_agent("You", lineage_id=1, first_move=COOPERATE)

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=1.0,
        descendant_mutation_bonus=2.0,
        rng=random.Random(1),
    )

    next_population = engine.repopulate([parent], target_size=2)
    child = next_population[1]

    assert child.genome is not parent.genome
    assert child.lineage_id == 1


def test_non_lineage_survivors_do_not_gain_player_lineage_id() -> None:
    parent = make_agent("Bot", lineage_id=None)

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    next_population = engine.repopulate([parent], target_size=2)
    child = next_population[1]

    assert child.lineage_id is None


def test_repopulate_with_target_equal_survivors_returns_no_new_children() -> None:
    survivors = [make_agent("A"), make_agent("B")]

    engine = EvolutionEngine(
        survivor_count=2,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )

    next_population = engine.repopulate(survivors=survivors, target_size=2)

    assert next_population == survivors
    assert all(not agent.name.endswith("*") for agent in next_population)


def test_apply_branch_focus_returns_new_genome_without_mutating_input() -> None:
    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=random.Random(1),
    )
    original = StrategyGenome(
        first_move=DEFECT,
        response_table={
            (COOPERATE, COOPERATE): DEFECT,
            (COOPERATE, DEFECT): COOPERATE,
            (DEFECT, COOPERATE): COOPERATE,
            (DEFECT, DEFECT): DEFECT,
        },
        noise=0.2,
    )

    transformed = engine._apply_branch_focus(original, "safe")

    assert transformed is not original
    assert original.first_move == DEFECT
    assert original.response_table[(COOPERATE, COOPERATE)] == DEFECT
    assert transformed.first_move == COOPERATE


def test_repopulate_does_not_duplicate_injected_doctrine_powerup_types() -> None:
    class FakeRng(random.Random):
        def choice(self, seq):
            return seq[0]

        def random(self) -> float:
            return 0.0

        def uniform(self, a, b):
            return a

    parent = make_agent("Parent", lineage_id=1)
    parent.is_player = True
    parent.powerups.append(TrustDividend(bonus=2))

    engine = EvolutionEngine(
        survivor_count=1,
        mutation_rate=0.15,
        descendant_mutation_bonus=1.75,
        rng=FakeRng(),
    )
    engine._doctrine_powerup = lambda _branch_focus: TrustDividend(bonus=1)

    next_population = engine.repopulate([parent], target_size=2)
    child = next_population[1]

    trust_dividends = [powerup for powerup in child.powerups if isinstance(powerup, TrustDividend)]
    assert len(trust_dividends) == 1
