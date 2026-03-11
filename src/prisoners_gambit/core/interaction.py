from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RosterEntry:
    name: str
    public_profile: str
    known_powerups: list[str]
    tags: list[str]
    descriptor: str


@dataclass(slots=True)
class FeaturedMatchPrompt:
    floor_number: int
    masked_opponent_label: str
    round_index: int
    total_rounds: int
    my_history: list[int]
    opp_history: list[int]
    my_match_score: int
    opp_match_score: int
    suggested_move: int
    roster_entries: list[RosterEntry]


@dataclass(slots=True)
class FeaturedRoundResult:
    masked_opponent_label: str
    round_index: int
    total_rounds: int
    player_move: int
    opponent_move: int
    player_delta: int
    opponent_delta: int
    player_total: int
    opponent_total: int
    player_reason: str
    opponent_reason: str


@dataclass(slots=True)
class FloorVotePrompt:
    floor_number: int
    floor_label: str
    suggested_vote: int
    current_floor_score: int
    powerups: list[str]


@dataclass(slots=True)
class FloorVoteResult:
    floor_number: int
    cooperation_prevailed: bool
    cooperators: int
    defectors: int
    player_vote: int
    player_reward: int