import random, pytest

from prisoners_gambit.content.archetypes import build_archetype, build_player_starter_genome
from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.content.names import build_agent_name
from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.constants import COOPERATE, DEFECT


def test_powerup_pool_is_non_empty_and_contains_parameterized_variants() -> None:
    pool = build_powerup_pool()

    assert len(pool) > 0
    names = [powerup.name for powerup in pool]
    assert "Opening Gambit" in names
    assert "Trust Dividend" in names

    opening_gambits = [powerup for powerup in pool if powerup.name == "Opening Gambit"]
    assert len(opening_gambits) >= 2
    assert sorted({perk.bonus for perk in opening_gambits}) == [1, 2]


def test_powerup_pool_items_clone_without_losing_parameters() -> None:
    pool = build_powerup_pool()
    parameterized = next(powerup for powerup in pool if getattr(powerup, "bonus", None) == 2)

    clone = parameterized.clone()

    assert clone is not parameterized
    assert type(clone) is type(parameterized)
    assert getattr(clone, "bonus", None) == 2


def test_genome_edit_pool_is_non_empty_and_contains_expected_names() -> None:
    pool = build_genome_edit_pool()
    names = {edit.name for edit in pool}

    assert len(pool) > 0
    assert "Open With Trust" in names
    assert "Open With Knife" in names
    assert "Punish Betrayal" in names
    assert "Calm the Noise" in names


def test_build_archetype_returns_label_profile_and_genome() -> None:
    archetype = build_archetype(index=0, rng=random.Random(1))

    assert isinstance(archetype.label, str) and archetype.label.strip()
    assert isinstance(archetype.public_profile, str) and archetype.public_profile.strip()
    assert archetype.genome is not None


def test_build_archetype_for_known_indices_is_deterministic_shape() -> None:
    labels = [build_archetype(index=i, rng=random.Random(1)).label for i in range(5)]

    assert len(labels) == 5
    assert all(isinstance(label, str) and label.strip() for label in labels)


def test_build_player_starter_genome_is_reciprocal_baseline() -> None:
    genome = build_player_starter_genome()

    assert genome.first_move == COOPERATE
    assert genome.response_table[(COOPERATE, COOPERATE)] == COOPERATE
    assert genome.response_table[(COOPERATE, DEFECT)] == DEFECT
    assert genome.response_table[(DEFECT, COOPERATE)] == COOPERATE
    assert genome.response_table[(DEFECT, DEFECT)] == DEFECT
    assert genome.noise == pytest.approx(0.0)


def test_build_agent_name_returns_simple_title_for_early_indices() -> None:
    name = build_agent_name(index=0, rng=random.Random(1))
    assert isinstance(name, str)
    assert "#" in name


def test_build_agent_name_returns_suffixed_title_for_larger_indices() -> None:
    name = build_agent_name(index=50, rng=random.Random(1))
    assert isinstance(name, str)
    assert "#" in name
    assert "of " in name or "The " in name
