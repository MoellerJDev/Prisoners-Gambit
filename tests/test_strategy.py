import random, pytest

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.strategy import StrategyGenome, random_genome


def make_genome(*, first_move=COOPERATE, noise=0.0) -> StrategyGenome:
    return StrategyGenome(
        first_move=first_move,
        response_table={
            (COOPERATE, COOPERATE): COOPERATE,
            (COOPERATE, DEFECT): DEFECT,
            (DEFECT, COOPERATE): COOPERATE,
            (DEFECT, DEFECT): DEFECT,
        },
        noise=noise,
    )


def test_choose_move_uses_first_move_when_no_history() -> None:
    genome = make_genome(first_move=DEFECT)
    move = genome.choose_move([], [], random.Random(1))

    assert move == DEFECT


def test_choose_move_uses_response_table_after_first_round() -> None:
    genome = make_genome()
    move = genome.choose_move([COOPERATE], [DEFECT], random.Random(1))

    assert move == DEFECT


def test_noise_can_flip_intended_move_when_probability_hits() -> None:
    genome = make_genome(first_move=COOPERATE, noise=1.0)
    move = genome.choose_move([], [], random.Random(1))

    assert move == DEFECT


def test_zero_noise_does_not_flip_move() -> None:
    genome = make_genome(first_move=COOPERATE, noise=0.0)
    move = genome.choose_move([], [], random.Random(1))

    assert move == COOPERATE


def test_mutate_can_flip_first_move() -> None:
    genome = make_genome(first_move=COOPERATE, noise=0.0)
    mutated = genome.mutate(random.Random(1), mutation_rate=1.0)

    assert mutated is not genome
    assert mutated.first_move == DEFECT


def test_mutate_can_flip_response_table_entries() -> None:
    genome = make_genome(first_move=COOPERATE, noise=0.0)
    mutated = genome.mutate(random.Random(1), mutation_rate=1.0)

    assert mutated.response_table[(COOPERATE, COOPERATE)] == DEFECT
    assert mutated.response_table[(COOPERATE, DEFECT)] == COOPERATE
    assert mutated.response_table[(DEFECT, COOPERATE)] == DEFECT
    assert mutated.response_table[(DEFECT, DEFECT)] == COOPERATE


def test_mutate_clamps_noise_at_upper_bound() -> None:
    genome = make_genome(noise=0.35)
    mutated = genome.mutate(random.Random(1), mutation_rate=1.0)

    assert 0.0 <= mutated.noise <= 0.35


def test_mutate_clamps_noise_at_lower_bound() -> None:
    genome = make_genome(noise=0.0)
    mutated = genome.mutate(random.Random(2), mutation_rate=1.0)

    assert 0.0 <= mutated.noise <= 0.35


def test_summary_contains_first_move_table_and_noise() -> None:
    genome = make_genome(first_move=COOPERATE, noise=0.12)
    summary = genome.summary()

    assert summary.startswith("F:C")
    assert "T:" in summary
    assert "N:0.12" in summary


def test_random_genome_produces_valid_moves_and_noise_range() -> None:
    genome = random_genome(random.Random(1))

    assert genome.first_move in {COOPERATE, DEFECT}
    assert all(move in {COOPERATE, DEFECT} for move in genome.response_table.values())
    assert 0.0 <= genome.noise <= 0.1