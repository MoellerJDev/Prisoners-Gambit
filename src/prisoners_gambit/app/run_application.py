from __future__ import annotations

import logging

from prisoners_gambit.app.interaction_controller import InteractionController
from prisoners_gambit.config.settings import Settings
from prisoners_gambit.core.events import Event, EventBus
from prisoners_gambit.core.civil_war import build_civil_war_context
from prisoners_gambit.core.featured_inference import normalize_featured_inference_signals
from prisoners_gambit.core.models import Agent
from prisoners_gambit.systems.evolution import EvolutionEngine
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import (
    PowerupOfferContext,
    derive_doctrine_state,
    generate_powerup_offer_set,
    offer_category_hint,
    seed_run_house_doctrine,
)
from prisoners_gambit.systems.population import create_population
from prisoners_gambit.systems.progression import ProgressionEngine
from prisoners_gambit.systems.tournament import TournamentEngine
from prisoners_gambit.ui.renderers import Renderer

logger = logging.getLogger(__name__)


class RunApplication:
    def __init__(
        self,
        settings: Settings,
        renderer: Renderer,
        event_bus: EventBus,
        tournament: TournamentEngine,
        evolution: EvolutionEngine,
        progression: ProgressionEngine,
    ) -> None:
        self.settings = settings
        self.renderer = renderer
        self.event_bus = event_bus
        self.tournament = tournament
        self.evolution = evolution
        self.progression = progression
        self.interaction_controller = InteractionController(renderer=renderer)
        self.tournament.interaction_controller = self.interaction_controller

    def _doctrine_state_framing(self, *, house: str | None, primary: str | None, secondary: str | None) -> tuple[str, str]:
        if not primary:
            return ("Doctrine status: unresolved", "Lineage doctrine has not stabilized yet.")
        if house is None or house == primary:
            if secondary:
                return (
                    f"Doctrine status: {primary} house with {secondary} hybrid wing",
                    f"Mutation pressure rises as {secondary} influence enters a {primary} house.",
                )
            return (f"Doctrine status: {primary} house holding", "Civil-war pressure favors doctrine continuity over fracture.")
        if secondary:
            return (
                f"Doctrine status: mutated from {house} to {primary} (hybrid {secondary})",
                f"Doctrine fracture risk is rising: {house} inheritance clashes with {primary}/{secondary} lines.",
            )
        return (
            f"Doctrine status: mutated from {house} to {primary}",
            f"Civil-war pressure rises as house {house} is displaced by {primary} doctrine.",
        )

    def run(self) -> Agent:
        """Execute the deterministic run loop as repeated heir-shaping floor cycles.

        Each floor is intended to:
        - reveal the current field through tournament outcomes,
        - pressure lineage survival and succession choices,
        - commit branch direction via limited offers,
        - and seed the next floor's future civil-war threats.
        """
        population = create_population(self.settings.population_size, self.progression.rng)
        player = next(agent for agent in population if agent.is_player)
        player_lineage_id = player.lineage_id

        self.interaction_controller.show_run_header(self.settings.seed)
        self.interaction_controller.set_civil_war_context(None)
        self.event_bus.publish(Event("run_started", {"seed": self.settings.seed, "player": player.name}))
        logger.info("Run started | seed=%s | player=%s | lineage_id=%s", self.settings.seed, player.name, player_lineage_id)

        floor_number = 0
        ecosystem_phase = True
        house_doctrine = seed_run_house_doctrine(seed=self.settings.seed)

        while True:
            floor_number += 1
            floor_config = self.progression.build_floor_config(floor_number)
            self.interaction_controller.set_floor_context(
                floor_number=floor_number,
                phase="ecosystem" if ecosystem_phase else "civil_war",
            )

            logger.info("Starting floor %s | ecosystem_phase=%s", floor_number, ecosystem_phase)
            logger.debug("Floor config: %s", floor_config)

            ranked = self.tournament.run_floor(
                population=population,
                floor_number=floor_number,
                floor_config=floor_config,
                phase="ecosystem" if ecosystem_phase else "civil_war",
            )
            clue_reader = getattr(self.tournament, "consume_last_floor_clue_log", None)
            floor_clue_log = clue_reader() if callable(clue_reader) else []
            self.interaction_controller.set_floor_summary(
                floor_number,
                ranked,
                floor_clue_log=floor_clue_log,
            )
            self.renderer.show_floor_summary(floor_number, ranked)
            show_featured_summary = getattr(self.renderer, "show_floor_featured_inference_summary", None)
            featured_summary = self.interaction_controller.snapshot.floor_summary.featured_inference_summary
            if callable(show_featured_summary):
                show_featured_summary(featured_summary)

            if ecosystem_phase:
                survivors, eliminated = self.evolution.split_population(ranked)
            else:
                survivors, eliminated = self.evolution.split_population_civil_war(ranked)

            self.event_bus.publish(
                Event(
                    "survivors_selected",
                    {
                        "floor": floor_number,
                        "survivors": [agent.name for agent in survivors],
                        "eliminated": [agent.name for agent in eliminated],
                        "ecosystem_phase": ecosystem_phase,
                    },
                )
            )

            surviving_lineage = [
                agent for agent in survivors
                if agent.lineage_id == player_lineage_id
            ]

            if not surviving_lineage:
                logger.info("Entire player lineage eliminated on floor %s", floor_number)
                self.event_bus.publish(
                    Event(
                        "player_lineage_eliminated",
                        {"floor": floor_number, "lineage_id": player_lineage_id},
                    )
                )
                self.interaction_controller.complete_run(
                    outcome="eliminated",
                    floor_number=floor_number,
                    player_name=player.name,
                    seed=self.settings.seed,
                )
                self.renderer.show_elimination(floor_number, self.settings.seed)
                return player

            if player not in surviving_lineage:
                logger.info(
                    "Current host eliminated on floor %s, but lineage survives | successors=%s",
                    floor_number,
                    [agent.name for agent in surviving_lineage],
                )
                successor = self.interaction_controller.choose_successor(floor_number, surviving_lineage)
                successor.is_player = True
                player.is_player = False
                player = successor

                self.event_bus.publish(
                    Event(
                        "player_successor_selected",
                        {
                            "floor": floor_number,
                            "successor": player.name,
                            "lineage_id": player_lineage_id,
                        },
                    )
                )
                self.renderer.show_successor_selected(player)

            doctrine_state = derive_doctrine_state(
                owned_powerups=tuple(player.powerups),
                genome=player.genome,
                house_doctrine_family=house_doctrine,
            )
            doctrine_chip, doctrine_pressure_note = self._doctrine_state_framing(
                house=house_doctrine,
                primary=doctrine_state.primary_doctrine_family,
                secondary=doctrine_state.secondary_doctrine_family,
            )

            outsiders_remaining = [
                agent for agent in survivors
                if agent.lineage_id != player_lineage_id
            ]

            if ecosystem_phase and not outsiders_remaining:
                ecosystem_phase = False
                population = list(surviving_lineage)

                civil_war_context = build_civil_war_context(
                    branches=population,
                    current_host=player,
                    featured_inference_signals=normalize_featured_inference_signals(floor_clue_log),
                )
                civil_war_context.doctrine_pressure = [doctrine_pressure_note, *civil_war_context.doctrine_pressure][:4]
                self.interaction_controller.clear_floor_vote_result()
                self.interaction_controller.set_civil_war_context(civil_war_context)

                self.event_bus.publish(
                    Event(
                        "civil_war_started",
                        {
                            "floor": floor_number,
                            "lineage_members": [agent.name for agent in population],
                            "civil_war_context": {
                                "thesis": civil_war_context.thesis,
                                "scoring_rules": civil_war_context.scoring_rules,
                                "dangerous_branches": civil_war_context.dangerous_branches,
                                "doctrine_pressure": civil_war_context.doctrine_pressure,
                            },
                        },
                    )
                )
                self.renderer.show_phase_transition(
                    "Lineage Judgment: Civil War",
                    "\n".join([
                        civil_war_context.thesis,
                        "What is being tested now:",
                        *[f"- {rule}" for rule in civil_war_context.scoring_rules[:3]],
                        "Danger lanes: " + (", ".join(civil_war_context.dangerous_branches) or "unknown"),
                    ]),
                )

                if len(population) == 1:
                    logger.info("Single lineage member remained immediately after ecosystem collapse.")
                    self.event_bus.publish(
                        Event(
                            "run_completed",
                            {"final_floor": floor_number, "player": player.name, "seed": self.settings.seed},
                        )
                    )
                    self.interaction_controller.complete_run(
                        outcome="victory",
                        floor_number=floor_number,
                        player_name=player.name,
                        seed=self.settings.seed,
                    )
                    self.renderer.show_victory(floor_number, player, self.settings.seed)
                    return player

            phase = ("ecosystem" if ecosystem_phase else "civil_war")
            generated_powerup_offers = generate_powerup_offer_set(
                self.settings.offers_per_floor,
                self.progression.rng,
                context=PowerupOfferContext(
                    owned_powerups=tuple(player.powerups),
                    genome=player.genome,
                    floor_number=floor_number,
                    phase=phase,
                    house_doctrine_family=house_doctrine,
                    primary_doctrine_family=doctrine_state.primary_doctrine_family,
                    secondary_doctrine_family=doctrine_state.secondary_doctrine_family,
                ),
            )
            powerup_offers = [entry.powerup for entry in generated_powerup_offers]
            self.event_bus.publish(
                Event(
                    "powerups_offered",
                    {"floor": floor_number, "offers": [offer.name for offer in powerup_offers], "doctrine": doctrine_chip},
                )
            )

            selected_powerup = self.interaction_controller.choose_powerup(
                floor_number,
                powerup_offers,
                offer_hints={entry.powerup.name: offer_category_hint(entry.category) for entry in generated_powerup_offers},
            )
            player.powerups.append(selected_powerup)
            logger.info("Player selected powerup '%s' on floor %s", selected_powerup.name, floor_number)
            self.event_bus.publish(
                Event(
                    "powerup_selected",
                    {"floor": floor_number, "player": player.name, "powerup": selected_powerup.name},
                )
            )

            genome_edit_offers = generate_genome_edit_offers(
                self.settings.genome_edit_offers_per_floor,
                self.progression.rng,
            )
            selected_edit = self.interaction_controller.choose_genome_edit(
                floor_number=floor_number,
                current_summary=player.genome.summary(),
                offers=genome_edit_offers,
            )
            player.genome = selected_edit.apply(player.genome)
            self.renderer.show_genome_edit_applied(selected_edit, player.genome.summary())
            logger.info("Player selected genome edit '%s' on floor %s", selected_edit.name, floor_number)
            self.event_bus.publish(
                Event(
                    "genome_edit_selected",
                    {"floor": floor_number, "player": player.name, "edit": selected_edit.name},
                )
            )

            self.progression.grant_ai_powerups(
                survivors=survivors,
                player=player,
                floor_config=floor_config,
            )

            if ecosystem_phase:
                population = self.evolution.repopulate(
                    survivors=survivors,
                    target_size=self.settings.population_size,
                )
            else:
                population = list(surviving_lineage)
                if len(population) == 1:
                    logger.info("Civil war complete | final_floor=%s | winner=%s | seed=%s", floor_number, player.name, self.settings.seed)
                    self.event_bus.publish(
                        Event(
                            "run_completed",
                            {"final_floor": floor_number, "player": player.name, "seed": self.settings.seed},
                        )
                    )
                    self.interaction_controller.complete_run(
                        outcome="victory",
                        floor_number=floor_number,
                        player_name=player.name,
                        seed=self.settings.seed,
                    )
                    self.renderer.show_victory(floor_number, player, self.settings.seed)
                    return player

            if ecosystem_phase and floor_number >= self.settings.floors:
                logger.info("Configured floor cap reached before civil war resolution | floor=%s", floor_number)
                self.event_bus.publish(
                    Event(
                        "run_completed",
                        {
                            "final_floor": floor_number,
                            "player": player.name,
                            "seed": self.settings.seed,
                            "outcome": "capped",
                            "reason": "ecosystem_floor_cap_before_civil_war",
                        },
                    )
                )
                self.interaction_controller.complete_run(
                    outcome="capped",
                    floor_number=floor_number,
                    player_name=player.name,
                    seed=self.settings.seed,
                )
                self.renderer.show_phase_transition(
                    "Floor Cap Reached",
                    "The configured ecosystem floor cap ended the run before civil-war resolution.",
                )
                return player
