from __future__ import annotations

from dataclasses import dataclass, field
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
    clue_channels: list[str] = field(default_factory=list)
    floor_clue_log: list[str] = field(default_factory=list)
    inference_focus: str | None = None


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
    inference_update: list[str] = field(default_factory=list)


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
class FloorSummaryPressureEntryView:
    name: str
    branch_role: str
    shaping_causes: list[str]
    score: int
    wins: int
    tags: list[str]
    descriptor: str
    rationale: str


@dataclass(slots=True)
class FloorSummaryHeirPressureView:
    branch_doctrine: str
    successor_candidates: list[FloorSummaryPressureEntryView]
    future_threats: list[FloorSummaryPressureEntryView]


@dataclass(slots=True)
class FloorSummaryState:
    floor_number: int
    entries: list[FloorSummaryEntryView]
    heir_pressure: FloorSummaryHeirPressureView | None = None
    featured_inference_summary: list[str] = field(default_factory=list)


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
    lineage_depth: int
    tags: list[str]
    descriptor: str
    genome_summary: str
    powerups: list[str]


@dataclass(slots=True)
class PowerupOfferView:
    name: str
    description: str
    lineage_commitment: str | None = None
    doctrine_vector: str | None = None
    branch_identity: str | None = None
    tradeoff: str | None = None
    phase_support: str | None = None
    successor_pressure: str | None = None
    tags: list[str] | None = None


@dataclass(slots=True)
class GenomeEditOfferView:
    name: str
    description: str
    lineage_commitment: str | None = None
    doctrine_vector: str | None = None
    branch_identity: str | None = None
    tradeoff: str | None = None
    phase_support: str | None = None
    successor_pressure: str | None = None
    current_summary: str | None = None
    projected_summary: str | None = None
    doctrine_drift: str | None = None


@dataclass(slots=True)
class SuccessorCandidateView:
    name: str
    lineage_depth: int
    score: int
    wins: int
    branch_role: str
    branch_doctrine: str
    shaping_causes: list[str]
    tags: list[str]
    descriptor: str
    tradeoffs: list[str]
    strengths: list[str]
    liabilities: list[str]
    attractive_now: str
    danger_later: str
    lineage_future: str
    succession_pitch: str
    succession_risk: str
    anti_score_note: str
    genome_summary: str
    powerups: list[str]
    featured_inference_context: str | None = None


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


def validated_stance_rounds(stance: str, rounds: int | None) -> int | None:
    """Normalize optional stance rounds and enforce them for duration-bound stances.

    Returns a positive round count for stances that use an explicit duration, or None
    for stances that are intended to run until another decision clears them. Raises
    ValueError when a duration-bound stance is selected without rounds > 0.
    """
    if stance not in ROUND_STANCES_REQUIRING_ROUNDS:
        # Non-duration stances always run until cleared; ignore any provided rounds.
        return None
    if rounds is None or rounds <= 0:
        raise ValueError(f"Stance '{stance}' requires rounds > 0.")
    return rounds


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
    current_phase: str | None = None
    lineage_doctrine: str | None = None
    threat_profile: list[str] | None = None
    civil_war_pressure: str | None = None
    featured_inference_summary: list[str] = field(default_factory=list)
    valid_actions: tuple[Literal["choose_successor"], ...] = ("choose_successor",)


@dataclass(slots=True)
class CivilWarContext:
    thesis: str
    scoring_rules: list[str]
    dangerous_branches: list[str]
    doctrine_pressure: list[str]


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
class DynastyBoardEntryView:
    name: str
    role: str
    doctrine_signal: str
    score: int
    wins: int
    lineage_depth: int
    is_current_host: bool
    has_successor_pressure: bool
    has_civil_war_danger: bool


@dataclass(slots=True)
class DynastyBoardState:
    phase: Literal["ecosystem", "civil_war"] | None
    entries: list[DynastyBoardEntryView]


@dataclass(slots=True)
class LineageChronicleEntry:
    event_id: str
    event_type: str
    floor_number: int | None
    phase: Literal["ecosystem", "civil_war"] | None
    summary: str


@dataclass(slots=True)
class RunSnapshot:
    header: RunHeaderState | None = None
    current_floor: int | None = None
    current_phase: Literal["ecosystem", "civil_war"] | None = None
    floor_roster: FloorRosterState | None = None
    latest_featured_round: FeaturedRoundResult | None = None
    floor_summary: FloorSummaryState | None = None
    floor_vote_result: FloorVoteResult | None = None
    dynasty_board: DynastyBoardState | None = None
    successor_options: SuccessorChoiceState | None = None
    civil_war_context: CivilWarContext | None = None
    active_featured_stance: FeaturedRoundStanceView | None = None
    lineage_chronicle: list[LineageChronicleEntry] = field(default_factory=list)
    session_status: SessionStatus = "running"
    completion: RunCompletion | None = None
