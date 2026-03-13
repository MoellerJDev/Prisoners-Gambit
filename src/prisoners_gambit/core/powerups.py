from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import IntEnum
import logging
from typing import TYPE_CHECKING, ClassVar

from prisoners_gambit.core.constants import COOPERATE, DEFECT

if TYPE_CHECKING:
    from prisoners_gambit.core.models import Agent

logger = logging.getLogger(__name__)


class DirectivePriority(IntEnum):
    OVERRIDE = 100
    FORCE = 200
    LOCK = 300


ROUND_EVENT_FORCED_OPPONENT_COOP = "forced_opponent_cooperation"
ROUND_EVENT_LOCKED_MUTUAL_COOP = "locked_mutual_cooperation"
ROUND_EVENT_BETRAYAL_INTO_COOP = "betrayal_into_cooperation"
ROUND_EVENT_RETALIATION_TRIGGERED = "retaliation_triggered"
ROUND_EVENT_MUTUAL_DEFECTION_SPIRAL = "mutual_defection_spiral"
ROUND_EVENT_FINAL_ROUND_BETRAYAL = "final_round_betrayal"

REFERENDUM_EVENT_CONTROLLED_VOTE = "referendum_controlled_vote"
REFERENDUM_EVENT_COOP_BLOC_WIN = "cooperation_bloc_win"
REFERENDUM_EVENT_SABOTAGE_BLOC_WIN = "sabotage_bloc_win"


@dataclass(slots=True)
class MoveDirective:
    move: int
    priority: int
    source: str


@dataclass(slots=True)
class RoundContext:
    round_index: int
    total_rounds: int
    my_history: list[int]
    opp_history: list[int]
    planned_move: int
    opp_planned_move: int
    combo_events: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class ReferendumContext:
    floor_number: int
    total_agents: int
    current_floor_score: int
    combo_events: tuple[str, ...] = field(default_factory=tuple)


def resolve_move(base_move: int, directives: list[MoveDirective]) -> tuple[int, str]:
    if not directives:
        return base_move, "base"

    highest_priority = max(directive.priority for directive in directives)
    highest = [directive for directive in directives if directive.priority == highest_priority]
    distinct_moves = {directive.move for directive in highest}

    if len(distinct_moves) == 1:
        resolved = highest[0].move
        source = ", ".join(sorted({directive.source for directive in highest}))
        return resolved, f"{source}@{highest_priority}"

    return DEFECT, f"conflict@{highest_priority}->D"


def derive_round_combo_events(
    *,
    context: RoundContext,
    my_move: int,
    opp_move: int,
    my_directives: list[MoveDirective],
    opp_directives: list[MoveDirective],
) -> tuple[str, ...]:
    events: list[str] = []
    if opp_move == COOPERATE and context.opp_planned_move != COOPERATE:
        events.append(ROUND_EVENT_FORCED_OPPONENT_COOP)

    locked_coop = any(d.move == COOPERATE and d.priority == DirectivePriority.LOCK for d in my_directives + opp_directives)
    if my_move == COOPERATE and opp_move == COOPERATE and locked_coop:
        events.append(ROUND_EVENT_LOCKED_MUTUAL_COOP)

    if my_move == DEFECT and opp_move == COOPERATE:
        events.append(ROUND_EVENT_BETRAYAL_INTO_COOP)

    if context.opp_history and context.opp_history[-1] == DEFECT and my_move == DEFECT:
        events.append(ROUND_EVENT_RETALIATION_TRIGGERED)

    if context.my_history and context.opp_history and context.my_history[-1] == DEFECT and context.opp_history[-1] == DEFECT and my_move == DEFECT and opp_move == DEFECT:
        events.append(ROUND_EVENT_MUTUAL_DEFECTION_SPIRAL)

    if context.round_index == context.total_rounds - 1 and my_move == DEFECT and opp_move == COOPERATE:
        events.append(ROUND_EVENT_FINAL_ROUND_BETRAYAL)

    return tuple(events)


def derive_referendum_combo_events(
    *,
    base_vote: int,
    final_vote: int,
    directives: list[MoveDirective],
    cooperation_prevailed: bool,
) -> tuple[str, ...]:
    events: list[str] = []
    if final_vote != base_vote and any(d.priority in (DirectivePriority.FORCE, DirectivePriority.LOCK) for d in directives):
        events.append(REFERENDUM_EVENT_CONTROLLED_VOTE)
    if cooperation_prevailed and final_vote == COOPERATE:
        events.append(REFERENDUM_EVENT_COOP_BLOC_WIN)
    if (not cooperation_prevailed) and final_vote == DEFECT:
        events.append(REFERENDUM_EVENT_SABOTAGE_BLOC_WIN)
    return tuple(events)


class Powerup:
    name: str = "Unnamed Powerup"
    description: str = "No description available."
    synergy_tags: ClassVar[tuple[str, ...]] = ()

    @property
    def keywords(self) -> tuple[str, ...]:
        return self.synergy_tags

    def self_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        return []

    def opponent_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        return my_points, opp_points

    def self_referendum_directives(self, *, owner: "Agent", context: ReferendumContext) -> list[MoveDirective]:
        return []

    def on_referendum_reward(self, *, owner: "Agent", my_vote: int, cooperation_prevailed: bool, current_reward: int, context: ReferendumContext) -> int:
        return current_reward

    def clone(self) -> "Powerup":
        return replace(self)


@dataclass(slots=True)
class OpeningGambit(Powerup):
    bonus: int = 1
    name: str = "Opening Gambit"
    description: str = "If you defect on round 1, gain bonus points."
    synergy_tags: ClassVar[tuple[str, ...]] = ("opportunist", "rewards_betrayal", "enabler")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if context.round_index == 0 and my_move == DEFECT:
            my_points += self.bonus
        return my_points, opp_points


@dataclass(slots=True)
class TrustDividend(Powerup):
    bonus: int = 1
    name: str = "Trust Dividend"
    description: str = "Mutual cooperation gives bonus points. Locked peace gives +1 more."
    synergy_tags: ClassVar[tuple[str, ...]] = ("rewards_mutual_coop", "coalition", "payoff")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if my_move == COOPERATE and opp_move == COOPERATE:
            my_points += self.bonus
            if ROUND_EVENT_LOCKED_MUTUAL_COOP in context.combo_events:
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class LastLaugh(Powerup):
    bonus: int = 1
    name: str = "Last Laugh"
    description: str = "Force defect on the final round. Final-round betrayal gains bonus points (+1 more if round 1 was betrayal)."
    synergy_tags: ClassVar[tuple[str, ...]] = ("opportunist", "final_round_payoff", "rewards_betrayal", "payoff")

    def self_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.round_index == context.total_rounds - 1:
            return [MoveDirective(move=DEFECT, priority=DirectivePriority.OVERRIDE, source=self.name)]
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if ROUND_EVENT_FINAL_ROUND_BETRAYAL in context.combo_events:
            my_points += self.bonus
            if context.my_history and context.my_history[0] == DEFECT:
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class SpiteEngine(Powerup):
    bonus: int = 1
    name: str = "Spite Engine"
    description: str = "If retaliation triggers, your defection gains bonus points. In a mutual-defection spiral, gain +1 more."
    synergy_tags: ClassVar[tuple[str, ...]] = ("retaliation_payoff", "rewards_betrayal", "payoff")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if ROUND_EVENT_RETALIATION_TRIGGERED in context.combo_events:
            my_points += self.bonus
            if ROUND_EVENT_MUTUAL_DEFECTION_SPIRAL in context.combo_events:
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class MercyShield(Powerup):
    name: str = "Mercy Shield"
    description: str = "After opponent defected last round, they gain no points from defecting this round. If retaliation triggers, gain +1."
    synergy_tags: ClassVar[tuple[str, ...]] = ("retaliation_payoff", "control", "amplifier")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if context.opp_history and context.opp_history[-1] == DEFECT and opp_move == DEFECT:
            opp_points = 0
            if ROUND_EVENT_RETALIATION_TRIGGERED in context.combo_events:
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class GoldenHandshake(Powerup):
    name: str = "Golden Handshake"
    description: str = "On round 1, lock both players into cooperation."
    synergy_tags: ClassVar[tuple[str, ...]] = ("creates_lock", "rewards_mutual_coop", "anchor")

    def self_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.round_index == 0:
            return [MoveDirective(move=COOPERATE, priority=DirectivePriority.LOCK, source=self.name)]
        return []

    def opponent_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.round_index == 0:
            return [MoveDirective(move=COOPERATE, priority=DirectivePriority.LOCK, source=self.name)]
        return []


@dataclass(slots=True)
class CoerciveControl(Powerup):
    name: str = "Coercive Control"
    description: str = "After you defect into their cooperation, force them to cooperate again next round. Betrayal into forced cooperation gains +1."
    synergy_tags: ClassVar[tuple[str, ...]] = ("creates_force", "rewards_force", "anchor")

    def opponent_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.my_history and context.opp_history:
            if context.my_history[-1] == DEFECT and context.opp_history[-1] == COOPERATE:
                return [MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source=self.name)]
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if ROUND_EVENT_FORCED_OPPONENT_COOP in context.combo_events and ROUND_EVENT_BETRAYAL_INTO_COOP in context.combo_events:
            my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class CounterIntel(Powerup):
    name: str = "Counter-Intel"
    description: str = "If they defected last round, force them toward cooperation. If that becomes mutual cooperation this round, gain +1."
    synergy_tags: ClassVar[tuple[str, ...]] = ("creates_force", "retaliation_payoff", "bridge")

    def opponent_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.opp_history and context.opp_history[-1] == DEFECT:
            return [MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source=self.name)]
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if ROUND_EVENT_FORCED_OPPONENT_COOP in context.combo_events and my_move == COOPERATE and opp_move == COOPERATE:
            my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class PanicButton(Powerup):
    name: str = "Panic Button"
    description: str = "After mutual defection, lock both players into defection next round. In that spiral, your defection gains +1."
    synergy_tags: ClassVar[tuple[str, ...]] = ("creates_lock", "chaos", "anchor")

    def self_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.my_history and context.opp_history:
            if context.my_history[-1] == DEFECT and context.opp_history[-1] == DEFECT:
                return [MoveDirective(move=DEFECT, priority=DirectivePriority.LOCK, source=self.name)]
        return []

    def opponent_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.my_history and context.opp_history:
            if context.my_history[-1] == DEFECT and context.opp_history[-1] == DEFECT:
                return [MoveDirective(move=DEFECT, priority=DirectivePriority.LOCK, source=self.name)]
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if ROUND_EVENT_MUTUAL_DEFECTION_SPIRAL in context.combo_events:
            my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class ComplianceDividend(Powerup):
    bonus: int = 1
    name: str = "Compliance Dividend"
    description: str = "If you betray into cooperation, gain bonus points. Gain +1 when cooperation was forced, +1 on retaliation conversion, and +1 on final-round betrayal."
    synergy_tags: ClassVar[tuple[str, ...]] = ("rewards_force", "rewards_betrayal", "payoff")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if ROUND_EVENT_BETRAYAL_INTO_COOP in context.combo_events:
            my_points += self.bonus
            if ROUND_EVENT_FORCED_OPPONENT_COOP in context.combo_events:
                my_points += 1
            if ROUND_EVENT_RETALIATION_TRIGGERED in context.combo_events:
                my_points += 1
            if ROUND_EVENT_FINAL_ROUND_BETRAYAL in context.combo_events:
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class UnityTicket(Powerup):
    name: str = "Unity Ticket"
    description: str = "Your referendum vote is forced to cooperation. If that controlled vote helps a cooperation bloc win, gain +1 referendum point."
    synergy_tags: ClassVar[tuple[str, ...]] = ("referendum_control", "rewards_mutual_coop", "enabler")

    def self_referendum_directives(self, *, owner: "Agent", context: ReferendumContext) -> list[MoveDirective]:
        return [MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source=self.name)]

    def on_referendum_reward(self, *, owner: "Agent", my_vote: int, cooperation_prevailed: bool, current_reward: int, context: ReferendumContext) -> int:
        if REFERENDUM_EVENT_CONTROLLED_VOTE in context.combo_events and REFERENDUM_EVENT_COOP_BLOC_WIN in context.combo_events:
            return current_reward + 1
        return current_reward


@dataclass(slots=True)
class SaboteurBloc(Powerup):
    name: str = "Saboteur Bloc"
    description: str = "Your referendum vote is forced to defection. If that controlled vote helps sabotage prevail, gain +1 referendum point."
    synergy_tags: ClassVar[tuple[str, ...]] = ("referendum_control", "rewards_betrayal", "enabler")

    def self_referendum_directives(self, *, owner: "Agent", context: ReferendumContext) -> list[MoveDirective]:
        return [MoveDirective(move=DEFECT, priority=DirectivePriority.FORCE, source=self.name)]

    def on_referendum_reward(self, *, owner: "Agent", my_vote: int, cooperation_prevailed: bool, current_reward: int, context: ReferendumContext) -> int:
        if REFERENDUM_EVENT_CONTROLLED_VOTE in context.combo_events and REFERENDUM_EVENT_SABOTAGE_BLOC_WIN in context.combo_events:
            return current_reward + 1
        return current_reward


@dataclass(slots=True)
class BlocPolitics(Powerup):
    bonus: int = 2
    name: str = "Bloc Politics"
    description: str = "If cooperation wins and you cooperated, gain bonus referendum points. Controlled-vote wins gain +1 more."
    synergy_tags: ClassVar[tuple[str, ...]] = ("rewards_mutual_coop", "referendum_control", "amplifier")

    def on_referendum_reward(self, *, owner: "Agent", my_vote: int, cooperation_prevailed: bool, current_reward: int, context: ReferendumContext) -> int:
        if REFERENDUM_EVENT_COOP_BLOC_WIN in context.combo_events:
            reward = current_reward + self.bonus
            if REFERENDUM_EVENT_CONTROLLED_VOTE in context.combo_events:
                reward += 1
            return reward
        return current_reward


ALL_POWERUP_TYPES = [
    OpeningGambit,
    TrustDividend,
    LastLaugh,
    SpiteEngine,
    MercyShield,
    GoldenHandshake,
    CoerciveControl,
    CounterIntel,
    PanicButton,
    ComplianceDividend,
    UnityTicket,
    SaboteurBloc,
    BlocPolitics,
]
