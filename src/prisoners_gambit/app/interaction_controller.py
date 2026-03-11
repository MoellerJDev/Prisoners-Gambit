from __future__ import annotations

from dataclasses import dataclass, field

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseSuccessorAction,
    FeaturedRoundDecisionState,
    FloorVoteDecisionState,
    GenomeEditChoiceState,
    PlayerAction,
    PowerupChoiceState,
    RunHeaderState,
    RunSnapshot,
    SuccessorChoiceState,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.ui.renderers import Renderer


@dataclass(slots=True)
class InteractionController:
    renderer: Renderer
    snapshot: RunSnapshot = field(default_factory=RunSnapshot)
    _autopilot_featured_match: bool = False

    def show_run_header(self, seed: int | None) -> None:
        self.snapshot.header = RunHeaderState(seed=seed)
        self.renderer.show_run_header(seed)

    def choose_round_move(self, state: FeaturedRoundDecisionState) -> int:
        if hasattr(self.renderer, "resolve_featured_round_decision"):
            action = self.renderer.resolve_featured_round_decision(state)
        else:
            legacy_move = self.renderer.choose_round_action(state.prompt)
            action = ChooseRoundMoveAction(mode="manual_move", move=legacy_move)
        if isinstance(action, ChooseRoundMoveAction):
            self._autopilot_featured_match = False
            return action.move

        if isinstance(action, ChooseRoundAutopilotAction):
            if action.mode == "autopilot_match":
                self._autopilot_featured_match = True
            return state.prompt.suggested_move

        raise ValueError(f"Unsupported featured round action: {action}")

    def choose_floor_vote(self, state: FloorVoteDecisionState) -> int:
        if hasattr(self.renderer, "resolve_floor_vote_decision"):
            action = self.renderer.resolve_floor_vote_decision(state)
        else:
            legacy_vote = self.renderer.choose_floor_vote(state.prompt)
            action = ChooseFloorVoteAction(mode="manual_vote", vote=legacy_vote)
        if not isinstance(action, ChooseFloorVoteAction):
            raise ValueError(f"Unsupported floor vote action: {action}")

        if action.mode == "autopilot_vote":
            return state.prompt.suggested_vote

        if action.vote not in (COOPERATE, DEFECT):
            raise ValueError("Manual floor vote must be cooperate or defect.")
        return action.vote

    def choose_powerup(self, floor_number: int, offers: list[Powerup]) -> Powerup:
        state = PowerupChoiceState(
            floor_number=floor_number,
            offers=[f"{offer.name} - {offer.description}" for offer in offers],
        )
        if hasattr(self.renderer, "resolve_powerup_choice"):
            action = self.renderer.resolve_powerup_choice(state)
        else:
            chosen = self.renderer.choose_powerup(offers)
            action = ChoosePowerupAction(offer_index=offers.index(chosen))
        if not isinstance(action, ChoosePowerupAction):
            raise ValueError(f"Unsupported powerup action: {action}")
        if action.offer_index < 0 or action.offer_index >= len(offers):
            raise ValueError("Powerup choice index out of range.")
        return offers[action.offer_index]

    def choose_genome_edit(self, floor_number: int, current_summary: str, offers: list[GenomeEdit]) -> GenomeEdit:
        state = GenomeEditChoiceState(
            floor_number=floor_number,
            current_summary=current_summary,
            offers=[f"{offer.name} - {offer.description}" for offer in offers],
        )
        if hasattr(self.renderer, "resolve_genome_edit_choice"):
            action = self.renderer.resolve_genome_edit_choice(state)
        else:
            chosen = self.renderer.choose_genome_edit(offers, current_summary=current_summary)
            action = ChooseGenomeEditAction(offer_index=offers.index(chosen))
        if not isinstance(action, ChooseGenomeEditAction):
            raise ValueError(f"Unsupported genome edit action: {action}")
        if action.offer_index < 0 or action.offer_index >= len(offers):
            raise ValueError("Genome edit choice index out of range.")
        return offers[action.offer_index]

    def choose_successor(self, floor_number: int, candidates: list[Agent]) -> Agent:
        state = SuccessorChoiceState(
            floor_number=floor_number,
            candidates=[candidate.name for candidate in candidates],
        )
        self.snapshot.successor_options = state
        if hasattr(self.renderer, "resolve_successor_choice"):
            action = self.renderer.resolve_successor_choice(state)
        else:
            chosen = self.renderer.choose_successor(candidates)
            action = ChooseSuccessorAction(candidate_index=candidates.index(chosen))
        if not isinstance(action, ChooseSuccessorAction):
            raise ValueError(f"Unsupported successor action: {action}")
        if action.candidate_index < 0 or action.candidate_index >= len(candidates):
            raise ValueError("Successor choice index out of range.")
        return candidates[action.candidate_index]

    def set_latest_round_result(self, result) -> None:
        self.snapshot.latest_featured_round = result

    def reset_featured_match_autopilot(self) -> None:
        self._autopilot_featured_match = False

    @property
    def should_autopilot_featured_match(self) -> bool:
        return self._autopilot_featured_match
