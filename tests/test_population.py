import random

import pytest

from prisoners_gambit.core.models import Agent
from prisoners_gambit.systems.population import create_population


def test_create_population_respects_requested_size() -> None:
    population = create_population(12, random.Random(1))
    assert len(population) == 12


def test_create_population_requires_at_least_two_agents() -> None:
    with pytest.raises(ValueError):
        create_population(1, random.Random(1))


def test_create_population_has_exactly_one_player() -> None:
    population = create_population(12, random.Random(1))
    players = [agent for agent in population if agent.is_player]

    assert len(players) == 1
    assert players[0].name == "You"


def test_player_starts_with_expected_lineage() -> None:
    population = create_population(8, random.Random(1))
    player = next(agent for agent in population if agent.is_player)

    assert player.lineage_id == 1
    assert player.lineage_depth == 0


def test_non_player_agents_do_not_start_in_player_lineage() -> None:
    population = create_population(8, random.Random(1))
    non_players = [agent for agent in population if not agent.is_player]

    assert all(agent.lineage_id is None for agent in non_players)
    assert all(agent.lineage_depth == 0 for agent in non_players)


def test_all_population_entries_are_agents() -> None:
    population = create_population(10, random.Random(1))
    assert all(isinstance(agent, Agent) for agent in population)


def test_player_has_expected_public_profile() -> None:
    population = create_population(6, random.Random(1))
    player = next(agent for agent in population if agent.is_player)

    assert player.public_profile == "Adaptive human pilot"


def test_non_players_have_non_empty_names_and_profiles() -> None:
    population = create_population(10, random.Random(1))
    non_players = [agent for agent in population if not agent.is_player]

    assert all(isinstance(agent.name, str) and agent.name.strip() for agent in non_players)
    assert all(isinstance(agent.public_profile, str) and agent.public_profile.strip() for agent in non_players)


def test_population_starter_player_is_inserted_at_front() -> None:
    population = create_population(5, random.Random(1))

    assert population[0].is_player is True
    assert population[0].name == "You"