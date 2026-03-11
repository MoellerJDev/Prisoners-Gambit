from __future__ import annotations

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
from prisoners_gambit.ui.renderers import Renderer
from prisoners_gambit.ui.view_models import (
    format_agent_line,
    format_featured_prompt,
    format_floor_vote_prompt,
    format_floor_vote_result,
    format_genome_edit_line,
    format_powerup_line,
    format_roster_line,
    format_round_result,
    format_successor_line,
)


class TerminalRenderer(Renderer):
    def __init__(
        self,
        auto_choose_powerups: bool = False,
        auto_choose_round_actions: bool = False,
        auto_choose_genome_edits: bool = False,
        auto_choose_floor_vote: bool = False,
    ) -> None:
        self.auto_choose_powerups = auto_choose_powerups
        self.auto_choose_round_actions = auto_choose_round_actions
        self.auto_choose_genome_edits = auto_choose_genome_edits
        self.auto_choose_floor_vote = auto_choose_floor_vote

    def show_run_header(self, seed: int | None) -> None:
        print("=== Prisoner's Gambit ===")
        print(f"Seed: {seed}")

    def show_phase_transition(self, title: str, message: str) -> None:
        print(f"\n== {title} ==")
        print(message)

    def show_floor_roster(self, floor_number: int, roster_entries: list[RosterEntry]) -> None:
        print(f"\n== Floor {floor_number} roster ==")
        print("These are the possible opponents in your masked featured matches.")
        for index, entry in enumerate(roster_entries, start=1):
            print(format_roster_line(index=index, entry=entry))

    def show_floor_summary(self, floor_number: int, ranked: list[Agent]) -> None:
        print(f"\n-- Floor {floor_number} results --")
        for index, agent in enumerate(ranked[:5], start=1):
            print(format_agent_line(index=index, agent=agent))

        player_rank = next((index for index, agent in enumerate(ranked, start=1) if agent.is_player), None)
        if player_rank is not None:
            player = ranked[player_rank - 1]
            print(f"You placed {player_rank}/{len(ranked)} with score={player.score} and wins={player.wins}")

        if ranked:
            print(f"Leader build: {ranked[0].build_summary()}")

    def choose_round_action(self, prompt: FeaturedMatchPrompt) -> int:
        action = self.resolve_featured_round_decision(FeaturedRoundDecisionState(prompt=prompt))
        if isinstance(action, ChooseRoundMoveAction):
            return action.move
        return prompt.suggested_move

    def resolve_featured_round_decision(
        self,
        state: FeaturedRoundDecisionState,
    ) -> ChooseRoundMoveAction | ChooseRoundAutopilotAction:
        prompt = state.prompt
        print(format_featured_prompt(prompt))

        if self.auto_choose_round_actions:
            print("Auto-following autopilot suggestion.")
            return ChooseRoundAutopilotAction(mode="autopilot_round")

        while True:
            raw = input(
                "Choose [C]ooperate, [D]efect, [A]utopilot match, or [Enter] for autopilot round: "
            ).strip().lower()
            if raw == "":
                return ChooseRoundAutopilotAction(mode="autopilot_round")
            if raw == "c":
                return ChooseRoundMoveAction(mode="manual_move", move=COOPERATE)
            if raw == "d":
                return ChooseRoundMoveAction(mode="manual_move", move=DEFECT)
            if raw == "a":
                return ChooseRoundAutopilotAction(mode="autopilot_match")
            print("Invalid choice.")

    def show_round_result(self, result: FeaturedRoundResult) -> None:
        print(format_round_result(result))

    def choose_floor_vote(self, prompt: FloorVotePrompt) -> int:
        action = self.resolve_floor_vote_decision(FloorVoteDecisionState(prompt=prompt))
        if action.mode == "autopilot_vote":
            return prompt.suggested_vote
        return action.vote if action.vote is not None else prompt.suggested_vote

    def resolve_floor_vote_decision(self, state: FloorVoteDecisionState) -> ChooseFloorVoteAction:
        prompt = state.prompt
        print(format_floor_vote_prompt(prompt))

        if self.auto_choose_floor_vote:
            print("Auto-following autopilot suggestion for floor referendum.")
            return ChooseFloorVoteAction(mode="autopilot_vote")

        while True:
            raw = input("Choose floor vote [C]ooperate, [D]efect, or [Enter] for autopilot: ").strip().lower()
            if raw == "":
                return ChooseFloorVoteAction(mode="autopilot_vote")
            if raw == "c":
                return ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE)
            if raw == "d":
                return ChooseFloorVoteAction(mode="manual_vote", vote=DEFECT)
            print("Invalid choice.")

    def show_referendum_result(self, result: FloorVoteResult) -> None:
        print(format_floor_vote_result(result))

    def choose_powerup(self, offers: list[Powerup]) -> Powerup:
        state = PowerupChoiceState(floor_number=0, offers=[offer.name for offer in offers])
        action = self.resolve_powerup_choice(state)
        return offers[action.offer_index]

    def resolve_powerup_choice(self, state: PowerupChoiceState) -> ChoosePowerupAction:
        offers = state.offers
        print("\nChoose a powerup:")
        for index, powerup_name in enumerate(offers, start=1):
            print(f"{index}. {powerup_name}")

        if self.auto_choose_powerups:
            print("Auto-selecting option 1.")
            return ChoosePowerupAction(offer_index=0)

        while True:
            raw = input(f"Select 1-{len(offers)}: ").strip()
            if raw.isdigit():
                choice = int(raw)
                if 1 <= choice <= len(offers):
                    return ChoosePowerupAction(offer_index=choice - 1)
            print("Invalid selection.")

    def choose_genome_edit(self, offers: list[GenomeEdit], current_summary: str) -> GenomeEdit:
        state = GenomeEditChoiceState(
            floor_number=0,
            current_summary=current_summary,
            offers=[offer.name for offer in offers],
        )
        action = self.resolve_genome_edit_choice(state)
        return offers[action.offer_index]

    def resolve_genome_edit_choice(self, state: GenomeEditChoiceState) -> ChooseGenomeEditAction:
        offers = state.offers
        print("\nChoose an autopilot edit:")
        print(f"Current autopilot: {state.current_summary}")
        for index, edit_name in enumerate(offers, start=1):
            print(f"{index}. {edit_name}")

        if self.auto_choose_genome_edits:
            print("Auto-selecting option 1.")
            return ChooseGenomeEditAction(offer_index=0)

        while True:
            raw = input(f"Select 1-{len(offers)}: ").strip()
            if raw.isdigit():
                choice = int(raw)
                if 1 <= choice <= len(offers):
                    return ChooseGenomeEditAction(offer_index=choice - 1)
            print("Invalid selection.")

    def show_genome_edit_applied(self, edit: GenomeEdit, new_summary: str) -> None:
        print(f"Applied autopilot edit: {edit.name}")
        print(f"New autopilot: {new_summary}")

    def choose_successor(self, successors: list[Agent]) -> Agent:
        state = SuccessorChoiceState(floor_number=0, candidates=[agent.name for agent in successors])
        action = self.resolve_successor_choice(state)
        return successors[action.candidate_index]

    def resolve_successor_choice(self, state: SuccessorChoiceState) -> ChooseSuccessorAction:
        print("\nYour current host was eliminated, but your lineage survives.")
        print("Choose a surviving descendant to continue as:")
        for index, candidate_name in enumerate(state.candidates, start=1):
            print(f"{index}. {candidate_name}")

        while True:
            raw = input(f"Select 1-{len(state.candidates)}: ").strip()
            if raw.isdigit():
                choice = int(raw)
                if 1 <= choice <= len(state.candidates):
                    return ChooseSuccessorAction(candidate_index=choice - 1)
            print("Invalid selection.")

    def show_successor_selected(self, successor: Agent) -> None:
        print(f"\nYou now continue as {successor.name}.")

    def show_elimination(self, floor_number: int, seed: int) -> None:
        print(f"\nYour lineage was eliminated on floor {floor_number}.")
        print(f"Run seed: {seed}")

    def show_victory(self, floor_number: int, player: Agent, seed: int) -> None:
        print(f"\nFinal survivor after floor {floor_number}: {player.name}")
        print(f"Run seed: {seed}")
