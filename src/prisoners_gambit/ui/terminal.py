from __future__ import annotations

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import (
    FeaturedMatchPrompt,
    FeaturedRoundResult,
    FloorVotePrompt,
    FloorVoteResult,
    RosterEntry,
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
        print(format_featured_prompt(prompt))

        if self.auto_choose_round_actions:
            print("Auto-following autopilot suggestion.")
            return prompt.suggested_move

        while True:
            raw = input("Choose [C]ooperate, [D]efect, or [Enter] for autopilot: ").strip().lower()
            if raw == "":
                return prompt.suggested_move
            if raw == "c":
                return COOPERATE
            if raw == "d":
                return DEFECT
            print("Invalid choice.")

    def show_round_result(self, result: FeaturedRoundResult) -> None:
        print(format_round_result(result))

    def choose_floor_vote(self, prompt: FloorVotePrompt) -> int:
        print(format_floor_vote_prompt(prompt))

        if self.auto_choose_floor_vote:
            print("Auto-following autopilot suggestion for floor referendum.")
            return prompt.suggested_vote

        while True:
            raw = input("Choose floor vote [C]ooperate, [D]efect, or [Enter] for autopilot: ").strip().lower()
            if raw == "":
                return prompt.suggested_vote
            if raw == "c":
                return COOPERATE
            if raw == "d":
                return DEFECT
            print("Invalid choice.")

    def show_referendum_result(self, result: FloorVoteResult) -> None:
        print(format_floor_vote_result(result))

    def choose_powerup(self, offers: list[Powerup]) -> Powerup:
        print("\nChoose a powerup:")
        for index, powerup in enumerate(offers, start=1):
            print(format_powerup_line(index=index, powerup=powerup))

        if self.auto_choose_powerups:
            print("Auto-selecting option 1.")
            return offers[0]

        while True:
            raw = input(f"Select 1-{len(offers)}: ").strip()
            if raw.isdigit():
                choice = int(raw)
                if 1 <= choice <= len(offers):
                    return offers[choice - 1]
            print("Invalid selection.")

    def choose_genome_edit(self, offers: list[GenomeEdit], current_summary: str) -> GenomeEdit:
        print("\nChoose an autopilot edit:")
        print(f"Current autopilot: {current_summary}")
        for index, edit in enumerate(offers, start=1):
            print(format_genome_edit_line(index=index, edit=edit))

        if self.auto_choose_genome_edits:
            print("Auto-selecting option 1.")
            return offers[0]

        while True:
            raw = input(f"Select 1-{len(offers)}: ").strip()
            if raw.isdigit():
                choice = int(raw)
                if 1 <= choice <= len(offers):
                    return offers[choice - 1]
            print("Invalid selection.")

    def show_genome_edit_applied(self, edit: GenomeEdit, new_summary: str) -> None:
        print(f"Applied autopilot edit: {edit.name}")
        print(f"New autopilot: {new_summary}")

    def choose_successor(self, successors: list[Agent]) -> Agent:
        print("\nYour current host was eliminated, but your lineage survives.")
        print("Choose a surviving descendant to continue as:")
        for index, agent in enumerate(successors, start=1):
            print(format_successor_line(index=index, agent=agent))

        while True:
            raw = input(f"Select 1-{len(successors)}: ").strip()
            if raw.isdigit():
                choice = int(raw)
                if 1 <= choice <= len(successors):
                    return successors[choice - 1]
            print("Invalid selection.")

    def show_successor_selected(self, successor: Agent) -> None:
        print(f"\nYou now continue as {successor.name}.")

    def show_elimination(self, floor_number: int, seed: int) -> None:
        print(f"\nYour lineage was eliminated on floor {floor_number}.")
        print(f"Run seed: {seed}")

    def show_victory(self, floor_number: int, player: Agent, seed: int) -> None:
        print(f"\nFinal survivor after floor {floor_number}: {player.name}")
        print(f"Run seed: {seed}")