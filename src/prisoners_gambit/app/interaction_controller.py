from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from prisoners_gambit.core.analysis import analyze_agent_identity
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
    DecisionState,
    FeaturedRoundDecisionState,
    FeaturedRoundStanceView,
    FloorRosterEntryView,
    FloorRosterState,
    FloorSummaryEntryView,
    FloorSummaryState,
    FloorVoteDecisionState,
    FloorVoteResult,
    GenomeEditChoiceState,
    GenomeEditOfferView,
    PlayerAction,
    PowerupChoiceState,
    PowerupOfferView,
    RunCompletion,
    RunHeaderState,
    RunSnapshot,
    SessionStatus,
    SuccessorCandidateView,
    SuccessorChoiceState,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.ui.renderers import Renderer


@dataclass(slots=True)
class RunSession:
    status: SessionStatus = "running"
    current_decision: DecisionState | None = None
    latest_snapshot: RunSnapshot = field(default_factory=RunSnapshot)
    completion: RunCompletion | None = None
    _queued_action: PlayerAction | None = None
    _expected_action_types: tuple[type, ...] = ()

    def start(self, snapshot: RunSnapshot) -> None:
        self.status = "running"
        self.current_decision = None
        self.latest_snapshot = snapshot
        self.completion = None
        self._queued_action = None
        self._expected_action_types = ()

    def update_snapshot(self, snapshot: RunSnapshot) -> None:
        self.latest_snapshot = snapshot

    def begin_decision(self, state: DecisionState, expected_types: tuple[type, ...], snapshot: RunSnapshot) -> None:
        if self.status == "completed":
            raise RuntimeError("Cannot begin decision for completed session.")
        self.status = "awaiting_decision"
        self.current_decision = state
        self._expected_action_types = expected_types
        self.latest_snapshot = snapshot

    def submit_action(self, action: PlayerAction) -> None:
        if self.status != "awaiting_decision":
            raise ValueError("Session is not awaiting a decision.")
        if self._expected_action_types and not isinstance(action, self._expected_action_types):
            raise ValueError(f"Invalid action type for current decision: {type(action).__name__}")
        self._queued_action = action

    def resolve_current_decision(self, default_resolver: Callable[[DecisionState], PlayerAction]) -> PlayerAction:
        if self.status != "awaiting_decision" or self.current_decision is None:
            raise RuntimeError("No active decision to resolve.")

        if self._queued_action is not None:
            action = self._queued_action
            self._queued_action = None
        else:
            action = default_resolver(self.current_decision)
            if self._expected_action_types and not isinstance(action, self._expected_action_types):
                raise ValueError(f"Resolver returned invalid action type: {type(action).__name__}")

        self.status = "running"
        self.current_decision = None
        self._expected_action_types = ()
        return action

    def complete(self, completion: RunCompletion, snapshot: RunSnapshot) -> None:
        self.status = "completed"
        self.current_decision = None
        self._expected_action_types = ()
        self._queued_action = None
        self.completion = completion
        self.latest_snapshot = snapshot


@dataclass(slots=True)
class InteractionController:
    renderer: Renderer
    snapshot: RunSnapshot = field(default_factory=RunSnapshot)
    session: RunSession = field(default_factory=RunSession)
    _autopilot_featured_match: bool = False
    _featured_stance: FeaturedRoundStanceView | None = None
    _last_manual_move: int | None = None

    def __post_init__(self) -> None:
        self.session.start(self.snapshot)

    def show_run_header(self, seed: int | None) -> None:
        self.snapshot.header = RunHeaderState(seed=seed)
        self._sync_session_snapshot()
        self.renderer.show_run_header(seed)

    def set_floor_context(self, floor_number: int, phase: str) -> None:
        self.snapshot.current_floor = floor_number
        self.snapshot.current_phase = "civil_war" if phase == "civil_war" else "ecosystem"
        self._sync_session_snapshot()

    def set_floor_roster(self, floor_number: int, roster_entries) -> None:
        self.snapshot.floor_roster = FloorRosterState(
            floor_number=floor_number,
            roster_entries=[
                FloorRosterEntryView(
                    name=entry.name,
                    public_profile=entry.public_profile,
                    known_powerups=list(entry.known_powerups),
                    tags=list(entry.tags),
                    descriptor=entry.descriptor,
                )
                for entry in roster_entries
            ],
        )
        self._sync_session_snapshot()

    def set_floor_summary(self, floor_number: int, ranked: list[Agent]) -> None:
        entries: list[FloorSummaryEntryView] = []
        for agent in ranked:
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
                    powerups=[powerup.name for powerup in agent.powerups],
                )
            )
        self.snapshot.floor_summary = FloorSummaryState(floor_number=floor_number, entries=entries)
        self._sync_session_snapshot()

    def set_floor_vote_result(self, result: FloorVoteResult) -> None:
        self.snapshot.floor_vote_result = result
        self._sync_session_snapshot()

    def complete_run(self, outcome: str, floor_number: int, player_name: str, seed: int | None) -> None:
        completion = RunCompletion(
            outcome="victory" if outcome == "victory" else "eliminated",
            floor_number=floor_number,
            player_name=player_name,
            seed=seed,
        )
        self.snapshot.completion = completion
        self.snapshot.session_status = "completed"
        self.session.complete(completion, self.snapshot)

    def submit_action(self, action: PlayerAction) -> None:
        self.session.submit_action(action)

    def get_status(self) -> SessionStatus:
        return self.session.status

    def get_current_decision(self) -> DecisionState | None:
        return self.session.current_decision

    def get_latest_snapshot(self) -> RunSnapshot:
        return self.session.latest_snapshot

    def can_auto_resolve_featured_round(self) -> bool:
        return self._autopilot_featured_match or self._featured_stance is not None

    def resolve_featured_round_automation(self, state: FeaturedRoundDecisionState) -> int:
        prompt = state.prompt
        if self._autopilot_featured_match:
            return prompt.suggested_move
        if self._featured_stance is None:
            return prompt.suggested_move

        stance = self._featured_stance.stance
        if stance == "cooperate_until_betrayed":
            move = DEFECT if prompt.opp_history and prompt.opp_history[-1] == DEFECT else COOPERATE
        elif stance == "defect_until_punished":
            move = COOPERATE if prompt.opp_history and prompt.opp_history[-1] == DEFECT else DEFECT
        elif stance == "follow_autopilot_for_n_rounds":
            move = prompt.suggested_move
            self._decrement_stance_rounds()
        elif stance == "lock_last_manual_move_for_n_rounds":
            move = self._featured_stance.locked_move if self._featured_stance.locked_move is not None else prompt.suggested_move
            self._decrement_stance_rounds()
        else:
            move = prompt.suggested_move

        self.snapshot.active_featured_stance = self._featured_stance
        self._sync_session_snapshot()
        return move

    def choose_round_move(self, state: FeaturedRoundDecisionState) -> int:
        self._begin_decision(
            state,
            (ChooseRoundMoveAction, ChooseRoundAutopilotAction, ChooseRoundStanceAction),
        )
        action = self.session.resolve_current_decision(self._resolve_featured_round_decision)
        self._sync_session_snapshot()

        if isinstance(action, ChooseRoundMoveAction):
            self._autopilot_featured_match = False
            self._featured_stance = None
            self.snapshot.active_featured_stance = None
            self._last_manual_move = action.move
            self._sync_session_snapshot()
            return action.move

        if isinstance(action, ChooseRoundAutopilotAction):
            if action.mode == "autopilot_match":
                self._autopilot_featured_match = True
                self._featured_stance = None
                self.snapshot.active_featured_stance = None
                self._sync_session_snapshot()
            return state.prompt.suggested_move

        if isinstance(action, ChooseRoundStanceAction):
            self._autopilot_featured_match = False
            rounds = action.rounds if action.rounds and action.rounds > 0 else None
            locked_move = self._last_manual_move if action.stance == "lock_last_manual_move_for_n_rounds" else None
            self._featured_stance = FeaturedRoundStanceView(
                stance=action.stance,
                rounds_remaining=rounds,
                locked_move=locked_move,
            )
            self.snapshot.active_featured_stance = self._featured_stance
            self._sync_session_snapshot()
            return self.resolve_featured_round_automation(state)

        raise ValueError(f"Unsupported featured round action: {action}")

    def choose_floor_vote(self, state: FloorVoteDecisionState) -> int:
        self._begin_decision(state, (ChooseFloorVoteAction,))
        action = self.session.resolve_current_decision(self._resolve_floor_vote_decision)
        self._sync_session_snapshot()
        if action.mode == "autopilot_vote":
            return state.prompt.suggested_vote

        if action.vote not in (COOPERATE, DEFECT):
            raise ValueError("Manual floor vote must be cooperate or defect.")
        return action.vote

    def choose_powerup(self, floor_number: int, offers: list[Powerup]) -> Powerup:
        state = PowerupChoiceState(
            floor_number=floor_number,
            offers=[PowerupOfferView(name=offer.name, description=offer.description, tags=None) for offer in offers],
        )
        self._begin_decision(state, (ChoosePowerupAction,))
        action = self.session.resolve_current_decision(lambda decision: self._resolve_powerup_choice(decision, offers))
        self._sync_session_snapshot()
        if action.offer_index < 0 or action.offer_index >= len(offers):
            raise ValueError("Powerup choice index out of range.")
        return offers[action.offer_index]

    def choose_genome_edit(self, floor_number: int, current_summary: str, offers: list[GenomeEdit]) -> GenomeEdit:
        state = GenomeEditChoiceState(
            floor_number=floor_number,
            current_summary=current_summary,
            offers=[
                GenomeEditOfferView(
                    name=offer.name,
                    description=offer.description,
                    current_summary=current_summary,
                    projected_summary=None,
                )
                for offer in offers
            ],
        )
        self._begin_decision(state, (ChooseGenomeEditAction,))
        action = self.session.resolve_current_decision(lambda decision: self._resolve_genome_edit_choice(decision, offers))
        self._sync_session_snapshot()
        if action.offer_index < 0 or action.offer_index >= len(offers):
            raise ValueError("Genome edit choice index out of range.")
        return offers[action.offer_index]

    def choose_successor(self, floor_number: int, candidates: list[Agent]) -> Agent:
        successor_views: list[SuccessorCandidateView] = []
        for candidate in candidates:
            identity = analyze_agent_identity(candidate)
            successor_views.append(
                SuccessorCandidateView(
                    name=candidate.name,
                    lineage_depth=candidate.lineage_depth,
                    score=candidate.score,
                    wins=candidate.wins,
                    tags=identity.tags,
                    descriptor=identity.descriptor,
                    genome_summary=candidate.genome.summary(),
                    powerups=[powerup.name for powerup in candidate.powerups],
                )
            )

        state = SuccessorChoiceState(floor_number=floor_number, candidates=successor_views)
        self.snapshot.successor_options = state
        self._begin_decision(state, (ChooseSuccessorAction,))
        action = self.session.resolve_current_decision(lambda decision: self._resolve_successor_choice(decision, candidates))
        self._sync_session_snapshot()
        if action.candidate_index < 0 or action.candidate_index >= len(candidates):
            raise ValueError("Successor choice index out of range.")
        return candidates[action.candidate_index]

    def set_latest_round_result(self, result) -> None:
        self.snapshot.latest_featured_round = result
        self._sync_session_snapshot()

    def reset_featured_match_autopilot(self) -> None:
        self._autopilot_featured_match = False
        self._featured_stance = None
        self.snapshot.active_featured_stance = None
        self._sync_session_snapshot()

    @property
    def should_autopilot_featured_match(self) -> bool:
        return self._autopilot_featured_match

    def _decrement_stance_rounds(self) -> None:
        if self._featured_stance is None or self._featured_stance.rounds_remaining is None:
            return
        self._featured_stance.rounds_remaining -= 1
        if self._featured_stance.rounds_remaining <= 0:
            self._featured_stance = None
        self.snapshot.active_featured_stance = self._featured_stance

    def _begin_decision(self, state: DecisionState, expected_types: tuple[type, ...]) -> None:
        self.snapshot.session_status = "awaiting_decision"
        self.session.begin_decision(state, expected_types, self.snapshot)

    def _sync_session_snapshot(self) -> None:
        self.snapshot.session_status = self.session.status
        self.session.update_snapshot(self.snapshot)

    def _resolve_featured_round_decision(self, state: DecisionState) -> PlayerAction:
        assert isinstance(state, FeaturedRoundDecisionState)
        if hasattr(self.renderer, "resolve_featured_round_decision"):
            return self.renderer.resolve_featured_round_decision(state)
        legacy_move = self.renderer.choose_round_action(state.prompt)
        return ChooseRoundMoveAction(mode="manual_move", move=legacy_move)

    def _resolve_floor_vote_decision(self, state: DecisionState) -> PlayerAction:
        assert isinstance(state, FloorVoteDecisionState)
        if hasattr(self.renderer, "resolve_floor_vote_decision"):
            return self.renderer.resolve_floor_vote_decision(state)
        legacy_vote = self.renderer.choose_floor_vote(state.prompt)
        return ChooseFloorVoteAction(mode="manual_vote", vote=legacy_vote)

    def _resolve_powerup_choice(self, state: DecisionState, offers: list[Powerup]) -> PlayerAction:
        assert isinstance(state, PowerupChoiceState)
        if hasattr(self.renderer, "resolve_powerup_choice"):
            return self.renderer.resolve_powerup_choice(state)
        chosen = self.renderer.choose_powerup(offers)
        return ChoosePowerupAction(offer_index=offers.index(chosen))

    def _resolve_genome_edit_choice(self, state: DecisionState, offers: list[GenomeEdit]) -> PlayerAction:
        assert isinstance(state, GenomeEditChoiceState)
        if hasattr(self.renderer, "resolve_genome_edit_choice"):
            return self.renderer.resolve_genome_edit_choice(state)
        chosen = self.renderer.choose_genome_edit(offers, current_summary=state.current_summary)
        return ChooseGenomeEditAction(offer_index=offers.index(chosen))

    def _resolve_successor_choice(self, state: DecisionState, candidates: list[Agent]) -> PlayerAction:
        assert isinstance(state, SuccessorChoiceState)
        if hasattr(self.renderer, "resolve_successor_choice"):
            return self.renderer.resolve_successor_choice(state)
        chosen = self.renderer.choose_successor(candidates)
        return ChooseSuccessorAction(candidate_index=candidates.index(chosen))
