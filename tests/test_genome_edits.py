import pytest

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.genome_edits import (
    CalmTheNoise,
    EmbraceChaos,
    OpenWithKnife,
    OpenWithTrust,
    PreservePeace,
    PressAdvantage,
    PunishBetrayal,
)
from prisoners_gambit.core.strategy import StrategyGenome


def make_genome(*, first_move=COOPERATE, noise=0.10) -> StrategyGenome:
    return StrategyGenome(
        first_move=first_move,
        response_table={
            (COOPERATE, COOPERATE): DEFECT,
            (COOPERATE, DEFECT): COOPERATE,
            (DEFECT, COOPERATE): COOPERATE,
            (DEFECT, DEFECT): DEFECT,
        },
        noise=noise,
    )


def test_open_with_trust_sets_first_move_to_cooperate_only() -> None:
    genome = make_genome(first_move=DEFECT)
    updated = OpenWithTrust().apply(genome)

    assert updated is not genome
    assert updated.first_move == COOPERATE
    assert updated.response_table == genome.response_table
    assert updated.noise == genome.noise


def test_open_with_knife_sets_first_move_to_defect_only() -> None:
    genome = make_genome(first_move=COOPERATE)
    updated = OpenWithKnife().apply(genome)

    assert updated is not genome
    assert updated.first_move == DEFECT
    assert updated.response_table == genome.response_table
    assert updated.noise == genome.noise


def test_punish_betrayal_only_changes_cd_response() -> None:
    genome = make_genome()
    updated = PunishBetrayal().apply(genome)

    assert updated.response_table[(COOPERATE, DEFECT)] == DEFECT
    assert updated.response_table[(COOPERATE, COOPERATE)] == genome.response_table[(COOPERATE, COOPERATE)]
    assert updated.response_table[(DEFECT, COOPERATE)] == genome.response_table[(DEFECT, COOPERATE)]
    assert updated.response_table[(DEFECT, DEFECT)] == genome.response_table[(DEFECT, DEFECT)]
    assert updated.first_move == genome.first_move
    assert updated.noise == genome.noise


def test_preserve_peace_only_changes_cc_response() -> None:
    genome = make_genome()
    updated = PreservePeace().apply(genome)

    assert updated.response_table[(COOPERATE, COOPERATE)] == COOPERATE
    assert updated.response_table[(COOPERATE, DEFECT)] == genome.response_table[(COOPERATE, DEFECT)]
    assert updated.response_table[(DEFECT, COOPERATE)] == genome.response_table[(DEFECT, COOPERATE)]
    assert updated.response_table[(DEFECT, DEFECT)] == genome.response_table[(DEFECT, DEFECT)]


def test_press_advantage_only_changes_dc_response() -> None:
    genome = make_genome()
    updated = PressAdvantage().apply(genome)

    assert updated.response_table[(DEFECT, COOPERATE)] == DEFECT
    assert updated.response_table[(COOPERATE, COOPERATE)] == genome.response_table[(COOPERATE, COOPERATE)]
    assert updated.response_table[(COOPERATE, DEFECT)] == genome.response_table[(COOPERATE, DEFECT)]
    assert updated.response_table[(DEFECT, DEFECT)] == genome.response_table[(DEFECT, DEFECT)]


def test_calm_the_noise_reduces_noise_but_not_below_zero() -> None:
    genome = make_genome(noise=0.03)
    updated = CalmTheNoise().apply(genome)

    assert updated.noise == pytest.approx(0.0)
    assert updated.response_table == genome.response_table
    assert updated.first_move == genome.first_move


def test_calm_the_noise_reduces_noise_by_point_zero_five_when_possible() -> None:
    genome = make_genome(noise=0.20)
    updated = CalmTheNoise().apply(genome)

    assert updated.noise == pytest.approx(0.15)


def test_embrace_chaos_increases_noise_but_not_above_point_three_five() -> None:
    genome = make_genome(noise=0.34)
    updated = EmbraceChaos().apply(genome)

    assert updated.noise == pytest.approx(0.35)


def test_embrace_chaos_increases_noise_by_point_zero_five_when_possible() -> None:
    genome = make_genome(noise=0.10)
    updated = EmbraceChaos().apply(genome)

    assert updated.noise == pytest.approx(0.15)


def test_genome_edits_do_not_mutate_original_genome() -> None:
    genome = make_genome(first_move=DEFECT, noise=0.22)
    original_table = dict(genome.response_table)

    _ = OpenWithTrust().apply(genome)
    _ = PunishBetrayal().apply(genome)
    _ = CalmTheNoise().apply(genome)

    assert genome.first_move == DEFECT
    assert genome.noise == pytest.approx(0.22)
    assert genome.response_table == original_table
