from __future__ import annotations

from prisoners_gambit.core.analysis import analyze_agent_identity
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
from prisoners_gambit.utils.formatting import move_symbol


def _history_text(history: list[int]) -> str:
    if not history:
        return "-"
    return " ".join(move_symbol(move) for move in history)


def _tag_text(tags: list[str]) -> str:
    if not tags:
        return "No tags"
    return ", ".join(tags)


def format_agent_line(index: int, agent: Agent) -> str:
    marker = "[YOU] " if agent.is_player else ""
    identity = analyze_agent_identity(agent)
    return (
        f"{index}. {marker}{agent.name} | score={agent.score} | wins={agent.wins} | "
        f"{_tag_text(identity.tags)}"
    )


def format_powerup_line(index: int, powerup: Powerup) -> str:
    return f"{index}. {powerup.name} - {powerup.description}"


def format_roster_line(index: int, entry: RosterEntry) -> str:
    powerups = ", ".join(entry.known_powerups) if entry.known_powerups else "No visible powerups"
    return (
        f"{index}. {entry.name} | {entry.public_profile}\n"
        f"   Tags: {_tag_text(entry.tags)}\n"
        f"   Read: {entry.descriptor}\n"
        f"   Visible powerups: {powerups}"
    )


def format_genome_edit_line(index: int, edit: GenomeEdit) -> str:
    return f"{index}. {edit.name} - {edit.description}"


def format_featured_prompt(prompt: FeaturedMatchPrompt) -> str:
    roster_hint = ""
    if prompt.roster_entries:
        roster_hint = "Use the floor roster and move patterns to infer who this may be.\n"

    return (
        f"\n[Featured Match] {prompt.masked_opponent_label}\n"
        f"Round {prompt.round_index + 1}/{prompt.total_rounds}\n"
        f"Match score: You {prompt.my_match_score} - {prompt.opp_match_score} Opponent\n"
        f"Your history: {_history_text(prompt.my_history)}\n"
        f"Their history: {_history_text(prompt.opp_history)}\n"
        f"{roster_hint}"
        f"Autopilot suggests: {move_symbol(prompt.suggested_move)}"
    )


def format_round_result(result: FeaturedRoundResult) -> str:
    score_adjustments = "none"
    if result.breakdown.score_adjustments:
        lines = [
            f"{adjustment.source}: {adjustment.player_delta:+}/{adjustment.opponent_delta:+}"
            for adjustment in result.breakdown.score_adjustments
        ]
        score_adjustments = ", ".join(lines)

    return (
        f"Round {result.round_index + 1}/{result.total_rounds}\n"
        f"- Autopilot planned: You={move_symbol(result.breakdown.player_plan)}, "
        f"Opp={move_symbol(result.breakdown.opponent_plan)}\n"
        f"- Directives: You={result.player_reason} | Opp={result.opponent_reason}\n"
        f"- Final moves: You={move_symbol(result.player_move)}, Opp={move_symbol(result.opponent_move)}\n"
        f"- Base payoff: {result.breakdown.base_player_points} / {result.breakdown.base_opponent_points}\n"
        f"- Score modifiers: {score_adjustments}\n"
        f"- Final payoff: {result.player_delta} / {result.opponent_delta}\n"
        f"- Match total: {result.player_total} / {result.opponent_total}"
    )


def format_floor_vote_prompt(prompt: FloorVotePrompt) -> str:
    powerups = ", ".join(prompt.powerups) if prompt.powerups else "No powerups"
    return (
        f"\n[Floor Referendum] Floor {prompt.floor_number} - {prompt.floor_label}\n"
        f"Current floor score: {prompt.current_floor_score}\n"
        f"Your visible powerups: {powerups}\n"
        f"Autopilot suggests: {move_symbol(prompt.suggested_vote)}\n"
        f"If cooperation reaches a majority or better, cooperators gain floor reward.\n"
        f"If defection is the majority, nobody gains anything."
    )


def format_floor_vote_result(result: FloorVoteResult) -> str:
    outcome = "Cooperation prevailed" if result.cooperation_prevailed else "Defection spoiled the vote"
    return (
        f"\n[Referendum Result] Floor {result.floor_number}\n"
        f"{outcome}\n"
        f"Cooperators: {result.cooperators} | Defectors: {result.defectors}\n"
        f"Your vote: {move_symbol(result.player_vote)} | Your reward: {result.player_reward}"
    )


def format_successor_line(index: int, agent: Agent) -> str:
    powerups = ", ".join(powerup.name for powerup in agent.powerups) if agent.powerups else "No powerups"
    identity = analyze_agent_identity(agent)
    return (
        f"{index}. {agent.name} | depth={agent.lineage_depth} | score={agent.score} | wins={agent.wins}\n"
        f"   Tags: {_tag_text(identity.tags)}\n"
        f"   Read: {identity.descriptor}\n"
        f"   Build: {agent.genome.summary()}\n"
        f"   Powerups: {powerups}"
    )
