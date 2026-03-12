from __future__ import annotations

from dataclasses import asdict
import random

from prisoners_gambit.app.heir_view_mapping import to_floor_summary_heir_pressure_view, to_successor_candidate_view
from prisoners_gambit.app.interaction_controller import RunSession
from prisoners_gambit.core.analysis import analyze_agent_identity, analyze_floor_heir_pressure, assess_successor_candidate
from prisoners_gambit.core.civil_war import build_civil_war_context
from prisoners_gambit.core.featured_inference import (
    normalize_featured_inference_signals,
    successor_featured_inference_context,
    summarize_featured_inference_signals,
)
from prisoners_gambit.core.successor_analysis import civil_war_pressure_for_threat_tags
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
    FeaturedMatchPrompt,
    FeaturedRoundDecisionState,
    FeaturedRoundResult,
    FeaturedRoundStanceView,
    FloorSummaryEntryView,
    FloorSummaryState,
    FloorVoteDecisionState,
    FloorVotePrompt,
    FloorVoteResult,
    GenomeEditChoiceState,
    GenomeEditOfferView,
    PowerupChoiceState,
    PowerupOfferView,
    RoundDirectiveResolution,
    RoundResolutionBreakdown,
    RunCompletion,
    RunSnapshot,
    ScoreAdjustment,
    SuccessorCandidateView,
    SuccessorChoiceState,
    validated_stance_rounds,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.offer_views import to_genome_edit_offer_view, to_powerup_offer_view
from prisoners_gambit.core.powerups import ComplianceDividend, CounterIntel, MoveDirective, RoundContext, resolve_move
from prisoners_gambit.core.scoring import base_payoff
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import generate_powerup_offers


class FeaturedMatchWebSession:
    def __init__(self, seed: int = 7, rounds: int = 3) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.rounds = rounds
        self.session = RunSession()
        self.snapshot = RunSnapshot()
        self.player = Agent(name="You", genome=self._default_genome(), is_player=True, lineage_id=1)
        self.opponent = Agent(name="Unknown Opponent", genome=self._opponent_genome())
        self.player.powerups.append(ComplianceDividend())
        self.opponent.powerups.append(CounterIntel())
        self.player_history: list[int] = []
        self.opponent_history: list[int] = []
        self.player_score = 0
        self.opponent_score = 0
        self.round_index = 0
        self.floor_number = 1
        self._last_manual_move: int | None = None
        self._active_stance: FeaturedRoundStanceView | None = None
        self._match_autopilot_active = False
        self._pending_screen: str | None = None
        self._pending_message: str | None = None
        self._powerup_offers = []
        self._genome_offers = []
        self._successor_candidates: list[Agent] = []
        self._floor_clue_log: list[str] = []

    def start(self) -> None:
        self.session.start(self.snapshot)
        self.snapshot.header = self.snapshot.header or None
        self.snapshot.current_floor = self.floor_number
        self.snapshot.current_phase = "ecosystem"
        self._floor_clue_log = []
        self._begin_featured_round_decision()

    def submit_action(
        self,
        action: (
            ChooseRoundMoveAction
            | ChooseRoundAutopilotAction
            | ChooseRoundStanceAction
            | ChooseFloorVoteAction
            | ChoosePowerupAction
            | ChooseGenomeEditAction
            | ChooseSuccessorAction
        ),
    ) -> None:
        self.session.submit_action(action)

    def advance(self) -> None:
        if self.session.status == "completed":
            return

        if self._pending_screen is not None:
            self._pending_screen = None
            self._pending_message = None
            self._begin_post_summary_flow()
            return

        if self.session.status != "awaiting_decision" or self.session.current_decision is None:
            return

        decision = self.session.current_decision
        if isinstance(decision, FeaturedRoundDecisionState):
            self._resolve_featured_round(decision)
            return
        if isinstance(decision, FloorVoteDecisionState):
            self._resolve_floor_vote(decision)
            return
        if isinstance(decision, PowerupChoiceState):
            self._resolve_powerup_choice(decision)
            return
        if isinstance(decision, GenomeEditChoiceState):
            self._resolve_genome_choice(decision)
            return
        if isinstance(decision, SuccessorChoiceState):
            self._resolve_successor_choice(decision)
            return

    def view(self) -> dict:
        return {
            "status": self.session.status,
            "decision_type": type(self.session.current_decision).__name__ if self.session.current_decision else None,
            "decision": asdict(self.session.current_decision) if self.session.current_decision else None,
            "snapshot": asdict(self.snapshot),
            "pending_screen": self._pending_screen,
            "pending_message": self._pending_message,
        }

    @property
    def should_autopilot_featured_match(self) -> bool:
        return self._match_autopilot_active

    def _begin_featured_round_decision(self) -> None:
        suggested_move = self.player.genome.choose_move(self.player_history, self.opponent_history, self.rng)
        state = FeaturedRoundDecisionState(
            prompt=FeaturedMatchPrompt(
                floor_number=self.floor_number,
                masked_opponent_label="Unknown Opponent",
                round_index=self.round_index,
                total_rounds=self.rounds,
                my_history=list(self.player_history),
                opp_history=list(self.opponent_history),
                my_match_score=self.player_score,
                opp_match_score=self.opponent_score,
                suggested_move=suggested_move,
                roster_entries=[],
                clue_channels=[
                    f"Profile signal: {self.opponent.public_profile}",
                    f"Known powerups: {', '.join(powerup.name for powerup in self.opponent.powerups) if self.opponent.powerups else 'none'}",
                    "Move-pattern signal: compare opening and retaliation cadence.",
                ],
                floor_clue_log=list(self._floor_clue_log),
                inference_focus=(
                    "Opening read: stress-test profile clues."
                    if self.round_index == 0
                    else "Pattern read: update tag confidence from response behavior."
                ),
            )
        )
        if self._active_stance is not None:
            self.session.begin_decision(
                state,
                (ChooseRoundMoveAction, ChooseRoundAutopilotAction, ChooseRoundStanceAction),
                self.snapshot,
            )
            self.session.submit_action(
                ChooseRoundStanceAction(
                    mode="set_round_stance",
                    stance=self._active_stance.stance,
                    rounds=self._active_stance.rounds_remaining,
                )
            )
        else:
            self.session.begin_decision(
                state,
                (ChooseRoundMoveAction, ChooseRoundAutopilotAction, ChooseRoundStanceAction),
                self.snapshot,
            )
        self.snapshot.session_status = "awaiting_decision"

    def _resolve_featured_round(self, decision: FeaturedRoundDecisionState) -> None:
        action = self.session.resolve_current_decision(self._default_featured_round_action)
        if isinstance(action, ChooseRoundMoveAction):
            self._match_autopilot_active = False
            self._last_manual_move = action.move
            self._active_stance = None
            self.snapshot.active_featured_stance = None
            player_plan = action.move
        elif isinstance(action, ChooseRoundStanceAction):
            self._match_autopilot_active = False
            rounds = self._validated_stance_rounds(action)
            locked_move = self._last_manual_move if action.stance == "lock_last_manual_move_for_n_rounds" else None
            self._active_stance = FeaturedRoundStanceView(stance=action.stance, rounds_remaining=rounds, locked_move=locked_move)
            self.snapshot.active_featured_stance = self._active_stance
            player_plan = self._resolve_stance_move(decision.prompt)
        elif isinstance(action, ChooseRoundAutopilotAction):
            if action.mode == "autopilot_match":
                self._match_autopilot_active = True
                self._active_stance = None
                self.snapshot.active_featured_stance = None
            player_plan = self._resolve_stance_move(decision.prompt)
        else:
            raise ValueError(f"Unsupported featured round action type: {type(action).__name__}")

        opponent_plan = self.opponent.genome.choose_move(self.opponent_history, self.player_history, self.rng)
        player_context = RoundContext(
            round_index=self.round_index,
            total_rounds=self.rounds,
            my_history=list(self.player_history),
            opp_history=list(self.opponent_history),
            planned_move=player_plan,
            opp_planned_move=opponent_plan,
        )
        opponent_context = RoundContext(
            round_index=self.round_index,
            total_rounds=self.rounds,
            my_history=list(self.opponent_history),
            opp_history=list(self.player_history),
            planned_move=opponent_plan,
            opp_planned_move=player_plan,
        )

        player_move, player_res = self._resolve_move(self.player, self.opponent, player_context, opponent_context, player_plan)
        opponent_move, opp_res = self._resolve_move(self.opponent, self.player, opponent_context, player_context, opponent_plan)

        base_p, base_o = base_payoff(player_move, opponent_move)
        p_points, o_points = base_p, base_o
        adjustments: list[ScoreAdjustment] = []
        p_points, o_points = self._apply_score(self.player, self.opponent, player_move, opponent_move, p_points, o_points, player_context, "player", adjustments)
        o_points, p_points = self._apply_score(self.opponent, self.player, opponent_move, player_move, o_points, p_points, opponent_context, "opponent", adjustments)

        self.player_score += p_points
        self.opponent_score += o_points
        self.player_history.append(player_move)
        self.opponent_history.append(opponent_move)

        self.snapshot.latest_featured_round = FeaturedRoundResult(
            masked_opponent_label="Unknown Opponent",
            round_index=self.round_index,
            total_rounds=self.rounds,
            player_move=player_move,
            opponent_move=opponent_move,
            player_delta=p_points,
            opponent_delta=o_points,
            player_total=self.player_score,
            opponent_total=self.opponent_score,
            player_reason=player_res.reason,
            opponent_reason=opp_res.reason,
            inference_update=[
                (
                    "Opened cooperatively; cooperative tag read strengthened."
                    if self.round_index == 0 and opponent_move == COOPERATE
                    else "Opened aggressively; aggressive tag read strengthened."
                )
                if self.round_index == 0
                else (
                    "Retaliated after pressure; retaliatory read strengthened."
                    if self.player_history and self.player_history[-1] == DEFECT and opponent_move == DEFECT
                    else "Pattern remained mixed; keep branch read probabilistic."
                ),
                "Carry this clue into floor summary and successor threat interpretation.",
            ],
            breakdown=RoundResolutionBreakdown(
                player_plan=player_plan,
                opponent_plan=opponent_plan,
                player_directives=player_res,
                opponent_directives=opp_res,
                base_player_points=base_p,
                base_opponent_points=base_o,
                score_adjustments=adjustments,
                final_player_points=p_points,
                final_opponent_points=o_points,
            ),
        )
        self._floor_clue_log.extend(self.snapshot.latest_featured_round.inference_update)
        self.round_index += 1

        if self.round_index < self.rounds:
            self._begin_featured_round_decision()
            return

        vote_prompt = FloorVotePrompt(
            floor_number=self.floor_number,
            floor_label=f"Floor {self.floor_number}",
            suggested_vote=COOPERATE,
            current_floor_score=self.player_score,
            powerups=[p.name for p in self.player.powerups],
        )
        self.session.begin_decision(FloorVoteDecisionState(prompt=vote_prompt), (ChooseFloorVoteAction,), self.snapshot)
        self.snapshot.session_status = "awaiting_decision"

    def _resolve_floor_vote(self, decision: FloorVoteDecisionState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChooseFloorVoteAction(mode="autopilot_vote"))
        vote = decision.prompt.suggested_vote if action.mode == "autopilot_vote" else action.vote
        if vote not in (COOPERATE, DEFECT):
            raise ValueError("Invalid floor vote")

        result = FloorVoteResult(
            floor_number=self.floor_number,
            cooperation_prevailed=vote == COOPERATE,
            cooperators=6 if vote == COOPERATE else 3,
            defectors=2 if vote == COOPERATE else 5,
            player_vote=vote,
            player_reward=2 if vote == COOPERATE else 1,
        )
        self.snapshot.floor_vote_result = result
        self.player_score += result.player_reward

        summary_agents = self._mock_floor_ranking()
        entries: list[FloorSummaryEntryView] = []
        for agent in summary_agents:
            identity = analyze_agent_identity(agent)
            entries.append(
                FloorSummaryEntryView(
                    agent_id=agent.agent_id,
                    name=agent.name,
                    is_player=agent.is_player,
                    score=agent.score,
                    wins=agent.wins,
                    tags=identity.tags,
                    descriptor=identity.descriptor,
                    genome_summary=agent.genome.summary(),
                    powerups=[p.name for p in agent.powerups],
                )
            )
        pressure = analyze_floor_heir_pressure(summary_agents, self.player.lineage_id)
        heir_pressure = to_floor_summary_heir_pressure_view(pressure)
        self.snapshot.floor_summary = FloorSummaryState(
            floor_number=self.floor_number,
            entries=entries,
            heir_pressure=heir_pressure,
            featured_inference_summary=summarize_featured_inference_signals(
                normalize_featured_inference_signals(self._floor_clue_log)
            ),
        )
        self.snapshot.session_status = "running"
        self._pending_screen = "floor_summary"
        self._pending_message = f"Floor {self.floor_number} complete. Review standings, then continue."

    def _begin_post_summary_flow(self) -> None:
        if self.floor_number == 1:
            self._successor_candidates = self._build_successor_candidates()
            candidates = []
            top_score = max((agent.score for agent in self._successor_candidates), default=0)
            threat_tags: set[str] = set()
            lineage_doctrine: str | None = None
            if self.snapshot.floor_summary and self.snapshot.floor_summary.heir_pressure:
                lineage_doctrine = self.snapshot.floor_summary.heir_pressure.branch_doctrine
                for threat in self.snapshot.floor_summary.heir_pressure.future_threats:
                    threat_tags.update(threat.tags)
            for agent in self._successor_candidates:
                identity = analyze_agent_identity(agent)
                assessment = assess_successor_candidate(
                    agent,
                    top_score=top_score,
                    phase=self.snapshot.current_phase,
                    threat_tags=threat_tags,
                    lineage_doctrine=lineage_doctrine,
                )
                candidates.append(
                    to_successor_candidate_view(
                        agent=agent,
                        identity=identity,
                        assessment=assessment,
                        featured_inference_context=successor_featured_inference_context(
                            candidate_tags=identity.tags,
                            featured_inference_signals=normalize_featured_inference_signals(self._floor_clue_log),
                        ),
                    )
                )
            civil_war_pressure = civil_war_pressure_for_threat_tags(threat_tags)
            state = SuccessorChoiceState(
                floor_number=self.floor_number,
                candidates=candidates,
                current_phase=self.snapshot.current_phase,
                lineage_doctrine=lineage_doctrine,
                threat_profile=sorted(threat_tags),
                civil_war_pressure=civil_war_pressure,
                featured_inference_summary=(
                    list(self.snapshot.floor_summary.featured_inference_summary)
                    if self.snapshot.floor_summary
                    else []
                ),
            )
            self.snapshot.successor_options = state
            self.session.begin_decision(state, (ChooseSuccessorAction,), self.snapshot)
            self.snapshot.session_status = "awaiting_decision"
            return

        self._powerup_offers = generate_powerup_offers(3, self.rng)
        offers = [to_powerup_offer_view(offer) for offer in self._powerup_offers]
        state = PowerupChoiceState(floor_number=self.floor_number, offers=offers)
        self.session.begin_decision(state, (ChoosePowerupAction,), self.snapshot)
        self.snapshot.session_status = "awaiting_decision"

    def _resolve_successor_choice(self, decision: SuccessorChoiceState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChooseSuccessorAction(candidate_index=0))
        if action.candidate_index < 0 or action.candidate_index >= len(self._successor_candidates):
            raise ValueError("Invalid successor index")
        chosen = self._successor_candidates[action.candidate_index]
        chosen.is_player = True
        self.player.is_player = False
        self.player = chosen
        self.snapshot.current_phase = "civil_war"
        self.snapshot.floor_vote_result = None
        self.snapshot.civil_war_context = build_civil_war_context(branches=list(self._successor_candidates), current_host=chosen)
        self.floor_number = 2
        self.snapshot.current_floor = self.floor_number
        self._pending_screen = "civil_war_transition"
        self._pending_message = self.snapshot.civil_war_context.thesis
        self.snapshot.session_status = "running"

    def _resolve_powerup_choice(self, decision: PowerupChoiceState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChoosePowerupAction(offer_index=0))
        if action.offer_index < 0 or action.offer_index >= len(self._powerup_offers):
            raise ValueError("Invalid powerup index")
        self.player.powerups.append(self._powerup_offers[action.offer_index])

        self._genome_offers = generate_genome_edit_offers(3, self.rng)
        state = GenomeEditChoiceState(
            floor_number=self.floor_number,
            current_summary=self.player.genome.summary(),
            offers=[
                to_genome_edit_offer_view(
                    offer,
                    current_summary=self.player.genome.summary(),
                    projected_summary=offer.apply(self.player.genome).summary(),
                )
                for offer in self._genome_offers
            ],
        )
        self.session.begin_decision(state, (ChooseGenomeEditAction,), self.snapshot)
        self.snapshot.session_status = "awaiting_decision"

    def _resolve_genome_choice(self, decision: GenomeEditChoiceState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChooseGenomeEditAction(offer_index=0))
        if action.offer_index < 0 or action.offer_index >= len(self._genome_offers):
            raise ValueError("Invalid genome edit index")
        self.player.genome = self._genome_offers[action.offer_index].apply(self.player.genome)

        completion = RunCompletion(
            outcome="victory" if self.player_score >= self.opponent_score else "eliminated",
            floor_number=self.floor_number,
            player_name=self.player.name,
            seed=self.seed,
        )
        self.snapshot.completion = completion
        self.session.complete(completion, self.snapshot)
        self.snapshot.session_status = "completed"

    def _resolve_stance_move(self, prompt: FeaturedMatchPrompt) -> int:
        if self._active_stance is None:
            return prompt.suggested_move
        stance = self._active_stance.stance
        if stance == "cooperate_until_betrayed":
            return DEFECT if prompt.opp_history and prompt.opp_history[-1] == DEFECT else COOPERATE
        if stance == "defect_until_punished":
            return COOPERATE if prompt.opp_history and prompt.opp_history[-1] == DEFECT else DEFECT
        if stance == "follow_autopilot_for_n_rounds":
            move = prompt.suggested_move
            self._decrement_stance_rounds()
            return move
        if stance == "lock_last_manual_move_for_n_rounds":
            move = self._active_stance.locked_move if self._active_stance.locked_move is not None else prompt.suggested_move
            self._decrement_stance_rounds()
            return move
        return prompt.suggested_move

    def _decrement_stance_rounds(self) -> None:
        if self._active_stance is None or self._active_stance.rounds_remaining is None:
            return
        self._active_stance.rounds_remaining -= 1
        if self._active_stance.rounds_remaining <= 0:
            self._active_stance = None
        self.snapshot.active_featured_stance = self._active_stance

    def _validated_stance_rounds(self, action: ChooseRoundStanceAction) -> int | None:
        return validated_stance_rounds(action.stance, action.rounds)

    def _default_featured_round_action(self, _: FeaturedRoundDecisionState) -> ChooseRoundAutopilotAction:
        mode = "autopilot_match" if self._match_autopilot_active else "autopilot_round"
        return ChooseRoundAutopilotAction(mode=mode)

    def _resolve_move(
        self,
        owner: Agent,
        opponent: Agent,
        owner_context: RoundContext,
        opponent_context: RoundContext,
        base_move: int,
    ) -> tuple[int, RoundDirectiveResolution]:
        directives: list[MoveDirective] = []
        for powerup in owner.powerups:
            directives.extend(powerup.self_move_directives(owner=owner, opponent=opponent, context=owner_context))
        for powerup in opponent.powerups:
            directives.extend(powerup.opponent_move_directives(owner=opponent, opponent=owner, context=opponent_context))
        resolved, reason = resolve_move(base_move, directives)
        return resolved, RoundDirectiveResolution(base_move=base_move, final_move=resolved, reason=reason, directives=directives)

    def _apply_score(
        self,
        owner: Agent,
        opponent: Agent,
        my_move: int,
        opp_move: int,
        my_points: int,
        opp_points: int,
        context: RoundContext,
        perspective: str,
        adjustments: list[ScoreAdjustment],
    ) -> tuple[int, int]:
        adjusted_my, adjusted_opp = my_points, opp_points
        for powerup in owner.powerups:
            prev_my, prev_opp = adjusted_my, adjusted_opp
            adjusted_my, adjusted_opp = powerup.on_score(
                owner=owner,
                opponent=opponent,
                my_move=my_move,
                opp_move=opp_move,
                my_points=adjusted_my,
                opp_points=adjusted_opp,
                context=context,
            )
            my_delta = adjusted_my - prev_my
            opp_delta = adjusted_opp - prev_opp
            if my_delta or opp_delta:
                player_delta, opponent_delta = my_delta, opp_delta
                if perspective == "opponent":
                    player_delta, opponent_delta = opp_delta, my_delta
                adjustments.append(ScoreAdjustment(source=powerup.name, player_delta=player_delta, opponent_delta=opponent_delta))
        return adjusted_my, adjusted_opp

    def _mock_floor_ranking(self) -> list[Agent]:
        player_clone = Agent(name=self.player.name, genome=self.player.genome, is_player=True, score=self.player_score, wins=2, lineage_depth=self.player.lineage_depth)
        rival_a = Agent(name="Echo Branch", genome=self._opponent_genome(), score=self.player_score - 1, wins=2, lineage_depth=2)
        rival_b = Agent(name="Delta Branch", genome=self._default_genome(), score=self.player_score - 2, wins=1, lineage_depth=3)
        return [player_clone, rival_a, rival_b]

    def _build_successor_candidates(self) -> list[Agent]:
        candidate_a = Agent(name="Heir A", genome=self._default_genome(), score=self.player_score + 1, wins=2, lineage_depth=2)
        candidate_b = Agent(name="Heir B", genome=self._opponent_genome(), score=self.player_score, wins=1, lineage_depth=3)
        return [candidate_a, candidate_b]

    @staticmethod
    def _default_genome() -> StrategyGenome:
        return StrategyGenome(
            first_move=COOPERATE,
            response_table={
                (COOPERATE, COOPERATE): COOPERATE,
                (COOPERATE, DEFECT): DEFECT,
                (DEFECT, COOPERATE): COOPERATE,
                (DEFECT, DEFECT): DEFECT,
            },
            noise=0.0,
        )

    @staticmethod
    def _opponent_genome() -> StrategyGenome:
        return StrategyGenome(
            first_move=DEFECT,
            response_table={
                (COOPERATE, COOPERATE): DEFECT,
                (COOPERATE, DEFECT): DEFECT,
                (DEFECT, COOPERATE): COOPERATE,
                (DEFECT, DEFECT): DEFECT,
            },
            noise=0.0,
        )
