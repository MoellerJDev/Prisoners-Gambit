from __future__ import annotations

from dataclasses import asdict
import random

from prisoners_gambit.content.session_text import (
    CIVIL_WAR_RIVAL_NAME,
    UNKNOWN_OPPONENT_LABEL,
    civil_war_round_start_summary,
    civil_war_started_fallback,
    civil_war_started_summary,
    doctrine_shift_summary,
    dominant_pressure_fallback,
    ecosystem_floor_start_summary,
    featured_round_clue_channels,
    featured_round_inference_focus,
    featured_round_pattern_focus,
    floor_complete_summary,
    floor_identity_focus,
    floor_identity_focus_with_cause,
    floor_identity_focus_with_clue,
    floor_identity_headline,
    floor_identity_pressure_reason,
    floor_pressure_label,
    heir_tag_fallback,
    host_hold_summary,
    host_shift_summary,
    lineage_direction_text,
    no_solid_clue_read_this_floor,
    pending_civil_war_start_message,
    pending_floor_complete_message,
    run_outcome_summary,
    run_start_summary,
    successor_pressure_cause_fallback,
    successor_pressure_summary,
    transition_action_label,
    unclear_playstyle_trend,
)
from prisoners_gambit.core.choice_presenters import doctrine_commitment_summary, offer_fit_detail
from prisoners_gambit.app.heir_view_mapping import to_successor_candidate_view
from prisoners_gambit.app.interaction_controller import RunSession
from prisoners_gambit.core.analysis import analyze_agent_identity, assess_successor_candidate
from prisoners_gambit.core.civil_war import build_civil_war_context
from prisoners_gambit.core.featured_inference import (
    normalize_featured_inference_signals,
    successor_featured_inference_brief,
    successor_featured_inference_context,
)
from prisoners_gambit.core.successor_analysis import civil_war_pressure_for_threat_tags
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseFloorEventAction,
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
    FloorIdentityState,
    FloorEventChoiceState,
    FloorVoteDecisionState,
    FloorVotePrompt,
    FloorVoteResult,
    GenomeEditChoiceState,
    PowerupChoiceState,
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
from prisoners_gambit.core.dynasty import (
    DynastyState,
    adjust_dynasty_state,
    can_use_contingency,
    clear_claimant,
    initial_dynasty_state,
    is_claimant_alive,
    set_claimant,
    spend_contingency,
    to_view as dynasty_to_view,
    update_after_floor,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.offer_views import to_genome_edit_offer_view, to_powerup_offer_view
from prisoners_gambit.core.powerups import (
    ALL_POWERUP_TYPES,
    ComplianceDividend,
    CounterIntel,
    MoveDirective,
    ReferendumContext,
    RoundContext,
    derive_referendum_combo_events,
    derive_round_combo_events,
    resolve_move,
)
from prisoners_gambit.core.scoring import base_payoff
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.content.genome_edit_templates import build_genome_edit_pool
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import (
    PowerupOfferContext,
    derive_doctrine_state,
    generate_powerup_offer_set,
    offer_category_hint,
    seed_run_house_doctrine,
)
from prisoners_gambit.systems.evolution import EvolutionEngine
from prisoners_gambit.systems.floor_events import (
    ActiveFloorEvent,
    apply_match_event_bonus,
    apply_referendum_event_bonus,
    choose_floor_event_response,
    clue_prefix,
    favored_offer_biases,
    generate_floor_event,
    response_dynasty_modifier,
    response_commitment_modifier,
    to_choice_state as floor_event_choice_state,
    to_snapshot_state as floor_event_snapshot_state,
)
from prisoners_gambit.systems.progression import ProgressionEngine
from prisoners_gambit.systems.tournament import TournamentEngine
from prisoners_gambit.web.floor_summary_support import FloorContinuityContext, synthesize_floor_summary
from prisoners_gambit.web.session_snapshot_support import (
    DynastyBoardBuildContext,
    lineage_cause_phrase,
    rebuild_dynasty_board,
    refresh_strategic_snapshot,
)
from prisoners_gambit.web.session_state_codec import (
    build_dataclass,
    deserialize_agent,
    deserialize_decision,
    deserialize_genome_edit,
    deserialize_powerup,
    deserialize_rng_state,
    deserialize_run_snapshot,
    export_save_code,
    import_save_code,
    resolve_expected_action_types,
    serialize_agent,
    serialize_genome_edit,
    serialize_powerup,
    serialize_rng_state,
    serialize_state_json,
)


SAVE_STATE_VERSION = 1
_DECISION_TYPES = {
    "FloorEventChoiceState": FloorEventChoiceState,
    "FeaturedRoundDecisionState": FeaturedRoundDecisionState,
    "FloorVoteDecisionState": FloorVoteDecisionState,
    "PowerupChoiceState": PowerupChoiceState,
    "GenomeEditChoiceState": GenomeEditChoiceState,
    "SuccessorChoiceState": SuccessorChoiceState,
}
_POWERUP_TYPES = {powerup_type.__name__: powerup_type for powerup_type in ALL_POWERUP_TYPES}
_GENOME_EDIT_TYPES = {type(edit).__name__: type(edit) for edit in build_genome_edit_pool()}


class FeaturedMatchWebSession:
    def __init__(
        self,
        seed: int = 7,
        rounds: int = 3,
        *,
        survivor_count: int = 4,
        floor_cap: int = 20,
        mutation_rate: float = 0.15,
        descendant_mutation_bonus: float = 1.75,
    ) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.rounds = rounds
        self.survivor_count = max(1, min(survivor_count, 4))
        self.floor_cap = max(1, floor_cap)
        self.mutation_rate = mutation_rate
        self.descendant_mutation_bonus = descendant_mutation_bonus
        self.session = RunSession()
        self.snapshot = RunSnapshot()
        self._dynasty_state = initial_dynasty_state()
        self.player = Agent(name="You", genome=self._default_genome(), is_player=True, lineage_id=1)
        self.opponent = Agent(name=UNKNOWN_OPPONENT_LABEL, genome=self._opponent_genome())
        self.player.powerups.append(ComplianceDividend())
        self.opponent.powerups.append(CounterIntel())
        self._branch_roster: list[Agent] = self._build_initial_branch_roster()
        self._target_population_size = len(self._branch_roster)
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
        self._upcoming_phase: str | None = None
        self._pending_successor_reason: str | None = None
        self._powerup_offers = []
        self._genome_offers = []
        self._successor_candidates: list[Agent] = []
        self._active_floor_event: ActiveFloorEvent | None = None
        self._previous_event_key: str | None = None
        self._floor_clue_log: list[str] = []
        self._chronicle_event_ids: set[str] = set()
        self._branch_continuity_streaks: dict[str, int] = {}
        self._previous_floor_names: set[str] = set()
        self._previous_pressure_levels: dict[str, int] = {}
        self._previous_branch_stats: dict[str, tuple[int, int]] = {}
        self._previous_central_rival: str | None = None
        self._current_floor_central_rival: str | None = None
        self._current_floor_new_central_rival: str | None = None
        self._progression = ProgressionEngine(rng=self.rng, offers_per_floor=3, featured_matches_per_floor=1)
        self._evolution = EvolutionEngine(
            survivor_count=self.survivor_count,
            mutation_rate=self.mutation_rate,
            descendant_mutation_bonus=self.descendant_mutation_bonus,
            rng=self.rng,
        )
        self._tournament = TournamentEngine(base_rounds_per_match=rounds, rng=self.rng)

    def serialize_state(self) -> dict:
        decision = self.session.current_decision
        expected_action_types = [action_type.__name__ for action_type in self.session._expected_action_types]
        return {
            "version": SAVE_STATE_VERSION,
            "seed": self.seed,
            "rounds": self.rounds,
            "survivor_count": self.survivor_count,
            "floor_cap": self.floor_cap,
            "mutation_rate": self.mutation_rate,
            "descendant_mutation_bonus": self.descendant_mutation_bonus,
            "rng_state": serialize_rng_state(self.rng.getstate()),
            "session": {
                "status": self.session.status,
                "decision_type": type(decision).__name__ if decision else None,
                "decision": asdict(decision) if decision else None,
                "expected_action_types": expected_action_types,
            },
            "snapshot": asdict(self.snapshot),
            "player": serialize_agent(self.player),
            "opponent": serialize_agent(self.opponent),
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
            "upcoming_phase": self._upcoming_phase,
            "pending_successor_reason": self._pending_successor_reason,
            "powerup_offers": [serialize_powerup(powerup) for powerup in self._powerup_offers],
            "genome_offers": [serialize_genome_edit(edit) for edit in self._genome_offers],
            "successor_candidates": [serialize_agent(agent) for agent in self._successor_candidates],
            "branch_roster": [serialize_agent(agent) for agent in self._branch_roster],
            "dynasty_state": asdict(self._dynasty_state),
            "active_floor_event": asdict(self._active_floor_event) if self._active_floor_event is not None else None,
            "previous_event_key": self._previous_event_key,
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
        return serialize_state_json(self.serialize_state())

    def export_save_code(self, secret: bytes) -> str:
        payload_json = self.serialize_state_json()
        # Security model: this is integrity protection against client-side payload editing.
        # It does not protect against users who can modify/replace the server code or secret.
        return export_save_code(payload_json, secret, version=SAVE_STATE_VERSION)

    @classmethod
    def from_serialized_state(cls, payload: dict) -> "FeaturedMatchWebSession":
        try:
            if payload.get("version") != SAVE_STATE_VERSION:
                raise ValueError("Unsupported save state version")

            session = cls(
                seed=int(payload["seed"]),
                rounds=int(payload["rounds"]),
                survivor_count=int(payload.get("survivor_count", 4)),
                floor_cap=int(payload.get("floor_cap", 20)),
                mutation_rate=float(payload.get("mutation_rate", 0.15)),
                descendant_mutation_bonus=float(payload.get("descendant_mutation_bonus", 1.75)),
            )
            rng_state = deserialize_rng_state(payload["rng_state"])
            session.rng.setstate(rng_state)

            session.snapshot = deserialize_run_snapshot(payload["snapshot"])
            session.player = deserialize_agent(payload["player"], powerup_types=_POWERUP_TYPES)
            session.opponent = deserialize_agent(payload["opponent"], powerup_types=_POWERUP_TYPES)
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
            session._upcoming_phase = payload.get("upcoming_phase")
            session._pending_successor_reason = payload.get("pending_successor_reason")
            session._powerup_offers = [deserialize_powerup(entry, _POWERUP_TYPES) for entry in payload.get("powerup_offers", [])]
            session._genome_offers = [deserialize_genome_edit(entry, _GENOME_EDIT_TYPES) for entry in payload.get("genome_offers", [])]
            session._successor_candidates = [deserialize_agent(entry, powerup_types=_POWERUP_TYPES) for entry in payload.get("successor_candidates", [])]
            session._branch_roster = [deserialize_agent(entry, powerup_types=_POWERUP_TYPES) for entry in payload.get("branch_roster", [])]
            session._dynasty_state = build_dataclass(DynastyState, payload.get("dynasty_state", {})) if payload.get("dynasty_state") else initial_dynasty_state()
            active_floor_event = payload.get("active_floor_event")
            session._active_floor_event = build_dataclass(ActiveFloorEvent, active_floor_event) if active_floor_event else None
            session._previous_event_key = payload.get("previous_event_key")
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
            session.session.current_decision = deserialize_decision(decision_type_name, decision_payload, _DECISION_TYPES)
            session.session._expected_action_types = resolve_expected_action_types(
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
        payload = import_save_code(save_code, secret, version=SAVE_STATE_VERSION)
        return cls.from_serialized_state(payload)


    def start(self) -> None:
        self.session.start(self.snapshot)
        self.snapshot.header = self.snapshot.header or None
        self.snapshot.current_floor = self.floor_number
        self.snapshot.current_phase = "ecosystem"
        self.snapshot.house_doctrine_family = self.snapshot.house_doctrine_family or seed_run_house_doctrine(seed=self.seed)
        doctrine_state = derive_doctrine_state(
            owned_powerups=tuple(self.player.powerups),
            genome=self.player.genome,
            house_doctrine_family=self.snapshot.house_doctrine_family,
        )
        self.snapshot.primary_doctrine_family = doctrine_state.primary_doctrine_family
        self.snapshot.secondary_doctrine_family = doctrine_state.secondary_doctrine_family
        self.snapshot.dynasty_resources = dynasty_to_view(self._dynasty_state)
        self._floor_clue_log = []
        self._append_chronicle_entry(
            event_id=f"run_start:seed:{self.seed}",
            event_type="run_start",
            floor_number=self.floor_number,
            summary=run_start_summary(seed=self.seed),
        )
        self._rebuild_dynasty_board()
        self._begin_floor_event_choice()

    def submit_action(
        self,
        action: (
            ChooseFloorEventAction
            |
            ChooseRoundMoveAction
            | ChooseRoundAutopilotAction
            | ChooseRoundStanceAction
            | ChooseFloorVoteAction
            | ChoosePowerupAction
            | ChooseGenomeEditAction
            | ChooseSuccessorAction
        ),
    ) -> None:
        # Compatibility shim for direct test/session driving code that was written
        # before floor events became the first explicit decision of each floor.
        if (
            self.session.current_decision is not None
            and isinstance(self.session.current_decision, FloorEventChoiceState)
            and not isinstance(action, ChooseFloorEventAction)
        ):
            self.session.submit_action(ChooseFloorEventAction(response_index=0))
            self.advance()
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
        if isinstance(decision, FloorEventChoiceState):
            self._resolve_floor_event_choice(decision)
            return
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
        self._refresh_strategic_snapshot()
        transition_kind = self._transition_action_kind()
        transition_label = transition_action_label(transition_kind) if transition_kind is not None else None
        return {
            "status": self.session.status,
            "decision_type": type(self.session.current_decision).__name__ if self.session.current_decision else None,
            "decision": asdict(self.session.current_decision) if self.session.current_decision else None,
            "snapshot": asdict(self.snapshot),
            "pending_screen": self._pending_screen,
            "pending_message": self._pending_message,
            "transition_action_kind": transition_kind,
            "transition_action_label": transition_label,
            "transition_action_visible": transition_label is not None,
        }

    def _refresh_strategic_snapshot(self) -> None:
        self.snapshot.strategic_snapshot = refresh_strategic_snapshot(
            self.snapshot,
            player_name=self.player.name,
            floor_number=self.floor_number,
        )


    def _transition_action_kind(self) -> str | None:
        if self.session.current_decision is not None:
            return None
        if self._pending_screen == "floor_summary":
            return "successor_review" if self._should_review_successor_options() else "reward_selection"
        if self._pending_screen == "civil_war_transition":
            return "civil_war_start"
        if self.session.status == "running":
            return "generic"
        return None

    def _lineage_survivors(self) -> list[Agent]:
        player_lineage_id = self.player.lineage_id
        return [agent for agent in self._branch_roster if agent.lineage_id == player_lineage_id]

    def _current_host_survived_floor(self) -> bool:
        return any(agent.agent_id == self.player.agent_id for agent in self._branch_roster)

    def _should_review_successor_options(self) -> bool:
        return self._pending_successor_reason is not None

    def _post_summary_phase(self) -> str:
        return self._upcoming_phase or self.snapshot.current_phase or "ecosystem"

    def _build_civil_war_context(self, *, current_host: Agent | None) -> object:
        context = build_civil_war_context(
            branches=list(self._branch_roster),
            current_host=current_host,
            featured_inference_signals=normalize_featured_inference_signals(self._floor_clue_log),
        )
        _, doctrine_pressure_note = self._doctrine_state_framing()
        context.doctrine_pressure = [doctrine_pressure_note, *context.doctrine_pressure][:4]
        return context

    def _record_host_choice(self, *, chosen: Agent, event_id: str, floor_number: int) -> None:
        previous_host = self.player.name
        if chosen is not self.player:
            chosen.is_player = True
            self.player.is_player = False
            self.player = chosen
        summary = (
            host_hold_summary(host_name=chosen.name)
            if previous_host == chosen.name
            else host_shift_summary(previous_host=previous_host, chosen_name=chosen.name)
        )
        self._append_chronicle_entry(
            event_id=event_id,
            event_type="successor_choice",
            floor_number=floor_number,
            summary=summary,
        )

    def _complete_run(self, *, outcome: str) -> None:
        completion = RunCompletion(
            outcome=outcome,
            floor_number=self.floor_number,
            player_name=self.player.name,
            seed=self.seed,
        )
        self.snapshot.completion = completion
        self._pending_screen = None
        self._pending_message = None
        self._upcoming_phase = None
        self._append_chronicle_entry(
            event_id=f"run_outcome:{outcome}:{self.floor_number}",
            event_type="run_outcome",
            floor_number=self.floor_number,
            summary=run_outcome_summary(
                outcome=outcome,
                floor_number=self.floor_number,
                player_name=self.player.name,
            ),
        )
        self.session.complete(completion, self.snapshot)
        self.snapshot.session_status = "completed"
        self._rebuild_dynasty_board()

    @property
    def should_autopilot_featured_match(self) -> bool:
        return self._match_autopilot_active

    def _sync_dynasty_snapshot(self) -> None:
        self.snapshot.dynasty_resources = dynasty_to_view(self._dynasty_state)
        self.snapshot.active_floor_event = (
            floor_event_snapshot_state(self._active_floor_event)
            if self._active_floor_event is not None and self._active_floor_event.response is not None
            else None
        )

    def _begin_floor_event_choice(self) -> None:
        phase = self.snapshot.current_phase or "ecosystem"
        self._active_floor_event = generate_floor_event(
            self.rng,
            floor_number=self.floor_number,
            phase=phase,
            dynasty_state=self._dynasty_state,
            previous_event_key=self._previous_event_key,
        )
        self.snapshot.active_floor_event = floor_event_snapshot_state(self._active_floor_event)
        state = floor_event_choice_state(self._active_floor_event)
        self.session.begin_decision(state, (ChooseFloorEventAction,), self.snapshot)
        self.snapshot.session_status = "awaiting_decision"

    def _resolve_floor_event_choice(self, decision: FloorEventChoiceState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChooseFloorEventAction(response_index=0))
        self._active_floor_event = choose_floor_event_response(self._active_floor_event, action.response_index)
        self._previous_event_key = self._active_floor_event.template.key
        event_change = response_dynasty_modifier(self._active_floor_event)
        self._dynasty_state = adjust_dynasty_state(
            self._dynasty_state,
            legitimacy_delta=event_change.legitimacy_delta,
            cohesion_delta=event_change.cohesion_delta,
            leverage_delta=event_change.leverage_delta,
            contingencies_delta=event_change.contingencies_delta,
        )
        self._sync_dynasty_snapshot()
        self._append_chronicle_entry(
            event_id=f"floor_event:{self.floor_number}:{self._active_floor_event.template.key}",
            event_type="floor_start",
            floor_number=self.floor_number,
            summary=f"{self._active_floor_event.template.title}: {self._active_floor_event.response.name}",
            cause=self._active_floor_event.response.summary,
        )
        self._begin_featured_round_decision()

    def _begin_featured_round_decision(self) -> None:
        suggested_move = self.player.genome.choose_move(self.player_history, self.opponent_history, self.rng)
        event_prefix = clue_prefix(self._active_floor_event)
        clue_channels = featured_round_clue_channels(
            public_profile=self.opponent.public_profile,
            powerup_names=[powerup.name for powerup in self.opponent.powerups],
        )
        if event_prefix is not None:
            clue_channels = [event_prefix, *clue_channels]
        state = FeaturedRoundDecisionState(
            prompt=FeaturedMatchPrompt(
                floor_number=self.floor_number,
                masked_opponent_label=UNKNOWN_OPPONENT_LABEL,
                round_index=self.round_index,
                total_rounds=self.rounds,
                my_history=list(self.player_history),
                opp_history=list(self.opponent_history),
                my_match_score=self.player_score,
                opp_match_score=self.opponent_score,
                suggested_move=suggested_move,
                roster_entries=[],
                clue_channels=clue_channels,
                floor_clue_log=list(self._floor_clue_log),
                inference_focus=(
                    featured_round_inference_focus()
                    if self.round_index == 0
                    else featured_round_pattern_focus()
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

        player_score_context = RoundContext(
            round_index=self.round_index,
            total_rounds=self.rounds,
            my_history=list(self.player_history),
            opp_history=list(self.opponent_history),
            planned_move=player_plan,
            opp_planned_move=opponent_plan,
            combo_events=derive_round_combo_events(
                context=player_context,
                my_move=player_move,
                opp_move=opponent_move,
                my_directives=player_res.directives,
                opp_directives=opp_res.directives,
            ),
        )
        opponent_score_context = RoundContext(
            round_index=self.round_index,
            total_rounds=self.rounds,
            my_history=list(self.opponent_history),
            opp_history=list(self.player_history),
            planned_move=opponent_plan,
            opp_planned_move=player_plan,
            combo_events=derive_round_combo_events(
                context=opponent_context,
                my_move=opponent_move,
                opp_move=player_move,
                my_directives=opp_res.directives,
                opp_directives=player_res.directives,
            ),
        )

        base_p, base_o = base_payoff(player_move, opponent_move)
        p_points, o_points = base_p, base_o
        adjustments: list[ScoreAdjustment] = []
        p_points, o_points = self._apply_score(self.player, self.opponent, player_move, opponent_move, p_points, o_points, player_score_context, "player", adjustments)
        o_points, p_points = self._apply_score(self.opponent, self.player, opponent_move, player_move, o_points, p_points, opponent_score_context, "opponent", adjustments)
        p_points, player_event_bonus = apply_match_event_bonus(
            self._active_floor_event,
            owner_is_player=True,
            my_move=player_move,
            opp_move=opponent_move,
            context=player_score_context,
            my_points=p_points,
        )
        if player_event_bonus:
            source = self._active_floor_event.response.name if self._active_floor_event and self._active_floor_event.response else self._active_floor_event.template.title if self._active_floor_event else "Floor event"
            adjustments.append(ScoreAdjustment(source=source, player_delta=player_event_bonus, opponent_delta=0))
        o_points, opponent_event_bonus = apply_match_event_bonus(
            self._active_floor_event,
            owner_is_player=False,
            my_move=opponent_move,
            opp_move=player_move,
            context=opponent_score_context,
            my_points=o_points,
        )
        if opponent_event_bonus:
            source = self._active_floor_event.template.title if self._active_floor_event else "Floor event"
            adjustments.append(ScoreAdjustment(source=source, player_delta=0, opponent_delta=opponent_event_bonus))

        self.player_score += p_points
        self.opponent_score += o_points
        self.player_history.append(player_move)
        self.opponent_history.append(opponent_move)

        if self._active_floor_event is not None and self._active_floor_event.clue_reliability == "murky":
            inference_update = [
                "Signals were distorted by the floor event; branch read is noisy.",
                "Treat this clue as provisional until the summary confirms a pattern.",
            ]
        elif self._active_floor_event is not None and self._active_floor_event.clue_reliability == "clear":
            inference_update = [
                (
                    "Signal came through cleanly; the rival opener exposed a real branch tendency."
                    if self.round_index == 0
                    else "This floor is unusually readable; pattern confidence increased."
                ),
                "Carry the cleaner read into succession and threat planning.",
            ]
        else:
            inference_update = [
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
            ]

        self.snapshot.latest_featured_round = FeaturedRoundResult(
            masked_opponent_label=UNKNOWN_OPPONENT_LABEL,
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
            inference_update=inference_update,
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
            floor_label=(
                f"Floor {self.floor_number} - {self._active_floor_event.template.title}"
                if self._active_floor_event is not None
                else f"Floor {self.floor_number}"
            ),
            suggested_vote=COOPERATE,
            current_floor_score=self.player_score,
            powerups=[p.name for p in self.player.powerups],
        )
        self.session.begin_decision(FloorVoteDecisionState(prompt=vote_prompt), (ChooseFloorVoteAction,), self.snapshot)
        self.snapshot.session_status = "awaiting_decision"

    def _resolve_floor_vote(self, decision: FloorVoteDecisionState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChooseFloorVoteAction(mode="autopilot_vote"))
        base_vote = decision.prompt.suggested_vote if action.mode == "autopilot_vote" else action.vote
        if base_vote not in (COOPERATE, DEFECT):
            raise ValueError("Invalid floor vote")
        current_phase = self.snapshot.current_phase or "ecosystem"

        total_agents = len(self._branch_roster)
        referendum_context = ReferendumContext(
            floor_number=self.floor_number,
            total_agents=total_agents,
            current_floor_score=self.player_score,
        )
        directives: list[MoveDirective] = []
        for powerup in self.player.powerups:
            directives.extend(powerup.self_referendum_directives(owner=self.player, context=referendum_context))
        final_vote, _ = resolve_move(base_vote, directives)

        self._advance_branch_roster_for_floor()

        votes: dict[int, int] = {self.player.agent_id: final_vote}
        base_votes: dict[int, int] = {self.player.agent_id: base_vote}
        referendum_directives: dict[int, list[MoveDirective]] = {self.player.agent_id: directives}
        for rival in self._branch_roster:
            if rival is self.player:
                continue
            rival_base_vote = rival.genome.first_move
            rival_context = ReferendumContext(
                floor_number=self.floor_number,
                total_agents=total_agents,
                current_floor_score=rival.score,
            )
            rival_directives: list[MoveDirective] = []
            for powerup in rival.powerups:
                rival_directives.extend(powerup.self_referendum_directives(owner=rival, context=rival_context))
            rival_final_vote, _ = resolve_move(rival_base_vote, rival_directives)
            votes[rival.agent_id] = rival_final_vote
            base_votes[rival.agent_id] = rival_base_vote
            referendum_directives[rival.agent_id] = rival_directives

        cooperators = sum(1 for vote in votes.values() if vote == COOPERATE)
        defectors = sum(1 for vote in votes.values() if vote == DEFECT)
        cooperation_prevailed = cooperators >= defectors
        combo_events = derive_referendum_combo_events(
            base_vote=base_vote,
            final_vote=final_vote,
            directives=directives,
            cooperation_prevailed=cooperation_prevailed,
        )

        floor_config = self._current_floor_config()
        player_reward = floor_config.referendum_reward if cooperation_prevailed and final_vote == COOPERATE else 0
        if cooperation_prevailed and final_vote == COOPERATE:
            reward_context = ReferendumContext(
                floor_number=self.floor_number,
                total_agents=cooperators + defectors,
                current_floor_score=self.player_score,
                combo_events=combo_events,
            )
            for powerup in self.player.powerups:
                player_reward = powerup.on_referendum_reward(
                    owner=self.player,
                    my_vote=final_vote,
                    cooperation_prevailed=True,
                    current_reward=player_reward,
                    context=reward_context,
                )
        player_reward, _ = apply_referendum_event_bonus(
            self._active_floor_event,
            owner_is_player=True,
            my_vote=final_vote,
            cooperation_prevailed=cooperation_prevailed,
            current_reward=player_reward,
        )

        result = FloorVoteResult(
            floor_number=self.floor_number,
            cooperation_prevailed=cooperation_prevailed,
            cooperators=cooperators,
            defectors=defectors,
            player_vote=final_vote,
            player_reward=player_reward,
        )
        self.snapshot.floor_vote_result = result
        self.player_score += result.player_reward
        self.player.score += result.player_reward

        for rival in self._branch_roster:
            if rival is self.player:
                continue
            if cooperation_prevailed and votes[rival.agent_id] == COOPERATE:
                rival_reward = floor_config.referendum_reward
                rival_reward_context = ReferendumContext(
                    floor_number=self.floor_number,
                    total_agents=total_agents,
                    current_floor_score=rival.score,
                    combo_events=derive_referendum_combo_events(
                        base_vote=base_votes[rival.agent_id],
                        final_vote=votes[rival.agent_id],
                        directives=referendum_directives[rival.agent_id],
                        cooperation_prevailed=cooperation_prevailed,
                    ),
                )
                for powerup in rival.powerups:
                    rival_reward = powerup.on_referendum_reward(
                        owner=rival,
                        my_vote=votes[rival.agent_id],
                        cooperation_prevailed=True,
                        current_reward=rival_reward,
                        context=rival_reward_context,
                    )
                rival_reward, _ = apply_referendum_event_bonus(
                    self._active_floor_event,
                    owner_is_player=False,
                    my_vote=votes[rival.agent_id],
                    cooperation_prevailed=cooperation_prevailed,
                    current_reward=rival_reward,
                )
                rival.score += rival_reward

        ranked = self._rank_agents(self._branch_roster)
        summary_agents = self._branch_floor_ranking(ranked)

        synthesis = synthesize_floor_summary(
            floor_number=self.floor_number,
            summary_agents=summary_agents,
            player=self.player,
            floor_clue_log=self._floor_clue_log,
            continuity=FloorContinuityContext(
                previous_floor_names=self._previous_floor_names,
                branch_continuity_streaks=self._branch_continuity_streaks,
                previous_branch_stats=self._previous_branch_stats,
                previous_pressure_levels=self._previous_pressure_levels,
                previous_central_rival=self._previous_central_rival,
            ),
        )
        self.snapshot.floor_summary = synthesis.summary
        self._previous_floor_names = synthesis.continuity.previous_floor_names
        self._branch_continuity_streaks = synthesis.continuity.branch_continuity_streaks
        self._previous_branch_stats = synthesis.continuity.previous_branch_stats
        self._previous_pressure_levels = synthesis.continuity.previous_pressure_levels
        self._current_floor_central_rival = synthesis.central_rival_name
        self._current_floor_new_central_rival = synthesis.current_floor_new_central_rival
        self._previous_central_rival = synthesis.continuity.previous_central_rival
        heir_pressure = synthesis.summary.heir_pressure

        featured_note = (
            self.snapshot.floor_summary.featured_inference_summary[0]
            if self.snapshot.floor_summary.featured_inference_summary
            else no_solid_clue_read_this_floor()
        )
        doctrine_note = heir_pressure.branch_doctrine if heir_pressure is not None else unclear_playstyle_trend()
        doctrine_chip, doctrine_pressure_note = self._doctrine_state_framing()
        self._append_chronicle_entry(
            event_id=f"floor_complete:{self.floor_number}",
            event_type="floor_complete",
            floor_number=self.floor_number,
            summary=floor_complete_summary(
                floor_number=self.floor_number,
                player_score=self.player_score,
                featured_note=featured_note,
            ),
        )
        self._append_chronicle_entry(
            event_id=f"doctrine_pivot:{self.floor_number}",
            event_type="doctrine_pivot",
            floor_number=self.floor_number,
            summary=doctrine_shift_summary(doctrine_note=doctrine_note, doctrine_chip=doctrine_chip),
            cause=self._lineage_cause_phrase(
                self.snapshot.floor_summary.featured_inference_summary,
                doctrine_note,
            ),
        )
        if current_phase == "ecosystem":
            survivors, _ = self._evolution.split_population(ranked)
        else:
            survivors, _ = self._evolution.split_population_civil_war(ranked)

        lineage_survivors = [
            agent
            for agent in survivors
            if agent.lineage_id == self.player.lineage_id
        ]
        current_host_survived = any(agent.agent_id == self.player.agent_id for agent in lineage_survivors)
        self._dynasty_state = update_after_floor(
            self._dynasty_state,
            ranked=ranked,
            player=self.player,
            vote_result=result,
            phase=current_phase,
            host_changed=not current_host_survived,
        )
        commitment_change = response_commitment_modifier(
            self._active_floor_event,
            round_history=list(self.player_history),
            final_vote=final_vote,
        )
        self._dynasty_state = adjust_dynasty_state(
            self._dynasty_state,
            legitimacy_delta=commitment_change.legitimacy_delta,
            cohesion_delta=commitment_change.cohesion_delta,
            leverage_delta=commitment_change.leverage_delta,
            contingencies_delta=commitment_change.contingencies_delta,
        )
        self._sync_dynasty_snapshot()

        if not lineage_survivors:
            self._branch_roster = []
            self._successor_candidates = []
            self.snapshot.successor_options = None
            self._complete_run(outcome="eliminated")
            return

        self._successor_candidates = []
        self.snapshot.successor_options = None
        self.snapshot.civil_war_context = None
        self._pending_successor_reason = None
        self._upcoming_phase = current_phase

        if current_phase == "ecosystem":
            self._branch_roster = list(survivors)
            outsiders_remaining = [
                agent
                for agent in survivors
                if agent.lineage_id != self.player.lineage_id
            ]
            if not outsiders_remaining:
                if len(lineage_survivors) == 1:
                    self._branch_roster = list(lineage_survivors)
                    self._record_host_choice(
                        chosen=lineage_survivors[0],
                        event_id=f"successor_choice:{self.floor_number}:sole_survivor",
                        floor_number=self.floor_number,
                    )
                    self._dynasty_state = set_claimant(self._dynasty_state, agent=lineage_survivors[0], allow_contingency=False)
                    self._sync_dynasty_snapshot()
                    self._complete_run(outcome="victory")
                    return
                self._branch_roster = list(lineage_survivors)
                self._upcoming_phase = "civil_war"
                self._pending_successor_reason = "civil_war_claimant"
                current_host = self.player if current_host_survived else None
                self.snapshot.civil_war_context = self._build_civil_war_context(current_host=current_host)
            elif not current_host_survived:
                self._pending_successor_reason = "host_eliminated"
        else:
            self._branch_roster = list(lineage_survivors)
            claimant_alive = is_claimant_alive(self._dynasty_state, lineage_survivors)
            if not claimant_alive:
                if can_use_contingency(self._dynasty_state):
                    self._dynasty_state = spend_contingency(self._dynasty_state)
                    self._pending_successor_reason = "civil_war_contingency"
                    self._sync_dynasty_snapshot()
                else:
                    self._complete_run(outcome="eliminated")
                    return
            elif len(lineage_survivors) == 1:
                self._record_host_choice(
                    chosen=lineage_survivors[0],
                    event_id=f"civil_war_victory:{self.floor_number}",
                    floor_number=self.floor_number,
                )
                self._complete_run(outcome="victory")
                return

        next_step_kind = "successor_review" if self._should_review_successor_options() else "reward_selection"
        self.snapshot.session_status = "running"
        self._pending_screen = "floor_summary"
        self._pending_message = pending_floor_complete_message(
            floor_number=self.floor_number,
            next_step_label=transition_action_label(next_step_kind),
        )
        self._rebuild_dynasty_board()

    def _begin_post_summary_flow(self) -> None:
        lineage_survivors = self._lineage_survivors()
        if not lineage_survivors:
            return
        if self._pending_successor_reason is not None and len(lineage_survivors) == 1:
            sole_survivor = lineage_survivors[0]
            self._record_host_choice(
                chosen=sole_survivor,
                event_id=f"successor_choice:{self.floor_number}:{self._pending_successor_reason}:sole",
                floor_number=self.floor_number,
            )
            if self._post_summary_phase() == "civil_war":
                self._dynasty_state = set_claimant(self._dynasty_state, agent=sole_survivor, allow_contingency=False)
            self._pending_successor_reason = None
            self._sync_dynasty_snapshot()
            if self._post_summary_phase() == "civil_war":
                self.snapshot.floor_identity = None
                self.snapshot.civil_war_context = self._build_civil_war_context(current_host=self.player)
            else:
                self.snapshot.floor_identity = self._build_next_floor_identity_for_agent(sole_survivor)
            self._begin_powerup_choice()
            return

        if self._pending_successor_reason is not None:
            self._successor_candidates = self._build_successor_candidates()
            candidates = []
            top_score = max((agent.score for agent in self._successor_candidates), default=0)
            threat_tags: set[str] = set()
            lineage_doctrine: str | None = None
            featured_signals = normalize_featured_inference_signals(self._floor_clue_log)
            if self.snapshot.floor_summary and self.snapshot.floor_summary.heir_pressure:
                lineage_doctrine = self.snapshot.floor_summary.heir_pressure.branch_doctrine
                for threat in self.snapshot.floor_summary.heir_pressure.future_threats:
                    threat_tags.update(threat.tags)
            if self._active_floor_event is not None:
                threat_tags.update(self._active_floor_event.threat_tags)
            doctrine_chip, _ = self._doctrine_state_framing()
            for agent in self._successor_candidates:
                identity = analyze_agent_identity(agent)
                assessment = assess_successor_candidate(
                    agent,
                    top_score=top_score,
                    phase=self._post_summary_phase(),
                    threat_tags=threat_tags,
                    lineage_doctrine=(f"{lineage_doctrine} | {doctrine_chip}" if lineage_doctrine else doctrine_chip),
                )
                inference_brief = successor_featured_inference_brief(
                    candidate_tags=identity.tags,
                    featured_inference_signals=featured_signals,
                )
                candidates.append(
                    to_successor_candidate_view(
                        agent=agent,
                        identity=identity,
                        assessment=assessment,
                        featured_inference_context=successor_featured_inference_context(
                            candidate_tags=identity.tags,
                            featured_inference_signals=featured_signals,
                        ),
                        featured_inference_brief=inference_brief,
                    )
                )
            civil_war_pressure = civil_war_pressure_for_threat_tags(threat_tags)
            state = SuccessorChoiceState(
                floor_number=self.floor_number,
                candidates=candidates,
                current_phase=self._post_summary_phase(),
                lineage_doctrine=(f"{lineage_doctrine} | {doctrine_chip}" if lineage_doctrine else doctrine_chip),
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
                summary=successor_pressure_summary(
                    civil_war_pressure=civil_war_pressure,
                    threat_tags=sorted(threat_tags),
                ),
                cause=self._lineage_cause_phrase(
                    list(self.snapshot.floor_summary.featured_inference_summary) if self.snapshot.floor_summary else [],
                    successor_pressure_cause_fallback(threat_tags=sorted(threat_tags)),
                ),
            )
            self.session.begin_decision(state, (ChooseSuccessorAction,), self.snapshot)
            self.snapshot.session_status = "awaiting_decision"
            return

        self.snapshot.successor_options = None
        self._successor_candidates = []
        if self._post_summary_phase() == "civil_war":
            self.snapshot.floor_identity = None
            self.snapshot.civil_war_context = self._build_civil_war_context(current_host=self.player)
        else:
            self.snapshot.floor_identity = self._build_next_floor_identity_for_agent(self.player)
        self._begin_powerup_choice()

    def _begin_powerup_choice(self) -> None:
        phase = self._post_summary_phase()
        generated = generate_powerup_offer_set(
            3,
            self.rng,
            context=PowerupOfferContext(
                owned_powerups=tuple(self.player.powerups),
                genome=self.player.genome,
                floor_number=self.floor_number,
                phase=phase,
                house_doctrine_family=self.snapshot.house_doctrine_family,
                primary_doctrine_family=self.snapshot.primary_doctrine_family,
                secondary_doctrine_family=self.snapshot.secondary_doctrine_family,
                event_bias_families=favored_offer_biases(self._active_floor_event),
            ),
        )
        self._powerup_offers = [entry.powerup for entry in generated]
        offers = [
            to_powerup_offer_view(
                entry.powerup,
                relevance_hint=offer_category_hint(entry.category),
                fit_detail=offer_fit_detail(entry.category),
                house_doctrine_family=self.snapshot.house_doctrine_family,
                primary_doctrine_family=self.snapshot.primary_doctrine_family,
                secondary_doctrine_family=self.snapshot.secondary_doctrine_family,
            )
            for entry in generated
        ]
        state = PowerupChoiceState(floor_number=self.floor_number, offers=offers)
        self.session.begin_decision(state, (ChoosePowerupAction,), self.snapshot)
        self.snapshot.session_status = "awaiting_decision"

    def _resolve_successor_choice(self, decision: SuccessorChoiceState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChooseSuccessorAction(candidate_index=0))
        if action.candidate_index < 0 or action.candidate_index >= len(self._successor_candidates):
            raise ValueError("Invalid successor index")
        chosen = self._successor_candidates[action.candidate_index]
        chosen_view = decision.candidates[action.candidate_index]
        reason = self._pending_successor_reason
        self._record_host_choice(
            chosen=chosen,
            event_id=f"successor_choice:{self.floor_number}:{reason or 'review'}:{action.candidate_index}",
            floor_number=self.floor_number,
        )
        self._pending_successor_reason = None

        if self._post_summary_phase() == "civil_war":
            self._dynasty_state = set_claimant(
                self._dynasty_state,
                agent=chosen,
                allow_contingency=True,
            )
            self.snapshot.floor_identity = None
            self.snapshot.civil_war_context = self._build_civil_war_context(current_host=chosen)
            self._pending_screen = None
            self._pending_message = None
            self._begin_powerup_choice()
        else:
            self.snapshot.current_phase = "ecosystem"
            self.snapshot.civil_war_context = None
            self.snapshot.floor_identity = self._build_next_floor_identity(decision=decision, chosen=chosen_view)
            self._pending_screen = None
            self._pending_message = None
            self._begin_powerup_choice()
        self._sync_dynasty_snapshot()
        self._rebuild_dynasty_board()


    def _doctrine_state_framing(self) -> tuple[str, str]:
        return doctrine_commitment_summary(
            house=self.snapshot.house_doctrine_family,
            primary=self.snapshot.primary_doctrine_family,
            secondary=self.snapshot.secondary_doctrine_family,
        )

    def _build_next_floor_identity(self, decision: SuccessorChoiceState, chosen: SuccessorCandidateView) -> FloorIdentityState:
        threat_profile = list(decision.threat_profile or [])
        pressure_label = floor_pressure_label(decision.civil_war_pressure)
        top_threat = threat_profile[0] if threat_profile else dominant_pressure_fallback()
        heir_tag = chosen.tags[0] if chosen.tags else heir_tag_fallback()
        dominant_pressure = top_threat if top_threat != dominant_pressure_fallback() else heir_tag
        clue_signal = (decision.featured_inference_summary[0] if decision.featured_inference_summary else None)
        doctrine = decision.lineage_doctrine or chosen.branch_doctrine
        floor_summary = self.snapshot.floor_summary
        branch_focus = None
        if floor_summary and floor_summary.heir_pressure and floor_summary.heir_pressure.future_threats:
            branch_focus = floor_summary.heir_pressure.future_threats[0]

        chosen_cause = (chosen.shaping_causes[0] if chosen.shaping_causes else chosen.succession_pitch).strip().rstrip(".")
        focus_name = branch_focus.name if branch_focus is not None else chosen.name
        focus_role = branch_focus.branch_role.lower() if branch_focus is not None else chosen.branch_role.lower()
        pressure_reason = floor_identity_pressure_reason(
            dominant_pressure=dominant_pressure,
            focus_name=focus_name,
            focus_role=focus_role,
            chosen_name=chosen.name,
        )

        attractive_focus = (chosen.why_now or chosen.attractive_now).lower()
        if len(attractive_focus) > 44:
            attractive_focus = attractive_focus[:41].rstrip() + "..."
        danger_focus = (chosen.watch_out or chosen.danger_later).lower()
        if len(danger_focus) > 44:
            danger_focus = danger_focus[:41].rstrip() + "..."
        strategic_focus = floor_identity_focus(
            chosen_name=chosen.name,
            attractive_focus=attractive_focus,
            danger_focus=danger_focus,
        )
        if clue_signal is not None:
            clue_focus = clue_signal.split("|", 1)[0].strip().rstrip(".")
            if len(clue_focus) > 44:
                clue_focus = clue_focus[:41].rstrip() + "..."
            strategic_focus = floor_identity_focus_with_clue(base_focus=strategic_focus, clue_focus=clue_focus)
        elif chosen_cause:
            cause_focus = chosen_cause
            if len(cause_focus) > 44:
                cause_focus = cause_focus[:41].rstrip() + "..."
            strategic_focus = floor_identity_focus_with_cause(base_focus=strategic_focus, cause_focus=cause_focus)

        if len(strategic_focus) > 160:
            strategic_focus = strategic_focus[:157].rstrip() + "..."

        headline = floor_identity_headline(
            pressure_label=pressure_label,
            chosen_name=chosen.name,
            branch_role=chosen.branch_role,
        )
        return FloorIdentityState(
            target_floor=self.floor_number + 1,
            host_name=chosen.name,
            headline=headline,
            pressure_label=pressure_label,
            dominant_pressure=dominant_pressure,
            pressure_reason=pressure_reason,
            lineage_direction=lineage_direction_text(doctrine=doctrine),
            strategic_focus=strategic_focus,
            key_signal=clue_signal,
        )

    def _build_next_floor_identity_for_agent(self, chosen: Agent) -> FloorIdentityState:
        floor_summary = self.snapshot.floor_summary
        threat_tags: set[str] = set()
        lineage_doctrine: str | None = None
        featured_inference_summary = list(floor_summary.featured_inference_summary) if floor_summary else []
        if floor_summary and floor_summary.heir_pressure:
            lineage_doctrine = floor_summary.heir_pressure.branch_doctrine
            for threat in floor_summary.heir_pressure.future_threats:
                threat_tags.update(threat.tags)
        if self._active_floor_event is not None:
            threat_tags.update(self._active_floor_event.threat_tags)

        doctrine_chip, _ = self._doctrine_state_framing()
        identity = analyze_agent_identity(chosen)
        assessment = assess_successor_candidate(
            chosen,
            top_score=max((agent.score for agent in self._lineage_survivors()), default=chosen.score),
            phase=self._post_summary_phase(),
            threat_tags=threat_tags,
            lineage_doctrine=(f"{lineage_doctrine} | {doctrine_chip}" if lineage_doctrine else doctrine_chip),
        )
        candidate_view = to_successor_candidate_view(
            agent=chosen,
            identity=identity,
            assessment=assessment,
            featured_inference_context=successor_featured_inference_context(
                candidate_tags=identity.tags,
                featured_inference_signals=normalize_featured_inference_signals(self._floor_clue_log),
            ),
            featured_inference_brief=successor_featured_inference_brief(
                candidate_tags=identity.tags,
                featured_inference_signals=normalize_featured_inference_signals(self._floor_clue_log),
            ),
        )
        synthetic_decision = SuccessorChoiceState(
            floor_number=self.floor_number,
            candidates=[candidate_view],
            current_phase=self._post_summary_phase(),
            lineage_doctrine=(f"{lineage_doctrine} | {doctrine_chip}" if lineage_doctrine else doctrine_chip),
            threat_profile=sorted(threat_tags),
            civil_war_pressure=civil_war_pressure_for_threat_tags(threat_tags),
            featured_inference_summary=featured_inference_summary,
        )
        return self._build_next_floor_identity(decision=synthetic_decision, chosen=candidate_view)

    def _begin_civil_war_floor(self) -> None:
        self.floor_number += 1
        self.snapshot.current_floor = self.floor_number
        self.snapshot.current_phase = "civil_war"
        self.snapshot.floor_identity = None
        self.snapshot.successor_options = None
        self._upcoming_phase = None
        self._reset_floor_state_for_new_match()
        self.opponent = self._select_floor_opponent()

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
            summary=civil_war_round_start_summary(opponent_name=self.opponent.name),
            cause=self._lineage_cause_phrase(
                doctrine_pressure,
                civil_war_started_fallback(),
            ),
        )
        self._begin_floor_event_choice()

    def _begin_next_ecosystem_floor(self) -> None:
        self.floor_number += 1
        self.snapshot.current_floor = self.floor_number
        self.snapshot.current_phase = "ecosystem"
        self.snapshot.civil_war_context = None
        self.snapshot.successor_options = None
        self._dynasty_state = clear_claimant(self._dynasty_state)
        self._sync_dynasty_snapshot()
        self._upcoming_phase = None
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
            summary=ecosystem_floor_start_summary(
                floor_number=self.floor_number,
                identity_note=identity_note,
            ),
        )
        self._begin_floor_event_choice()

    def _reset_floor_state_for_new_match(self) -> None:
        self.round_index = 0
        self.player_history = []
        self.opponent_history = []
        self.player_score = 0
        self.opponent_score = 0
        self._active_floor_event = None
        self.snapshot.floor_vote_result = None
        self.snapshot.floor_summary = None
        self.snapshot.active_floor_event = None
        self._floor_clue_log = []
        for agent in self._branch_roster:
            agent.reset_for_floor()

    def _resolve_powerup_choice(self, decision: PowerupChoiceState) -> None:
        action = self.session.resolve_current_decision(lambda _: ChoosePowerupAction(offer_index=0))
        if action.offer_index < 0 or action.offer_index >= len(self._powerup_offers):
            raise ValueError("Invalid powerup index")
        chosen_powerup = self._powerup_offers[action.offer_index]
        self.player.powerups.append(chosen_powerup)
        house = self.snapshot.house_doctrine_family or seed_run_house_doctrine(seed=self.seed)
        self.snapshot.house_doctrine_family = house
        doctrine_state = derive_doctrine_state(
            owned_powerups=tuple(self.player.powerups),
            genome=self.player.genome,
            house_doctrine_family=house,
        )
        self.snapshot.primary_doctrine_family = doctrine_state.primary_doctrine_family
        self.snapshot.secondary_doctrine_family = doctrine_state.secondary_doctrine_family

        self._genome_offers = generate_genome_edit_offers(3, self.rng)
        state = GenomeEditChoiceState(
            floor_number=self.floor_number,
            current_summary=self.player.genome.summary(),
            offers=[
                to_genome_edit_offer_view(
                    offer,
                    current_summary=self.player.genome.summary(),
                    projected_summary=offer.apply(self.player.genome).summary(),
                    house_doctrine_family=self.snapshot.house_doctrine_family,
                    primary_doctrine_family=self.snapshot.primary_doctrine_family,
                    secondary_doctrine_family=self.snapshot.secondary_doctrine_family,
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

        floor_config = self._current_floor_config()
        self._progression.grant_ai_powerups(
            survivors=self._branch_roster,
            player=self.player,
            floor_config=floor_config,
        )

        current_phase = self.snapshot.current_phase or "ecosystem"
        upcoming_phase = self._post_summary_phase()
        if upcoming_phase == "ecosystem":
            if self.floor_number >= self.floor_cap:
                self._complete_run(outcome="capped")
            else:
                self._branch_roster = self._evolution.repopulate(
                    survivors=self._branch_roster,
                    target_size=self._target_population_size,
                )
                self._begin_next_ecosystem_floor()
                self.snapshot.session_status = "awaiting_decision"
        elif current_phase == "ecosystem":
            if len(self._branch_roster) == 1:
                self._complete_run(outcome="victory")
            else:
                if self.snapshot.civil_war_context is None:
                    self.snapshot.civil_war_context = self._build_civil_war_context(current_host=self.player)
                self.snapshot.floor_identity = None
                self.snapshot.floor_vote_result = None
                self._pending_screen = "civil_war_transition"
                self._pending_message = pending_civil_war_start_message(thesis=self.snapshot.civil_war_context.thesis)
                self._append_chronicle_entry(
                    event_id=f"phase_transition:civil_war:{self.floor_number + 1}",
                    event_type="phase_transition",
                    floor_number=self.floor_number + 1,
                    summary=civil_war_started_summary(thesis=self.snapshot.civil_war_context.thesis),
                    cause=self._lineage_cause_phrase(
                        list(self.snapshot.civil_war_context.doctrine_pressure),
                        self.snapshot.civil_war_context.thesis,
                    ),
                )
                self.snapshot.session_status = "running"
                self._upcoming_phase = None
        else:
            if len(self._branch_roster) == 1:
                self._complete_run(outcome="victory")
            else:
                self._begin_civil_war_floor()
                self.snapshot.session_status = "awaiting_decision"
        self._rebuild_dynasty_board()

    def _rebuild_dynasty_board(self) -> None:
        self.snapshot.dynasty_board = rebuild_dynasty_board(
            DynastyBoardBuildContext(
                snapshot=self.snapshot,
                player=self.player,
                opponent=self.opponent,
                successor_candidates=self._successor_candidates,
                current_floor_central_rival=self._current_floor_central_rival,
                current_floor_new_central_rival=self._current_floor_new_central_rival,
            )
        )

    def _lineage_cause_phrase(self, shaping_causes: list[str], fallback: str) -> str:
        return lineage_cause_phrase(shaping_causes, fallback)


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
        featured_pair = frozenset((self.player.agent_id, self.opponent.agent_id))

        # The featured pairing is already played interactively in web flow.
        # Write those authoritative featured results into the roster exactly once.
        self.player.score = self.player_score
        self.opponent.score = self.opponent_score
        self.player.wins = 0
        self.opponent.wins = 0
        if self.player_score > self.opponent_score:
            self.player.wins = 1
        elif self.opponent_score > self.player_score:
            self.opponent.wins = 1

        floor_config = self._current_floor_config()
        for left_index, left in enumerate(self._branch_roster):
            for right in self._branch_roster[left_index + 1 :]:
                if frozenset((left.agent_id, right.agent_id)) == featured_pair:
                    continue
                result = self._tournament.play_match(left=left, right=right, rounds_per_match=floor_config.rounds_per_match)
                left.score += result.left_score
                right.score += result.right_score
                if result.left_score > result.right_score:
                    left.wins += 1
                elif result.right_score > result.left_score:
                    right.wins += 1

    def _rank_agents(self, agents: list[Agent]) -> list[Agent]:
        return sorted(agents, key=lambda agent: (agent.score, agent.wins, -agent.agent_id), reverse=True)

    def _branch_floor_ranking(self, ranked: list[Agent] | None = None) -> list[Agent]:
        ranked_agents = self._rank_agents(self._branch_roster if ranked is None else ranked)
        if len(ranked_agents) <= 4:
            return ranked_agents
        top_agents = list(ranked_agents[:4])
        if any(agent.agent_id == self.player.agent_id for agent in top_agents):
            return top_agents
        current_host = next((agent for agent in ranked_agents if agent.agent_id == self.player.agent_id), None)
        if current_host is None:
            return top_agents
        return self._rank_agents([*top_agents[:3], current_host])

    def _current_floor_config(self):
        config = self._progression.build_floor_config(self.floor_number)
        config.rounds_per_match = self.rounds
        return config

    def _select_floor_opponent(self) -> Agent:
        rivals = [agent for agent in self._branch_roster if agent is not self.player]
        if not rivals:
            return Agent(name=CIVIL_WAR_RIVAL_NAME, genome=self._opponent_genome())
        opponent = max(rivals, key=lambda agent: (agent.score, agent.wins, -agent.agent_id))
        opponent.is_player = False
        return opponent

    def _build_successor_candidates(self) -> list[Agent]:
        lineage_branches = [
            agent
            for agent in self._branch_roster
            if agent.lineage_id == self.player.lineage_id
        ]
        lineage_branches.sort(key=lambda agent: (agent.score, agent.wins, -agent.agent_id), reverse=True)
        return lineage_branches[:4]

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
