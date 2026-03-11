from __future__ import annotations

from typing import Protocol

from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
    FeaturedRoundDecisionState,
    FeaturedMatchPrompt,
    FeaturedRoundResult,
    FloorVoteDecisionState,
    FloorVotePrompt,
    FloorVoteResult,
    GenomeEditChoiceState,
    PowerupChoiceState,
    RosterEntry,
    SuccessorChoiceState,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import Powerup


class Renderer(Protocol):
    def show_run_header(self, seed: int | None) -> None:
        ...

    def show_phase_transition(self, title: str, message: str) -> None:
        ...

    def show_floor_roster(self, floor_number: int, roster_entries: list[RosterEntry]) -> None:
        ...

    def show_floor_summary(self, floor_number: int, ranked: list[Agent]) -> None:
        ...

    def choose_round_action(self, prompt: FeaturedMatchPrompt) -> int:
        ...

    def resolve_featured_round_decision(
        self,
        state: FeaturedRoundDecisionState,
    ) -> ChooseRoundMoveAction | ChooseRoundAutopilotAction | ChooseRoundStanceAction:
        ...

    def show_round_result(self, result: FeaturedRoundResult) -> None:
        ...

    def choose_floor_vote(self, prompt: FloorVotePrompt) -> int:
        ...

    def resolve_floor_vote_decision(self, state: FloorVoteDecisionState) -> ChooseFloorVoteAction:
        ...

    def show_referendum_result(self, result: FloorVoteResult) -> None:
        ...

    def choose_powerup(self, offers: list[Powerup]) -> Powerup:
        ...

    def resolve_powerup_choice(self, state: PowerupChoiceState) -> ChoosePowerupAction:
        ...

    def choose_genome_edit(self, offers: list[GenomeEdit], current_summary: str) -> GenomeEdit:
        ...

    def resolve_genome_edit_choice(self, state: GenomeEditChoiceState) -> ChooseGenomeEditAction:
        ...

    def show_genome_edit_applied(self, edit: GenomeEdit, new_summary: str) -> None:
        ...

    def choose_successor(self, successors: list[Agent]) -> Agent:
        ...

    def resolve_successor_choice(self, state: SuccessorChoiceState) -> ChooseSuccessorAction:
        ...

    def show_successor_selected(self, successor: Agent) -> None:
        ...

    def show_elimination(self, floor_number: int, seed: int) -> None:
        ...

    def show_victory(self, floor_number: int, player: Agent, seed: int) -> None:
        ...
