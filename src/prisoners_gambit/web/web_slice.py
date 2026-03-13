from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import hmac
import json
import random
import zlib
from typing import get_type_hints

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
    FloorIdentityState,
    DynastyBoardEntryView,
    DynastyBoardState,
    FloorVoteDecisionState,
    FloorVotePrompt,
    FloorVoteResult,
    GenomeEditChoiceState,
    GenomeEditOfferView,
    PowerupChoiceState,
    PowerupOfferView,
    RoundDirectiveResolution,
    RoundResolutionBreakdown,
    LineageChronicleEntry,
    RunCompletion,
    RunSnapshot,
    ScoreAdjustment,
    SuccessorCandidateView,
    SuccessorChoiceState,
    validated_stance_rounds,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.offer_views import to_genome_edit_offer_view, to_powerup_offer_view
from prisoners_gambit.core.powerups import (
    ALL_POWERUP_TYPES,
    ComplianceDividend,
    CounterIntel,
    MoveDirective,
    Powerup,
    RoundContext,
    resolve_move,
)
from prisoners_gambit.core.scoring import base_payoff
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import generate_powerup_offers


SAVE_STATE_VERSION = 1
_DECISION_TYPES = {
    "FeaturedRoundDecisionState": FeaturedRoundDecisionState,
    "FloorVoteDecisionState": FloorVoteDecisionState,
    "PowerupChoiceState": PowerupChoiceState,
    "GenomeEditChoiceState": GenomeEditChoiceState,
    "SuccessorChoiceState": SuccessorChoiceState,
}
_POWERUP_TYPES = {powerup_type.__name__: powerup_type for powerup_type in ALL_POWERUP_TYPES}
_GENOME_EDIT_TYPES = {type(edit).__name__: type(edit) for edit in build_genome_edit_pool()}


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
        self._branch_roster: list[Agent] = self._build_initial_branch_roster()
        self.opponent = self._select_floor_opponent()
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
        self._chronicle_event_ids: set[str] = set()
        self._branch_continuity_streaks: dict[str, int] = {}
        self._previous_floor_names: set[str] = set()
        self._previous_pressure_levels: dict[str, int] = {}
        self._previous_branch_stats: dict[str, tuple[int, int]] = {}
        self._previous_central_rival: str | None = None
        self._current_floor_central_rival: str | None = None
        self._current_floor_new_central_rival: str | None = None

    def serialize_state(self) -> dict:
        decision = self.session.current_decision
        expected_action_types = [action_type.__name__ for action_type in self.session._expected_action_types]
        return {
            "version": SAVE_STATE_VERSION,
            "seed": self.seed,
            "rounds": self.rounds,
            "rng_state": self._serialize_rng_state(self.rng.getstate()),
            "session": {
                "status": self.session.status,
                "decision_type": type(decision).__name__ if decision else None,
                "decision": asdict(decision) if decision else None,
                "expected_action_types": expected_action_types,
            },
            "snapshot": asdict(self.snapshot),
            "player": self._serialize_agent(self.player),
            "opponent": self._serialize_agent(self.opponent),
            "player_history": list(self.player_history),
            "opponent_history": list(self.opponent_history),
            "player_score": self.player_score,
            "opponent_score": self.opponent_score,
            "round_index": self.round_index,
            "floor_number": self.floor_number,
            "last_manual_move": self._last_manual_move,
            "active_stance": asdict(self._active_stance) if self._active_stance else None,
            "match_autopilot_active": self._match_autopilot_active,
            "pending_screen": self._pending_screen,
            "pending_message": self._pending_message,
            "powerup_offers": [self._serialize_powerup(powerup) for powerup in self._powerup_offers],
            "genome_offers": [self._serialize_genome_edit(edit) for edit in self._genome_offers],
            "successor_candidates": [self._serialize_agent(agent) for agent in self._successor_candidates],
            "branch_roster": [self._serialize_agent(agent) for agent in self._branch_roster],
            "floor_clue_log": list(self._floor_clue_log),
            "chronicle_event_ids": sorted(self._chronicle_event_ids),
            "branch_continuity_streaks": dict(self._branch_continuity_streaks),
            "previous_floor_names": sorted(self._previous_floor_names),
            "previous_pressure_levels": dict(self._previous_pressure_levels),
            "previous_branch_stats": {name: [stats[0], stats[1]] for name, stats in self._previous_branch_stats.items()},
            "previous_central_rival": self._previous_central_rival,
            "current_floor_central_rival": self._current_floor_central_rival,
            "current_floor_new_central_rival": self._current_floor_new_central_rival,
        }

    def serialize_state_json(self) -> str:
        return json.dumps(self.serialize_state(), sort_keys=True, separators=(",", ":"))

    def export_save_code(self, secret: bytes) -> str:
        payload_json = self.serialize_state_json()
        signature = hmac.new(secret, payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
        # Security model: this is integrity protection against client-side payload editing.
        # It does not protect against users who can modify/replace the server code or secret.
        envelope = {
            "version": SAVE_STATE_VERSION,
            "compressed": True,
            "payload": base64.urlsafe_b64encode(zlib.compress(payload_json.encode("utf-8"))).decode("ascii"),
            "signature": signature,
        }
        encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(encoded).decode("ascii")

    @classmethod
    def from_serialized_state(cls, payload: dict) -> "FeaturedMatchWebSession":
        try:
            if payload.get("version") != SAVE_STATE_VERSION:
                raise ValueError("Unsupported save state version")

            session = cls(seed=int(payload["seed"]), rounds=int(payload["rounds"]))
            rng_state = cls._deserialize_rng_state(payload["rng_state"])
            session.rng.setstate(rng_state)

            session.snapshot = cls._deserialize_run_snapshot(payload["snapshot"])
            session.player = cls._deserialize_agent(payload["player"])
            session.opponent = cls._deserialize_agent(payload["opponent"])
            session.player_history = list(payload["player_history"])
            session.opponent_history = list(payload["opponent_history"])
            session.player_score = int(payload["player_score"])
            session.opponent_score = int(payload["opponent_score"])
            session.round_index = int(payload["round_index"])
            session.floor_number = int(payload["floor_number"])
            session._last_manual_move = payload["last_manual_move"]
            active_stance = payload.get("active_stance")
            session._active_stance = FeaturedRoundStanceView(**active_stance) if active_stance else None
            session._match_autopilot_active = bool(payload["match_autopilot_active"])
            session._pending_screen = payload.get("pending_screen")
            session._pending_message = payload.get("pending_message")
            session._powerup_offers = [cls._deserialize_powerup(entry) for entry in payload.get("powerup_offers", [])]
            session._genome_offers = [cls._deserialize_genome_edit(entry) for entry in payload.get("genome_offers", [])]
            session._successor_candidates = [cls._deserialize_agent(entry) for entry in payload.get("successor_candidates", [])]
            session._branch_roster = [cls._deserialize_agent(entry) for entry in payload.get("branch_roster", [])]
            if not session._branch_roster:
                session._branch_roster = session._build_initial_branch_roster()
            matched_player = next((agent for agent in session._branch_roster if agent.name == session.player.name), None)
            if matched_player is not None:
                matched_player.is_player = True
                session.player = matched_player
            session.opponent = next(
                (agent for agent in session._branch_roster if agent.name == session.opponent.name and not agent.is_player),
                session._select_floor_opponent(),
            )
            session._floor_clue_log = list(payload.get("floor_clue_log", []))
            session._chronicle_event_ids = set(payload.get("chronicle_event_ids", []))
            session._branch_continuity_streaks = {str(name): int(streak) for name, streak in payload.get("branch_continuity_streaks", {}).items()}
            session._previous_floor_names = set(payload.get("previous_floor_names", []))
            session._previous_pressure_levels = {str(name): int(level) for name, level in payload.get("previous_pressure_levels", {}).items()}
            session._previous_branch_stats = {str(name): (int(stats[0]), int(stats[1])) for name, stats in payload.get("previous_branch_stats", {}).items()}
            previous_central_rival = payload.get("previous_central_rival")
            session._previous_central_rival = str(previous_central_rival) if previous_central_rival else None
            current_floor_central_rival = payload.get("current_floor_central_rival")
            session._current_floor_central_rival = str(current_floor_central_rival) if current_floor_central_rival else None
            current_floor_new_central_rival = payload.get("current_floor_new_central_rival")
            session._current_floor_new_central_rival = str(current_floor_new_central_rival) if current_floor_new_central_rival else None

            session_payload = payload["session"]
            session.session.status = session_payload["status"]
            decision_type_name = session_payload.get("decision_type")
            decision_payload = session_payload.get("decision")
            session.session.current_decision = cls._deserialize_decision(decision_type_name, decision_payload)
            session.session._expected_action_types = cls._resolve_expected_action_types(
                session_payload.get("expected_action_types", []),
                session.session.current_decision,
            )
            session.session._queued_action = None
            session.session.latest_snapshot = session.snapshot
            session.session.completion = session.snapshot.completion
            return session
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid save payload") from exc

    @classmethod
    def import_save_code(cls, save_code: str, secret: bytes) -> "FeaturedMatchWebSession":
        try:
            raw = base64.urlsafe_b64decode(save_code.encode("ascii")).decode("utf-8")
            envelope = json.loads(raw)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid save code") from exc
        if not isinstance(envelope, dict):
            raise ValueError("Invalid save code")
        if not isinstance(envelope.get("payload"), str) or not isinstance(envelope.get("signature"), str):
            raise ValueError("Invalid save code")

        payload_json = envelope["payload"]
        if envelope.get("compressed"):
            try:
                payload_json = zlib.decompress(base64.urlsafe_b64decode(payload_json.encode("ascii"))).decode("utf-8")
            except (ValueError, UnicodeDecodeError, zlib.error) as exc:
                raise ValueError("Invalid save code") from exc
        provided_signature = envelope["signature"]
        expected_signature = hmac.new(secret, payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise ValueError("Invalid save code")
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid save code") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invalid save code")
        return cls.from_serialized_state(payload)

    def start(self) -> None:
        self.session.start(self.snapshot)
        self.snapshot.header = self.snapshot.header or None
        self.snapshot.current_floor = self.floor_number
        self.snapshot.current_phase = "ecosystem"
        self._floor_clue_log = []
        self._append_chronicle_entry(
            event_id=f"run_start:seed:{self.seed}",
            event_type="run_start",
            floor_number=self.floor_number,
            summary=f"Run started (seed {self.seed}) in ecosystem play.",
        )
        self._rebuild_dynasty_board()
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
            pending_screen = self._pending_screen
            self._pending_screen = None
            self._pending_message = None
            if pending_screen == "civil_war_transition":
                self._begin_civil_war_floor()
            else:
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
        transition_label = self._transition_action_label()
        return {
            "status": self.session.status,
            "decision_type": type(self.session.current_decision).__name__ if self.session.current_decision else None,
            "decision": asdict(self.session.current_decision) if self.session.current_decision else None,
            "snapshot": asdict(self.snapshot),
            "pending_screen": self._pending_screen,
            "pending_message": self._pending_message,
            "transition_action_label": transition_label,
            "transition_action_visible": transition_label is not None,
        }

    def _transition_action_label(self) -> str | None:
        if self.session.current_decision is not None:
            return None
        if self._pending_screen == "floor_summary":
            return "Review successor options" if self.floor_number == 1 else "Continue to reward selection"
        if self._pending_screen == "civil_war_transition":
            return "Start civil-war round"
        if self.session.status == "running":
            return "Continue to next phase"
        return None

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

        self._advance_branch_roster_for_floor()
        summary_agents = self._branch_floor_ranking()
        previous_pressure_levels = {
            name: level for name, level in self._previous_pressure_levels.items()
        }

        pressure = analyze_floor_heir_pressure(summary_agents, self.player.lineage_id)
        heir_pressure = to_floor_summary_heir_pressure_view(pressure)
        successor_names = {entry.name for entry in heir_pressure.successor_candidates}
        threat_names = {entry.name for entry in heir_pressure.future_threats}

        entries: list[FloorSummaryEntryView] = []
        for agent in summary_agents:
            identity = analyze_agent_identity(agent)
            if agent.is_player:
                lineage_relation = "host"
            elif self.player.lineage_id is not None and agent.lineage_id == self.player.lineage_id:
                lineage_relation = "kin"
            else:
                lineage_relation = "outsider"

            survived_previous_floor = agent.name in self._previous_floor_names
            continuity_streak = self._branch_continuity_streaks.get(agent.name, 0) + 1 if survived_previous_floor else 1
            previous_score, previous_wins = self._previous_branch_stats.get(agent.name, (agent.score, agent.wins))
            score_delta = agent.score - previous_score
            wins_delta = agent.wins - previous_wins
            pressure_level = int(agent.name in successor_names) + int(agent.name in threat_names)
            previous_pressure_level = previous_pressure_levels.get(agent.name, pressure_level)
            if pressure_level > previous_pressure_level:
                pressure_trend = "rising"
            elif pressure_level < previous_pressure_level:
                pressure_trend = "falling"
            else:
                pressure_trend = "steady"

            entries.append(
                FloorSummaryEntryView(
                    agent_id=agent.agent_id,
                    name=agent.name,
                    is_player=agent.is_player,
                    score=agent.score,
                    wins=agent.wins,
                    lineage_depth=agent.lineage_depth,
                    tags=identity.tags,
                    descriptor=identity.descriptor,
                    genome_summary=agent.genome.summary(),
                    powerups=[p.name for p in agent.powerups],
                    lineage_relation=lineage_relation,
                    survived_previous_floor=survived_previous_floor,
                    continuity_streak=continuity_streak,
                    score_delta=score_delta,
                    wins_delta=wins_delta,
                    pressure_trend=pressure_trend,
                )
            )
        ordered_entries = sorted(entries, key=lambda entry: (-entry.score, entry.name, entry.lineage_depth))
        central_rival_name = next((entry.name for entry in ordered_entries if not entry.is_player), None)
        self._current_floor_central_rival = central_rival_name
        self._current_floor_new_central_rival = (
            central_rival_name
            if central_rival_name is not None and central_rival_name != self._previous_central_rival
            else None
        )

        self.snapshot.floor_summary = FloorSummaryState(
            floor_number=self.floor_number,
            entries=entries,
            heir_pressure=heir_pressure,
            featured_inference_summary=summarize_featured_inference_signals(
                normalize_featured_inference_signals(self._floor_clue_log)
            ),
        )
        self._previous_floor_names = {entry.name for entry in entries}
        self._branch_continuity_streaks = {entry.name: entry.continuity_streak for entry in entries}
        self._previous_branch_stats = {entry.name: (entry.score, entry.wins) for entry in entries}
        self._previous_pressure_levels = {
            entry.name: int(entry.name in successor_names) + int(entry.name in threat_names)
            for entry in entries
        }
        self._previous_central_rival = central_rival_name
        self.snapshot.session_status = "running"
        self._pending_screen = "floor_summary"
        next_step = "review successor options" if self.floor_number == 1 else "continue to reward selection"
        self._pending_message = f"Floor {self.floor_number} complete — {next_step}."
        featured_note = self.snapshot.floor_summary.featured_inference_summary[0] if self.snapshot.floor_summary.featured_inference_summary else "No solid clue read survived this floor."
        doctrine_note = heir_pressure.branch_doctrine if heir_pressure is not None else "Playstyle trend is unclear."
        self._append_chronicle_entry(
            event_id=f"floor_complete:{self.floor_number}",
            event_type="floor_complete",
            floor_number=self.floor_number,
            summary=f"Floor {self.floor_number} ended at {self.player_score} points. {featured_note}",
        )
        self._append_chronicle_entry(
            event_id=f"doctrine_pivot:{self.floor_number}",
            event_type="doctrine_pivot",
            floor_number=self.floor_number,
            summary=f"Lineage trend: {doctrine_note}",
            cause=self._lineage_cause_phrase(
                self.snapshot.floor_summary.featured_inference_summary,
                doctrine_note,
            ),
        )
        self._rebuild_dynasty_board()

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
            self._rebuild_dynasty_board()
            self._append_chronicle_entry(
                event_id=f"successor_pressure:{self.floor_number}",
                event_type="successor_pressure",
                floor_number=self.floor_number,
                summary=f"Succession pressure is {civil_war_pressure}; top threats: {', '.join(sorted(threat_tags)) or 'none' }.",
                cause=self._lineage_cause_phrase(
                    list(self.snapshot.floor_summary.featured_inference_summary) if self.snapshot.floor_summary else [],
                    f"threat mix {', '.join(sorted(threat_tags)) or 'none'}",
                ),
            )
            self.session.begin_decision(state, (ChooseSuccessorAction,), self.snapshot)
            self.snapshot.session_status = "awaiting_decision"
            return

        self._begin_powerup_choice()

    def _begin_powerup_choice(self) -> None:
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
        chosen_view = decision.candidates[action.candidate_index]
        previous_host = self.player.name
        chosen.is_player = True
        self.player.is_player = False
        self.player = chosen
        self._append_chronicle_entry(
            event_id=f"successor_choice:{self.floor_number}:{action.candidate_index}",
            event_type="successor_choice",
            floor_number=1,
            summary=f"Host shifted from {previous_host} to {chosen.name}.",
        )

        if self._should_start_civil_war():
            self.snapshot.floor_identity = None
            self.snapshot.current_phase = "civil_war"
            self.snapshot.floor_vote_result = None
            self.snapshot.civil_war_context = build_civil_war_context(
                branches=list(self._successor_candidates),
                current_host=chosen,
                featured_inference_signals=normalize_featured_inference_signals(self._floor_clue_log),
            )
            self.floor_number = 2
            self.snapshot.current_floor = self.floor_number
            self._pending_screen = "civil_war_transition"
            self._pending_message = f"{self.snapshot.civil_war_context.thesis} Start the civil-war round."
            self._append_chronicle_entry(
                event_id="phase_transition:civil_war",
                event_type="phase_transition",
                floor_number=self.floor_number,
                summary=f"Civil war started: {self.snapshot.civil_war_context.thesis}",
                cause=self._lineage_cause_phrase(
                    list(self.snapshot.civil_war_context.doctrine_pressure),
                    self.snapshot.civil_war_context.thesis,
                ),
            )
            self.snapshot.session_status = "running"
        else:
            self.snapshot.current_phase = "ecosystem"
            self.snapshot.civil_war_context = None
            self.snapshot.floor_identity = self._build_next_floor_identity(decision=decision, chosen=chosen_view)
            self._pending_screen = None
            self._pending_message = None
            self._begin_powerup_choice()
        self._rebuild_dynasty_board()

    def _build_next_floor_identity(self, decision: SuccessorChoiceState, chosen: SuccessorCandidateView) -> FloorIdentityState:
        threat_profile = list(decision.threat_profile or [])
        pressure_label = {
            "high": "Containment floor",
            "rising": "Pressure-test floor",
            "low": "Expansion floor",
        }.get(decision.civil_war_pressure or "", "Lineage floor")
        top_threat = threat_profile[0] if threat_profile else "no dominant threat tag"
        heir_tag = chosen.tags[0] if chosen.tags else "untyped"
        dominant_pressure = top_threat if top_threat != "no dominant threat tag" else heir_tag
        clue_signal = (decision.featured_inference_summary[0] if decision.featured_inference_summary else None)
        doctrine = decision.lineage_doctrine or chosen.branch_doctrine
        headline = f"{pressure_label}: {chosen.name} · {chosen.branch_role}"
        return FloorIdentityState(
            target_floor=self.floor_number + 1,
            host_name=chosen.name,
            headline=headline,
            pressure_label=pressure_label,
            dominant_pressure=dominant_pressure,
            pressure_reason=f"{chosen.name} inherits into {dominant_pressure} pressure.",
            lineage_direction=f"Doctrine path: {doctrine}",
            strategic_focus=f"Lean into {chosen.attractive_now.lower()} while respecting {chosen.danger_later.lower()}.",
            key_signal=clue_signal,
        )

    def _should_start_civil_war(self) -> bool:
        floor_summary = self.snapshot.floor_summary
        if floor_summary is None or floor_summary.heir_pressure is None:
            return False
        return len(floor_summary.heir_pressure.future_threats) == 0

    def _begin_civil_war_floor(self) -> None:
        self._reset_floor_state_for_new_match()

        rivals = [agent for agent in self._successor_candidates if agent.name != self.player.name]
        if rivals:
            self.opponent = max(rivals, key=lambda agent: (agent.score, agent.wins, -agent.agent_id))
        else:
            self.opponent = Agent(name="Civil War Rival", genome=self._opponent_genome())
        self.opponent.is_player = False

        context = self.snapshot.civil_war_context
        doctrine_pressure = []
        if isinstance(context, dict):
            doctrine_pressure = list(context.get("doctrine_pressure", []))
        elif context is not None:
            doctrine_pressure = list(context.doctrine_pressure)

        self._append_chronicle_entry(
            event_id=f"civil_war_floor_start:{self.floor_number}:{self.opponent.name}",
            event_type="civil_war_round_start",
            floor_number=self.floor_number,
            summary=f"Civil-war round started against {self.opponent.name}.",
            cause=self._lineage_cause_phrase(
                doctrine_pressure,
                "civil-war pressure forces a direct duel",
            ),
        )
        self._begin_featured_round_decision()

    def _begin_next_ecosystem_floor(self) -> None:
        self.floor_number += 1
        self.snapshot.current_floor = self.floor_number
        self.snapshot.current_phase = "ecosystem"
        self.snapshot.civil_war_context = None
        self.snapshot.successor_options = None
        self._pending_screen = None
        self._pending_message = None

        self._reset_floor_state_for_new_match()
        self.opponent = self._select_floor_opponent()

        floor_identity = self.snapshot.floor_identity
        identity_note = (
            f" {floor_identity.pressure_label}: {floor_identity.strategic_focus}"
            if floor_identity and floor_identity.target_floor == self.floor_number
            else ""
        )
        self._append_chronicle_entry(
            event_id=f"floor_start:{self.floor_number}",
            event_type="floor_start",
            floor_number=self.floor_number,
            summary=f"Floor {self.floor_number} started in ecosystem play.{identity_note}",
        )
        self._begin_featured_round_decision()

    def _reset_floor_state_for_new_match(self) -> None:
        self.round_index = 0
        self.player_history = []
        self.opponent_history = []
        self.player_score = 0
        self.opponent_score = 0
        self.snapshot.floor_vote_result = None
        self.snapshot.floor_summary = None
        self._floor_clue_log = []

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

        if self.snapshot.current_phase == "civil_war":
            completion = RunCompletion(
                outcome="victory" if self.player_score >= self.opponent_score else "eliminated",
                floor_number=self.floor_number,
                player_name=self.player.name,
                seed=self.seed,
            )
            self.snapshot.completion = completion
            self._append_chronicle_entry(
                event_id=f"run_outcome:{completion.outcome}",
                event_type="run_outcome",
                floor_number=self.floor_number,
                summary=f"Run ended in {completion.outcome} on floor {self.floor_number} as {self.player.name}.",
            )
            self.session.complete(completion, self.snapshot)
            self.snapshot.session_status = "completed"
        else:
            self._begin_next_ecosystem_floor()
            self.snapshot.session_status = "awaiting_decision"
        self._rebuild_dynasty_board()

    def _rebuild_dynasty_board(self) -> None:
        pressure_names: set[str] = set()
        danger_names: set[str] = set()
        pressure_causes: dict[str, str] = {}
        danger_causes: dict[str, str] = {}
        floor_summary = self.snapshot.floor_summary
        if floor_summary and floor_summary.heir_pressure:
            pressure_names.update(entry.name for entry in floor_summary.heir_pressure.successor_candidates)
            danger_names.update(entry.name for entry in floor_summary.heir_pressure.future_threats)
            for entry in floor_summary.heir_pressure.successor_candidates:
                pressure_causes[entry.name] = self._lineage_cause_phrase(entry.shaping_causes, entry.rationale)
            for entry in floor_summary.heir_pressure.future_threats:
                danger_causes[entry.name] = self._lineage_cause_phrase(entry.shaping_causes, entry.rationale)
        successor_options = self.snapshot.successor_options
        successor_candidate_views = {
            candidate.name: candidate for candidate in successor_options.candidates
        } if successor_options else {}
        if successor_options and successor_options.candidates:
            top_score = max(candidate.score for candidate in successor_options.candidates)
            for candidate in successor_options.candidates:
                if candidate.score == top_score:
                    pressure_names.add(candidate.name)
                    if candidate.name not in pressure_causes:
                        pressure_causes[candidate.name] = self._lineage_cause_phrase(
                            candidate.shaping_causes,
                            candidate.succession_pitch,
                        )

        entries: list[DynastyBoardEntryView] = []
        floor_entry_by_name = {entry.name: entry for entry in floor_summary.entries} if floor_summary else {}
        if self.snapshot.successor_options and self._successor_candidates:
            branch_pool = list(self._successor_candidates)
            if all(agent.name != self.player.name for agent in branch_pool):
                branch_pool.append(self.player)
            for agent in branch_pool:
                identity = analyze_agent_identity(agent)
                doctrine_signal = ", ".join(identity.tags[:2]) if identity.tags else identity.descriptor
                entries.append(
                    DynastyBoardEntryView(
                        name=agent.name,
                        role=identity.descriptor,
                        doctrine_signal=doctrine_signal,
                        score=agent.score,
                        wins=agent.wins,
                        lineage_depth=agent.lineage_depth,
                        is_current_host=agent.is_player or agent.name == self.player.name,
                        has_successor_pressure=agent.name in pressure_names,
                        has_civil_war_danger=agent.name in danger_names,
                        successor_pressure_cause=pressure_causes.get(agent.name),
                        civil_war_danger_cause=danger_causes.get(agent.name),
                        lineage_relation=(
                            floor_entry_by_name[agent.name].lineage_relation
                            if agent.name in floor_entry_by_name
                            else ("host" if (agent.is_player or agent.name == self.player.name) else ("kin" if self.player.lineage_id is not None and agent.lineage_id == self.player.lineage_id else "outsider"))
                        ),
                        survived_previous_floor=(floor_entry_by_name[agent.name].survived_previous_floor if agent.name in floor_entry_by_name else False),
                        continuity_streak=(floor_entry_by_name[agent.name].continuity_streak if agent.name in floor_entry_by_name else 1),
                        score_delta=(floor_entry_by_name[agent.name].score_delta if agent.name in floor_entry_by_name else 0),
                        wins_delta=(floor_entry_by_name[agent.name].wins_delta if agent.name in floor_entry_by_name else 0),
                        pressure_trend=(floor_entry_by_name[agent.name].pressure_trend if agent.name in floor_entry_by_name else "steady"),
                        is_central_rival=agent.name == self._current_floor_central_rival,
                        is_new_central_rival=agent.name == self._current_floor_new_central_rival,
                    )
                )
        elif floor_summary and floor_summary.entries:
            for entry in floor_summary.entries:
                doctrine_signal = ", ".join(entry.tags[:2]) if entry.tags else entry.descriptor
                entries.append(
                    DynastyBoardEntryView(
                        name=entry.name,
                        role=entry.descriptor,
                        doctrine_signal=doctrine_signal,
                        score=entry.score,
                        wins=entry.wins,
                        lineage_depth=entry.lineage_depth,
                        is_current_host=entry.is_player,
                        has_successor_pressure=entry.name in pressure_names,
                        has_civil_war_danger=entry.name in danger_names,
                        successor_pressure_cause=pressure_causes.get(entry.name),
                        civil_war_danger_cause=danger_causes.get(entry.name),
                        lineage_relation=getattr(entry, "lineage_relation", "host" if entry.is_player else "outsider"),
                        survived_previous_floor=getattr(entry, "survived_previous_floor", False),
                        continuity_streak=getattr(entry, "continuity_streak", 1),
                        score_delta=getattr(entry, "score_delta", 0),
                        wins_delta=getattr(entry, "wins_delta", 0),
                        pressure_trend=getattr(entry, "pressure_trend", "steady"),
                        is_central_rival=entry.name == self._current_floor_central_rival,
                        is_new_central_rival=entry.name == self._current_floor_new_central_rival,
                    )
                )
        else:
            for agent in (self.player, self.opponent):
                identity = analyze_agent_identity(agent)
                doctrine_signal = ", ".join(identity.tags[:2]) if identity.tags else identity.descriptor
                entries.append(
                    DynastyBoardEntryView(
                        name=agent.name,
                        role=identity.descriptor,
                        doctrine_signal=doctrine_signal,
                        score=agent.score,
                        wins=agent.wins,
                        lineage_depth=agent.lineage_depth,
                        is_current_host=agent.is_player,
                        has_successor_pressure=False,
                        has_civil_war_danger=False,
                        successor_pressure_cause=None,
                        civil_war_danger_cause=None,
                        lineage_relation=("host" if agent.is_player else ("kin" if self.player.lineage_id is not None and agent.lineage_id == self.player.lineage_id else "outsider")),
                        survived_previous_floor=False,
                        continuity_streak=1,
                        score_delta=0,
                        wins_delta=0,
                        pressure_trend="steady",
                        is_central_rival=agent.name == self._current_floor_central_rival,
                        is_new_central_rival=agent.name == self._current_floor_new_central_rival,
                    )
                )

        if self.snapshot.current_phase == "civil_war":
            threat_tags = set((self.snapshot.successor_options and self.snapshot.successor_options.threat_profile) or [])
            for idx, board_entry in enumerate(entries):
                candidate = next((agent for agent in self._successor_candidates if agent.name == board_entry.name), None)
                if candidate is None:
                    continue
                tags = set(analyze_agent_identity(candidate).tags)
                if tags & threat_tags:
                    existing_cause = entries[idx].civil_war_danger_cause
                    candidate_view = successor_candidate_views.get(candidate.name)
                    danger_cause = existing_cause or self._lineage_cause_phrase(
                        candidate_view.shaping_causes if candidate_view else [],
                        candidate_view.danger_later if candidate_view else "civil-war threat tags are active",
                    )
                    entries[idx] = DynastyBoardEntryView(
                        name=board_entry.name,
                        role=board_entry.role,
                        doctrine_signal=board_entry.doctrine_signal,
                        score=board_entry.score,
                        wins=board_entry.wins,
                        lineage_depth=board_entry.lineage_depth,
                        is_current_host=board_entry.is_current_host,
                        has_successor_pressure=board_entry.has_successor_pressure,
                        has_civil_war_danger=True,
                        successor_pressure_cause=board_entry.successor_pressure_cause,
                        civil_war_danger_cause=danger_cause,
                        lineage_relation=board_entry.lineage_relation,
                        survived_previous_floor=board_entry.survived_previous_floor,
                        continuity_streak=board_entry.continuity_streak,
                        score_delta=board_entry.score_delta,
                        wins_delta=board_entry.wins_delta,
                        pressure_trend=board_entry.pressure_trend,
                        is_central_rival=board_entry.is_central_rival,
                        is_new_central_rival=board_entry.is_new_central_rival,
                    )

        entries.sort(key=lambda entry: (-entry.score, entry.name, entry.lineage_depth))
        self.snapshot.dynasty_board = DynastyBoardState(phase=self.snapshot.current_phase, entries=entries)

    def _lineage_cause_phrase(self, shaping_causes: list[str], fallback: str) -> str:
        lead = shaping_causes[0] if shaping_causes else fallback
        compact = lead.strip().rstrip(".")
        return f"because {compact}"

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

    def _append_chronicle_entry(
        self,
        *,
        event_id: str,
        event_type: str,
        floor_number: int | None,
        summary: str,
        cause: str | None = None,
    ) -> None:
        if event_id in self._chronicle_event_ids:
            return
        self._chronicle_event_ids.add(event_id)
        self.snapshot.lineage_chronicle.append(
            LineageChronicleEntry(
                event_id=event_id,
                event_type=event_type,
                floor_number=floor_number,
                phase=self.snapshot.current_phase,
                summary=summary,
                cause=cause,
            )
        )

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

    def _build_initial_branch_roster(self) -> list[Agent]:
        player = self.player
        player.is_player = True
        return [
            player,
            Agent(name="Cinder Branch", genome=self._default_genome(), lineage_id=1, lineage_depth=1),
            Agent(name="Vesper Branch", genome=self._opponent_genome(), lineage_id=1, lineage_depth=2),
            Agent(name="Thorn Compact", genome=self._opponent_genome(), lineage_depth=2),
            Agent(name="Morrow Syndic", genome=self._default_genome(), lineage_depth=3),
        ]

    def _advance_branch_roster_for_floor(self) -> None:
        self.player.score = self.player_score
        self.player.wins = max(0, min(self.rounds, (self.player_score + 1) // 2))
        rivals = [agent for agent in self._branch_roster if agent is not self.player]
        rivals.sort(key=lambda agent: agent.agent_id)
        for idx, rival in enumerate(rivals, start=1):
            swing = ((self.seed + self.floor_number + rival.agent_id) % 3) - 1
            rival.score = max(0, self.player_score - idx + swing)
            rival.wins = max(0, min(self.rounds, rival.score // 2))

    def _branch_floor_ranking(self) -> list[Agent]:
        ranked = sorted(self._branch_roster, key=lambda agent: (agent.score, agent.wins, -agent.agent_id), reverse=True)
        return ranked[:4]

    def _select_floor_opponent(self) -> Agent:
        rivals = [agent for agent in self._branch_roster if agent is not self.player]
        if not rivals:
            return Agent(name="Civil War Rival", genome=self._opponent_genome())
        opponent = max(rivals, key=lambda agent: (agent.score, agent.wins, -agent.agent_id))
        opponent.is_player = False
        return opponent

    def _build_successor_candidates(self) -> list[Agent]:
        lineage_branches = [
            agent
            for agent in self._branch_roster
            if agent.lineage_id == self.player.lineage_id and agent is not self.player
        ]
        if not lineage_branches:
            new_heir = self.player.clone_for_offspring(self.player.genome)
            new_heir.lineage_id = self.player.lineage_id
            self._branch_roster.append(new_heir)
            lineage_branches.append(new_heir)
        lineage_branches.sort(key=lambda agent: (agent.score, agent.wins, -agent.agent_id), reverse=True)
        return lineage_branches[:3]

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

    @staticmethod
    def _serialize_powerup(powerup: Powerup) -> dict:
        payload = asdict(powerup)
        payload["type"] = type(powerup).__name__
        return payload

    @staticmethod
    def _deserialize_powerup(payload: dict) -> Powerup:
        powerup_type_name = payload.get("type")
        if powerup_type_name not in _POWERUP_TYPES:
            raise ValueError("Unsupported powerup type in save state")
        powerup_type = _POWERUP_TYPES[powerup_type_name]
        kwargs = {key: value for key, value in payload.items() if key != "type"}
        return powerup_type(**kwargs)

    @staticmethod
    def _serialize_genome_edit(edit: GenomeEdit) -> dict:
        return {"type": type(edit).__name__}

    @staticmethod
    def _deserialize_genome_edit(payload: dict) -> GenomeEdit:
        genome_edit_type_name = payload.get("type")
        if genome_edit_type_name not in _GENOME_EDIT_TYPES:
            raise ValueError("Unsupported genome edit type in save state")
        return _GENOME_EDIT_TYPES[genome_edit_type_name]()

    @classmethod
    def _serialize_agent(cls, agent: Agent) -> dict:
        return {
            "name": agent.name,
            "public_profile": agent.public_profile,
            "powerups": [cls._serialize_powerup(powerup) for powerup in agent.powerups],
            "score": agent.score,
            "wins": agent.wins,
            "is_player": agent.is_player,
            "lineage_id": agent.lineage_id,
            "lineage_depth": agent.lineage_depth,
            "agent_id": agent.agent_id,
            "genome": cls._serialize_genome(agent.genome),
        }

    @classmethod
    def _deserialize_agent(cls, payload: dict) -> Agent:
        return Agent(
            name=payload["name"],
            genome=cls._deserialize_genome(payload["genome"]),
            public_profile=payload["public_profile"],
            powerups=[cls._deserialize_powerup(entry) for entry in payload.get("powerups", [])],
            score=payload["score"],
            wins=payload["wins"],
            is_player=payload["is_player"],
            lineage_id=payload["lineage_id"],
            lineage_depth=payload["lineage_depth"],
            agent_id=payload["agent_id"],
        )

    @staticmethod
    def _serialize_genome(genome: StrategyGenome) -> dict:
        return {
            "first_move": genome.first_move,
            "noise": genome.noise,
            "response_table": {
                "cc": genome.response_table[(COOPERATE, COOPERATE)],
                "cd": genome.response_table[(COOPERATE, DEFECT)],
                "dc": genome.response_table[(DEFECT, COOPERATE)],
                "dd": genome.response_table[(DEFECT, DEFECT)],
            },
        }

    @staticmethod
    def _deserialize_genome(payload: dict) -> StrategyGenome:
        table = payload["response_table"]
        return StrategyGenome(
            first_move=payload["first_move"],
            noise=payload["noise"],
            response_table={
                (COOPERATE, COOPERATE): table["cc"],
                (COOPERATE, DEFECT): table["cd"],
                (DEFECT, COOPERATE): table["dc"],
                (DEFECT, DEFECT): table["dd"],
            },
        )

    @classmethod
    def _deserialize_decision(cls, decision_type_name: str | None, payload: dict | None):
        if decision_type_name is None or payload is None:
            return None
        decision_type = _DECISION_TYPES.get(decision_type_name)
        if decision_type is None:
            raise ValueError("Unsupported decision type in save state")
        return cls._build_dataclass(decision_type, payload)

    @classmethod
    def _resolve_expected_action_types(cls, expected_type_names: list[str], decision) -> tuple[type, ...]:
        if expected_type_names:
            type_map = {
                "ChooseRoundMoveAction": ChooseRoundMoveAction,
                "ChooseRoundAutopilotAction": ChooseRoundAutopilotAction,
                "ChooseRoundStanceAction": ChooseRoundStanceAction,
                "ChooseFloorVoteAction": ChooseFloorVoteAction,
                "ChoosePowerupAction": ChoosePowerupAction,
                "ChooseGenomeEditAction": ChooseGenomeEditAction,
                "ChooseSuccessorAction": ChooseSuccessorAction,
            }
            resolved_types: list[type] = []
            for expected_name in expected_type_names:
                if expected_name not in type_map:
                    raise ValueError("Unsupported expected action type in save state")
                resolved_types.append(type_map[expected_name])
            return tuple(resolved_types)
        if isinstance(decision, FeaturedRoundDecisionState):
            return (ChooseRoundMoveAction, ChooseRoundAutopilotAction, ChooseRoundStanceAction)
        if isinstance(decision, FloorVoteDecisionState):
            return (ChooseFloorVoteAction,)
        if isinstance(decision, PowerupChoiceState):
            return (ChoosePowerupAction,)
        if isinstance(decision, GenomeEditChoiceState):
            return (ChooseGenomeEditAction,)
        if isinstance(decision, SuccessorChoiceState):
            return (ChooseSuccessorAction,)
        return ()

    @classmethod
    def _deserialize_run_snapshot(cls, payload: dict) -> RunSnapshot:
        return cls._build_dataclass(RunSnapshot, payload)

    @classmethod
    def _build_dataclass(cls, dataclass_type: type, payload: dict):
        field_values = {}
        hints = get_type_hints(dataclass_type)
        for field in dataclass_type.__dataclass_fields__.values():  # type: ignore[attr-defined]
            if field.name not in payload:
                continue
            annotation = hints.get(field.name, field.type)
            field_values[field.name] = cls._decode_value(annotation, payload[field.name])
        return dataclass_type(**field_values)

    @classmethod
    def _decode_value(cls, annotation, value):
        if value is None:
            return None
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())
        if origin is list and args:
            return [cls._decode_value(args[0], item) for item in value]
        if origin is tuple and args:
            return tuple(cls._decode_value(args[0], item) for item in value)
        if origin is None and hasattr(annotation, "__dataclass_fields__") and isinstance(value, dict):
            return cls._build_dataclass(annotation, value)
        if str(origin) in {"typing.Union", "types.UnionType"}:
            for candidate in args:
                if candidate is type(None):
                    continue
                try:
                    return cls._decode_value(candidate, value)
                except Exception:  # noqa: BLE001
                    continue
        return value

    @classmethod
    def _serialize_rng_state(cls, state: tuple) -> dict:
        version, internal_state, gauss_next = state
        return {
            "version": int(version),
            "internal_state": cls._encode_tuple(internal_state),
            "gauss_next": gauss_next,
        }

    @classmethod
    def _deserialize_rng_state(cls, payload: dict) -> tuple:
        if not isinstance(payload, dict):
            raise ValueError("Invalid rng_state payload")
        if "version" not in payload or "internal_state" not in payload:
            raise ValueError("Invalid rng_state payload")
        internal_state = cls._decode_tuple(payload["internal_state"])
        gauss_next = payload.get("gauss_next")
        if gauss_next is not None and not isinstance(gauss_next, (int, float)):
            raise ValueError("Invalid rng_state payload")
        return (int(payload["version"]), internal_state, gauss_next)

    @classmethod
    def _encode_tuple(cls, value):
        if isinstance(value, tuple):
            return [cls._encode_tuple(item) for item in value]
        if isinstance(value, list):
            return [cls._encode_tuple(item) for item in value]
        return value

    @classmethod
    def _decode_tuple(cls, value):
        if isinstance(value, list):
            return tuple(cls._decode_tuple(item) for item in value)
        return value
