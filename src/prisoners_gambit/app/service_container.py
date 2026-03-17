from __future__ import annotations

import random

from prisoners_gambit.app.run_application import RunApplication
from prisoners_gambit.config.settings import Settings
from prisoners_gambit.core.events import EventBus
from prisoners_gambit.systems.evolution import EvolutionEngine
from prisoners_gambit.systems.progression import ProgressionEngine
from prisoners_gambit.systems.tournament import TournamentEngine
from prisoners_gambit.ui.terminal import TerminalRenderer


def build_run_application(settings: Settings) -> RunApplication:
    rng = random.Random(settings.seed)
    event_bus = EventBus()

    renderer = TerminalRenderer(
        auto_choose_powerups=settings.auto_choose_powerups,
        auto_choose_round_actions=settings.auto_choose_round_actions,
        auto_choose_genome_edits=settings.auto_choose_genome_edits,
        auto_choose_floor_vote=settings.auto_choose_floor_vote,
        auto_choose_successors=settings.auto_choose_successors,
    )

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

    return RunApplication(
        settings=settings,
        renderer=renderer,
        event_bus=event_bus,
        tournament=tournament,
        evolution=evolution,
        progression=progression,
    )
