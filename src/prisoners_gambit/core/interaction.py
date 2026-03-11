from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prisoners_gambit.core.powerups import MoveDirective


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
    breakdown: RoundResolutionBreakdown


@dataclass(slots=True)
class RoundDirectiveResolution:
    base_move: int
    final_move: int
    reason: str
    directives: list[MoveDirective]


@dataclass(slots=True)
class ScoreAdjustment:
    source: str
    player_delta: int
    opponent_delta: int


@dataclass(slots=True)
class RoundResolutionBreakdown:
    player_plan: int
    opponent_plan: int
    player_directives: RoundDirectiveResolution
    opponent_directives: RoundDirectiveResolution
    base_player_points: int
    base_opponent_points: int
    score_adjustments: list[ScoreAdjustment]
    final_player_points: int
    final_opponent_points: int


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


@dataclass(slots=True)
class RunHeaderState:
    seed: int | None


@dataclass(slots=True)
class FloorRosterState:
    floor_number: int
    roster_entries: list[FloorRosterEntryView]


@dataclass(slots=True)
class FloorSummaryState:
    floor_number: int
    entries: list[FloorSummaryEntryView]


@dataclass(slots=True)
class FloorRosterEntryView:
    name: str
    public_profile: str
    known_powerups: list[str]
    tags: list[str]
    descriptor: str


@dataclass(slots=True)
class FloorSummaryEntryView:
    agent_id: int
    name: str
    is_player: bool
    score: int
    wins: int
    tags: list[str]
    descriptor: str
    genome_summary: str
    powerups: list[str]


@dataclass(slots=True)
class PowerupOfferView:
    name: str
    description: str
    tags: list[str] | None = None


@dataclass(slots=True)
class GenomeEditOfferView:
    name: str
    description: str
    current_summary: str | None = None
    projected_summary: str | None = None


@dataclass(slots=True)
class SuccessorCandidateView:
    name: str
    lineage_depth: int
    score: int
    wins: int
    tags: list[str]
    descriptor: str
    genome_summary: str
    powerups: list[str]


@dataclass(slots=True)
class FeaturedRoundDecisionState:
    prompt: FeaturedMatchPrompt
    valid_actions: tuple[
        Literal[
            "manual_move",
            "autopilot_round",
            "autopilot_match",
            "set_round_stance",
        ],
        ...,
    ] = (
        "manual_move",
        "autopilot_round",
        "autopilot_match",
        "set_round_stance",
    )
    stance_options: tuple[
        Literal[
            "cooperate_until_betrayed",
            "defect_until_punished",
            "follow_autopilot_for_n_rounds",
            "lock_last_manual_move_for_n_rounds",
        ],
        ...,
    ] = (
        "cooperate_until_betrayed",
        "defect_until_punished",
        "follow_autopilot_for_n_rounds",
        "lock_last_manual_move_for_n_rounds",
    )


ROUND_STANCES_REQUIRING_ROUNDS: frozenset[str] = frozenset({
    "follow_autopilot_for_n_rounds",
    "lock_last_manual_move_for_n_rounds",
})


@dataclass(slots=True)
class FloorVoteDecisionState:
    prompt: FloorVotePrompt
    valid_actions: tuple[Literal["manual_vote", "autopilot_vote"], ...] = ("manual_vote", "autopilot_vote")


@dataclass(slots=True)
class PowerupChoiceState:
    floor_number: int
    offers: list[PowerupOfferView]
    valid_actions: tuple[Literal["choose_powerup"], ...] = ("choose_powerup",)


@dataclass(slots=True)
class GenomeEditChoiceState:
    floor_number: int
    current_summary: str
    offers: list[GenomeEditOfferView]
    valid_actions: tuple[Literal["choose_genome_edit"], ...] = ("choose_genome_edit",)


@dataclass(slots=True)
class SuccessorChoiceState:
    floor_number: int
    candidates: list[SuccessorCandidateView]
    valid_actions: tuple[Literal["choose_successor"], ...] = ("choose_successor",)


DecisionState = (
    FeaturedRoundDecisionState
    | FloorVoteDecisionState
    | PowerupChoiceState
    | GenomeEditChoiceState
    | SuccessorChoiceState
)


@dataclass(slots=True)
class ChooseRoundMoveAction:
    mode: Literal["manual_move"]
    move: int


@dataclass(slots=True)
class ChooseRoundAutopilotAction:
    mode: Literal["autopilot_round", "autopilot_match"]


@dataclass(slots=True)
class FeaturedRoundStanceView:
    stance: Literal[
        "cooperate_until_betrayed",
        "defect_until_punished",
        "follow_autopilot_for_n_rounds",
        "lock_last_manual_move_for_n_rounds",
    ]
    rounds_remaining: int | None = None
    locked_move: int | None = None


@dataclass(slots=True)
class ChooseRoundStanceAction:
    mode: Literal["set_round_stance"]
    stance: Literal[
        "cooperate_until_betrayed",
        "defect_until_punished",
        "follow_autopilot_for_n_rounds",
        "lock_last_manual_move_for_n_rounds",
    ]
    rounds: int | None = None


@dataclass(slots=True)
class ChooseFloorVoteAction:
    mode: Literal["manual_vote", "autopilot_vote"]
    vote: int | None = None


@dataclass(slots=True)
class ChoosePowerupAction:
    offer_index: int


@dataclass(slots=True)
class ChooseGenomeEditAction:
    offer_index: int


@dataclass(slots=True)
class ChooseSuccessorAction:
    candidate_index: int


PlayerAction = (
    ChooseRoundMoveAction
    | ChooseRoundAutopilotAction
    | ChooseRoundStanceAction
    | ChooseFloorVoteAction
    | ChoosePowerupAction
    | ChooseGenomeEditAction
    | ChooseSuccessorAction
)

SessionStatus = Literal["running", "awaiting_decision", "completed"]


@dataclass(slots=True)
class RunCompletion:
    outcome: Literal["victory", "eliminated"]
    floor_number: int
    player_name: str
    seed: int | None


@dataclass(slots=True)
class RunSnapshot:
    header: RunHeaderState | None = None
    current_floor: int | None = None
    current_phase: Literal["ecosystem", "civil_war"] | None = None
    floor_roster: FloorRosterState | None = None
    latest_featured_round: FeaturedRoundResult | None = None
    floor_summary: FloorSummaryState | None = None
    floor_vote_result: FloorVoteResult | None = None
    successor_options: SuccessorChoiceState | None = None
    active_featured_stance: FeaturedRoundStanceView | None = None
    session_status: SessionStatus = "running"
    completion: RunCompletion | None = None
