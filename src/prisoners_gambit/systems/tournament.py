from __future__ import annotations

from dataclasses import dataclass
import logging
import random

from prisoners_gambit.core.analysis import analyze_agent_identity
from prisoners_gambit.app.interaction_controller import InteractionController
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.events import Event, EventBus
from prisoners_gambit.core.interaction import (
    FeaturedMatchPrompt,
    FeaturedRoundDecisionState,
    FeaturedRoundResult,
    FloorVoteDecisionState,
    FloorVotePrompt,
    FloorVoteResult,
    RosterEntry,
    RoundDirectiveResolution,
    RoundResolutionBreakdown,
    ScoreAdjustment,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import (
    MoveDirective,
    ReferendumContext,
    RoundContext,
    resolve_move,
)
from prisoners_gambit.core.scoring import base_payoff
from prisoners_gambit.systems.progression import FloorConfig
from prisoners_gambit.ui.renderers import Renderer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MatchResult:
    left_score: int
    right_score: int


class TournamentEngine:
    def __init__(
        self,
        base_rounds_per_match: int,
        rng: random.Random,
        renderer: Renderer | None = None,
        interaction_controller: InteractionController | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.base_rounds_per_match = base_rounds_per_match
        self.rng = rng
        self.renderer = renderer
        self.interaction_controller = interaction_controller
        self.event_bus = event_bus

    def run_floor(
        self,
        population: list[Agent],
        floor_number: int,
        floor_config: FloorConfig,
    ) -> list[Agent]:
        logger.info(
            "Running floor | floor=%s | label=%s | population=%s | rounds_per_match=%s",
            floor_number,
            floor_config.label,
            len(population),
            floor_config.rounds_per_match,
        )

        for agent in population:
            agent.reset_for_floor()

        player = next((agent for agent in population if agent.is_player), None)

        roster_entries = self._build_roster_entries(population)
        if player and self.renderer:
            self.renderer.show_floor_roster(floor_number, roster_entries)

        featured_opponents: list[Agent] = []
        if player:
            candidates = [agent for agent in population if agent is not player]
            featured_opponents = self.rng.sample(
                candidates,
                k=min(floor_config.featured_matches, len(candidates)),
            )

        featured_ids = {agent.agent_id for agent in featured_opponents}

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    "floor_started",
                    {
                        "floor": floor_number,
                        "label": floor_config.label,
                        "population": len(population),
                        "rounds_per_match": floor_config.rounds_per_match,
                        "featured_matches": len(featured_opponents),
                        "referendum_reward": floor_config.referendum_reward,
                    },
                )
            )

        featured_counter = 1

        for left_index in range(len(population)):
            for right_index in range(left_index + 1, len(population)):
                left_agent = population[left_index]
                right_agent = population[right_index]

                if left_agent.is_player and right_agent.agent_id in featured_ids:
                    player_score, opponent_score = self.play_featured_player_match(
                        player=left_agent,
                        opponent=right_agent,
                        rounds_per_match=floor_config.rounds_per_match,
                        floor_number=floor_number,
                        roster_entries=roster_entries,
                        masked_opponent_label=f"Unknown Opponent {featured_counter}",
                    )
                    featured_counter += 1
                    left_agent.score += player_score
                    right_agent.score += opponent_score
                    if player_score > opponent_score:
                        left_agent.wins += 1
                    elif opponent_score > player_score:
                        right_agent.wins += 1
                    continue

                if right_agent.is_player and left_agent.agent_id in featured_ids:
                    player_score, opponent_score = self.play_featured_player_match(
                        player=right_agent,
                        opponent=left_agent,
                        rounds_per_match=floor_config.rounds_per_match,
                        floor_number=floor_number,
                        roster_entries=roster_entries,
                        masked_opponent_label=f"Unknown Opponent {featured_counter}",
                    )
                    featured_counter += 1
                    right_agent.score += player_score
                    left_agent.score += opponent_score
                    if player_score > opponent_score:
                        right_agent.wins += 1
                    elif opponent_score > player_score:
                        left_agent.wins += 1
                    continue

                result = self.play_match(
                    left=left_agent,
                    right=right_agent,
                    rounds_per_match=floor_config.rounds_per_match,
                )

                left_agent.score += result.left_score
                right_agent.score += result.right_score

                if result.left_score > result.right_score:
                    left_agent.wins += 1
                elif result.right_score > result.left_score:
                    right_agent.wins += 1

        self._run_floor_referendum(
            population=population,
            floor_number=floor_number,
            floor_config=floor_config,
        )

        ranked = sorted(
            population,
            key=lambda agent: (agent.score, agent.wins),
            reverse=True,
        )

        if self.event_bus and ranked:
            self.event_bus.publish(
                Event(
                    "floor_completed",
                    {
                        "floor": floor_number,
                        "label": floor_config.label,
                        "top_agent": ranked[0].name,
                        "top_score": ranked[0].score,
                    },
                )
            )

        logger.info(
            "Floor complete | floor=%s | leader=%s | leader_score=%s",
            floor_number,
            ranked[0].name if ranked else "n/a",
            ranked[0].score if ranked else "n/a",
        )

        return ranked

    def play_match(
        self,
        left: Agent,
        right: Agent,
        rounds_per_match: int | None = None,
    ) -> MatchResult:
        rounds = rounds_per_match if rounds_per_match is not None else self.base_rounds_per_match

        left_history: list[int] = []
        right_history: list[int] = []
        left_score = 0
        right_score = 0

        for round_index in range(rounds):
            left_plan = left.genome.choose_move(left_history, right_history, self.rng)
            right_plan = right.genome.choose_move(right_history, left_history, self.rng)

            left_context = RoundContext(
                round_index=round_index,
                total_rounds=rounds,
                my_history=list(left_history),
                opp_history=list(right_history),
                planned_move=left_plan,
                opp_planned_move=right_plan,
            )
            right_context = RoundContext(
                round_index=round_index,
                total_rounds=rounds,
                my_history=list(right_history),
                opp_history=list(left_history),
                planned_move=right_plan,
                opp_planned_move=left_plan,
            )

            left_move, _ = self._resolve_agent_move(
                owner=left,
                opponent=right,
                owner_context=left_context,
                opponent_context=right_context,
                base_move=left_plan,
            )
            right_move, _ = self._resolve_agent_move(
                owner=right,
                opponent=left,
                owner_context=right_context,
                opponent_context=left_context,
                base_move=right_plan,
            )

            round_left_points, round_right_points = base_payoff(left_move, right_move)

            round_left_points, round_right_points = self._apply_score_powerups(
                owner=left,
                opponent=right,
                my_move=left_move,
                opp_move=right_move,
                my_points=round_left_points,
                opp_points=round_right_points,
                context=left_context,
            )

            round_right_points, round_left_points = self._apply_score_powerups(
                owner=right,
                opponent=left,
                my_move=right_move,
                opp_move=left_move,
                my_points=round_right_points,
                opp_points=round_left_points,
                context=right_context,
            )

            left_score += round_left_points
            right_score += round_right_points

            left_history.append(left_move)
            right_history.append(right_move)

        return MatchResult(left_score=left_score, right_score=right_score)

    def play_featured_player_match(
        self,
        player: Agent,
        opponent: Agent,
        rounds_per_match: int,
        floor_number: int,
        roster_entries: list[RosterEntry],
        masked_opponent_label: str,
    ) -> tuple[int, int]:
        player_history: list[int] = []
        opponent_history: list[int] = []
        player_score = 0
        opponent_score = 0

        for round_index in range(rounds_per_match):
            suggested_move = player.genome.choose_move(player_history, opponent_history, self.rng)
            opponent_plan = opponent.genome.choose_move(opponent_history, player_history, self.rng)

            prompt = FeaturedMatchPrompt(
                floor_number=floor_number,
                masked_opponent_label=masked_opponent_label,
                round_index=round_index,
                total_rounds=rounds_per_match,
                my_history=list(player_history),
                opp_history=list(opponent_history),
                my_match_score=player_score,
                opp_match_score=opponent_score,
                suggested_move=suggested_move,
                roster_entries=roster_entries,
            )

            if self.interaction_controller:
                if self.interaction_controller.should_autopilot_featured_match:
                    player_plan = suggested_move
                else:
                    player_plan = self.interaction_controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))
            else:
                player_plan = self.renderer.choose_round_action(prompt) if self.renderer else suggested_move

            player_context = RoundContext(
                round_index=round_index,
                total_rounds=rounds_per_match,
                my_history=list(player_history),
                opp_history=list(opponent_history),
                planned_move=player_plan,
                opp_planned_move=opponent_plan,
            )
            opponent_context = RoundContext(
                round_index=round_index,
                total_rounds=rounds_per_match,
                my_history=list(opponent_history),
                opp_history=list(player_history),
                planned_move=opponent_plan,
                opp_planned_move=player_plan,
            )

            player_move, player_directive_resolution = self._resolve_agent_move(
                owner=player,
                opponent=opponent,
                owner_context=player_context,
                opponent_context=opponent_context,
                base_move=player_plan,
            )
            opponent_move, opponent_directive_resolution = self._resolve_agent_move(
                owner=opponent,
                opponent=player,
                owner_context=opponent_context,
                opponent_context=player_context,
                base_move=opponent_plan,
            )

            base_player_points, base_opponent_points = base_payoff(player_move, opponent_move)
            round_player_points, round_opponent_points = base_player_points, base_opponent_points

            score_adjustments: list[ScoreAdjustment] = []

            round_player_points, round_opponent_points = self._apply_score_powerups(
                owner=player,
                opponent=opponent,
                my_move=player_move,
                opp_move=opponent_move,
                my_points=round_player_points,
                opp_points=round_opponent_points,
                context=player_context,
                perspective="player",
                score_adjustments=score_adjustments,
            )

            round_opponent_points, round_player_points = self._apply_score_powerups(
                owner=opponent,
                opponent=player,
                my_move=opponent_move,
                opp_move=player_move,
                my_points=round_opponent_points,
                opp_points=round_player_points,
                context=opponent_context,
                perspective="opponent",
                score_adjustments=score_adjustments,
            )

            player_score += round_player_points
            opponent_score += round_opponent_points

            player_history.append(player_move)
            opponent_history.append(opponent_move)

            if self.renderer:
                round_result = FeaturedRoundResult(
                    masked_opponent_label=masked_opponent_label,
                    round_index=round_index,
                    total_rounds=rounds_per_match,
                    player_move=player_move,
                    opponent_move=opponent_move,
                    player_delta=round_player_points,
                    opponent_delta=round_opponent_points,
                    player_total=player_score,
                    opponent_total=opponent_score,
                    player_reason=player_directive_resolution.reason,
                    opponent_reason=opponent_directive_resolution.reason,
                    breakdown=RoundResolutionBreakdown(
                        player_plan=player_plan,
                        opponent_plan=opponent_plan,
                        player_directives=player_directive_resolution,
                        opponent_directives=opponent_directive_resolution,
                        base_player_points=base_player_points,
                        base_opponent_points=base_opponent_points,
                        score_adjustments=score_adjustments,
                        final_player_points=round_player_points,
                        final_opponent_points=round_opponent_points,
                    ),
                )
                self.renderer.show_round_result(round_result)
                if self.interaction_controller:
                    self.interaction_controller.set_latest_round_result(round_result)

        if self.interaction_controller:
            self.interaction_controller.reset_featured_match_autopilot()

        return player_score, opponent_score

    def _run_floor_referendum(
        self,
        population: list[Agent],
        floor_number: int,
        floor_config: FloorConfig,
    ) -> None:
        votes: dict[int, int] = {}
        player = next((agent for agent in population if agent.is_player), None)

        for agent in population:
            suggested_vote = agent.genome.first_move
            context = ReferendumContext(
                floor_number=floor_number,
                total_agents=len(population),
                current_floor_score=agent.score,
            )

            if agent.is_player and self.renderer:
                prompt = FloorVotePrompt(
                    floor_number=floor_number,
                    floor_label=floor_config.label,
                    suggested_vote=suggested_vote,
                    current_floor_score=agent.score,
                    powerups=[powerup.name for powerup in agent.powerups],
                )
                if self.interaction_controller:
                    base_vote = self.interaction_controller.choose_floor_vote(FloorVoteDecisionState(prompt=prompt))
                else:
                    base_vote = self.renderer.choose_floor_vote(prompt)
            else:
                base_vote = suggested_vote

            directives: list[MoveDirective] = []
            for powerup in agent.powerups:
                directives.extend(powerup.self_referendum_directives(owner=agent, context=context))

            final_vote, _ = resolve_move(base_vote, directives)
            votes[agent.agent_id] = final_vote

        cooperators = sum(1 for vote in votes.values() if vote == COOPERATE)
        defectors = sum(1 for vote in votes.values() if vote == DEFECT)
        cooperation_prevailed = cooperators >= defectors

        if cooperation_prevailed:
            for agent in population:
                if votes[agent.agent_id] == COOPERATE:
                    reward = floor_config.referendum_reward
                    context = ReferendumContext(
                        floor_number=floor_number,
                        total_agents=len(population),
                        current_floor_score=agent.score,
                    )
                    for powerup in agent.powerups:
                        reward = powerup.on_referendum_reward(
                            owner=agent,
                            my_vote=COOPERATE,
                            cooperation_prevailed=True,
                            current_reward=reward,
                            context=context,
                        )
                    agent.score += reward
        else:
            reward = 0

        if player and self.renderer:
            player_vote = votes[player.agent_id]
            player_reward = 0
            if cooperation_prevailed and player_vote == COOPERATE:
                player_reward = floor_config.referendum_reward
                context = ReferendumContext(
                    floor_number=floor_number,
                    total_agents=len(population),
                    current_floor_score=player.score,
                )
                for powerup in player.powerups:
                    player_reward = powerup.on_referendum_reward(
                        owner=player,
                        my_vote=player_vote,
                        cooperation_prevailed=True,
                        current_reward=player_reward,
                        context=context,
                    )

            self.renderer.show_referendum_result(
                FloorVoteResult(
                    floor_number=floor_number,
                    cooperation_prevailed=cooperation_prevailed,
                    cooperators=cooperators,
                    defectors=defectors,
                    player_vote=player_vote,
                    player_reward=player_reward if cooperation_prevailed and player_vote == COOPERATE else 0,
                )
            )

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    "floor_referendum_resolved",
                    {
                        "floor": floor_number,
                        "cooperators": cooperators,
                        "defectors": defectors,
                        "cooperation_prevailed": cooperation_prevailed,
                    },
                )
            )

    def _build_roster_entries(self, population: list[Agent]) -> list[RosterEntry]:
        entries: list[RosterEntry] = []

        for agent in population:
            if agent.is_player:
                continue

            identity = analyze_agent_identity(agent)
            entries.append(
                RosterEntry(
                    name=agent.name,
                    public_profile=agent.public_profile,
                    known_powerups=[powerup.name for powerup in agent.powerups],
                    tags=identity.tags,
                    descriptor=identity.descriptor,
                )
            )

        return entries

    def _resolve_agent_move(
        self,
        owner: Agent,
        opponent: Agent,
        owner_context: RoundContext,
        opponent_context: RoundContext,
        base_move: int,
    ) -> tuple[int, RoundDirectiveResolution]:
        directives: list[MoveDirective] = []

        for powerup in owner.powerups:
            directives.extend(
                powerup.self_move_directives(
                    owner=owner,
                    opponent=opponent,
                    context=owner_context,
                )
            )

        for powerup in opponent.powerups:
            directives.extend(
                powerup.opponent_move_directives(
                    owner=opponent,
                    opponent=owner,
                    context=opponent_context,
                )
            )

        resolved_move, reason = resolve_move(base_move, directives)
        return resolved_move, RoundDirectiveResolution(
            base_move=base_move,
            final_move=resolved_move,
            reason=reason,
            directives=directives,
        )

    def _apply_score_powerups(
        self,
        owner: Agent,
        opponent: Agent,
        my_move: int,
        opp_move: int,
        my_points: int,
        opp_points: int,
        context: RoundContext,
        perspective: str | None = None,
        score_adjustments: list[ScoreAdjustment] | None = None,
    ) -> tuple[int, int]:
        adjusted_my_points = my_points
        adjusted_opp_points = opp_points

        for powerup in owner.powerups:
            previous_my_points = adjusted_my_points
            previous_opp_points = adjusted_opp_points
            adjusted_my_points, adjusted_opp_points = powerup.on_score(
                owner=owner,
                opponent=opponent,
                my_move=my_move,
                opp_move=opp_move,
                my_points=adjusted_my_points,
                opp_points=adjusted_opp_points,
                context=context,
            )

            if score_adjustments is not None:
                my_delta = adjusted_my_points - previous_my_points
                opp_delta = adjusted_opp_points - previous_opp_points
                if my_delta or opp_delta:
                    player_delta, opponent_delta = my_delta, opp_delta
                    if perspective == "opponent":
                        player_delta, opponent_delta = opp_delta, my_delta
                    score_adjustments.append(
                        ScoreAdjustment(
                            source=powerup.name,
                            player_delta=player_delta,
                            opponent_delta=opponent_delta,
                        )
                    )

        return adjusted_my_points, adjusted_opp_points
