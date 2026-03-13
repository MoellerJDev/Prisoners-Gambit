from __future__ import annotations

from dataclasses import dataclass, replace
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


@dataclass(slots=True)
class ReferendumContext:
    floor_number: int
    total_agents: int
    current_floor_score: int


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


class Powerup:
    name: str = "Unnamed Powerup"
    description: str = "No description available."
    synergy_tags: ClassVar[tuple[str, ...]] = ()

    @property
    def keywords(self) -> tuple[str, ...]:
        return self.synergy_tags

    def self_move_directives(
        self,
        *,
        owner: "Agent",
        opponent: "Agent",
        context: RoundContext,
    ) -> list[MoveDirective]:
        return []

    def opponent_move_directives(
        self,
        *,
        owner: "Agent",
        opponent: "Agent",
        context: RoundContext,
    ) -> list[MoveDirective]:
        return []

    def on_score(
        self,
        *,
        owner: "Agent",
        opponent: "Agent",
        my_move: int,
        opp_move: int,
        my_points: int,
        opp_points: int,
        context: RoundContext,
    ) -> tuple[int, int]:
        return my_points, opp_points

    def self_referendum_directives(
        self,
        *,
        owner: "Agent",
        context: ReferendumContext,
    ) -> list[MoveDirective]:
        return []

    def on_referendum_reward(
        self,
        *,
        owner: "Agent",
        my_vote: int,
        cooperation_prevailed: bool,
        current_reward: int,
        context: ReferendumContext,
    ) -> int:
        return current_reward

    def clone(self) -> "Powerup":
        return replace(self)


def owner_has_keyword(owner: "Agent", keyword: str) -> bool:
    return any(keyword in powerup.keywords for powerup in owner.powerups)


@dataclass(slots=True)
class OpeningGambit(Powerup):
    bonus: int = 1
    name: str = "Opening Gambit"
    description: str = "If you defect on round 1, gain bonus points. Gain +1 more if your lineage carries a final-round payoff."
    synergy_tags: ClassVar[tuple[str, ...]] = ("opportunist", "rewards_betrayal", "enabler")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if context.round_index == 0 and my_move == DEFECT:
            my_points += self.bonus
            if owner_has_keyword(owner, "final_round_payoff"):
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class TrustDividend(Powerup):
    bonus: int = 1
    name: str = "Trust Dividend"
    description: str = "Mutual cooperation gives bonus points. If it happens in consecutive rounds, gain +1 more."
    synergy_tags: ClassVar[tuple[str, ...]] = ("rewards_mutual_coop", "coalition", "payoff")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if my_move == COOPERATE and opp_move == COOPERATE:
            my_points += self.bonus
            if context.my_history and context.opp_history and context.my_history[-1] == COOPERATE and context.opp_history[-1] == COOPERATE:
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class LastLaugh(Powerup):
    bonus: int = 1
    name: str = "Last Laugh"
    description: str = "Force defect on the final round. If they cooperate into it, gain bonus points (+1 more after an opening betrayal)."
    synergy_tags: ClassVar[tuple[str, ...]] = ("opportunist", "final_round_payoff", "rewards_betrayal", "payoff")

    def self_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.round_index == context.total_rounds - 1:
            return [MoveDirective(move=DEFECT, priority=DirectivePriority.OVERRIDE, source=self.name)]
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if context.round_index == context.total_rounds - 1 and my_move == DEFECT and opp_move == COOPERATE:
            my_points += self.bonus
            if context.my_history and context.my_history[0] == DEFECT and owner_has_keyword(owner, "opportunist"):
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class SpiteEngine(Powerup):
    bonus: int = 1
    name: str = "Spite Engine"
    description: str = "If opponent defected last round, your defect gains bonus points. Gain +1 more when the feud has already collapsed into mutual defection."
    synergy_tags: ClassVar[tuple[str, ...]] = ("retaliation_payoff", "rewards_betrayal", "payoff")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if context.opp_history and context.opp_history[-1] == DEFECT and my_move == DEFECT:
            my_points += self.bonus
            if context.my_history and context.my_history[-1] == DEFECT:
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class MercyShield(Powerup):
    name: str = "Mercy Shield"
    description: str = "After opponent defected last round, they gain no points from defecting this round. If you retaliate, gain +1."
    synergy_tags: ClassVar[tuple[str, ...]] = ("retaliation_payoff", "control", "amplifier")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if context.opp_history and context.opp_history[-1] == DEFECT and opp_move == DEFECT:
            opp_points = 0
            if my_move == DEFECT and owner_has_keyword(owner, "retaliation_payoff"):
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
    description: str = "After you defect into their cooperation, force them to cooperate again next round. Exploiting that compliance grants +1."
    synergy_tags: ClassVar[tuple[str, ...]] = ("creates_force", "rewards_force", "anchor")

    def opponent_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.my_history and context.opp_history:
            if context.my_history[-1] == DEFECT and context.opp_history[-1] == COOPERATE:
                return [MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source=self.name)]
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if my_move == DEFECT and opp_move == COOPERATE and owner_has_keyword(owner, "rewards_force"):
            my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class CounterIntel(Powerup):
    name: str = "Counter-Intel"
    description: str = "If they defected last round, force them toward cooperation. If that turns into mutual cooperation, gain +1."
    synergy_tags: ClassVar[tuple[str, ...]] = ("creates_force", "retaliation_payoff", "bridge")

    def opponent_move_directives(self, *, owner: "Agent", opponent: "Agent", context: RoundContext) -> list[MoveDirective]:
        if context.opp_history and context.opp_history[-1] == DEFECT:
            return [MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source=self.name)]
        return []

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if context.opp_history and context.opp_history[-1] == DEFECT and my_move == COOPERATE and opp_move == COOPERATE:
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
        if context.my_history and context.opp_history and context.my_history[-1] == DEFECT and context.opp_history[-1] == DEFECT and my_move == DEFECT:
            my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class ComplianceDividend(Powerup):
    bonus: int = 1
    name: str = "Compliance Dividend"
    description: str = "If you defect into opponent cooperation, gain bonus points. Gain +1 more after recent betrayal, and +1 more if your lineage can force compliance."
    synergy_tags: ClassVar[tuple[str, ...]] = ("rewards_force", "rewards_betrayal", "payoff")

    def on_score(self, *, owner: "Agent", opponent: "Agent", my_move: int, opp_move: int, my_points: int, opp_points: int, context: RoundContext) -> tuple[int, int]:
        if my_move == DEFECT and opp_move == COOPERATE:
            my_points += self.bonus
            if context.opp_history and context.opp_history[-1] == DEFECT:
                my_points += 1
            if owner_has_keyword(owner, "creates_force"):
                my_points += 1
            if context.round_index == context.total_rounds - 1 and owner_has_keyword(owner, "opportunist"):
                my_points += 1
        return my_points, opp_points


@dataclass(slots=True)
class UnityTicket(Powerup):
    name: str = "Unity Ticket"
    description: str = "Your referendum vote is forced to cooperation. If cooperation prevails and your lineage rewards trust, gain +1 referendum point."
    synergy_tags: ClassVar[tuple[str, ...]] = ("referendum_control", "rewards_mutual_coop", "enabler")

    def self_referendum_directives(self, *, owner: "Agent", context: ReferendumContext) -> list[MoveDirective]:
        return [MoveDirective(move=COOPERATE, priority=DirectivePriority.FORCE, source=self.name)]

    def on_referendum_reward(self, *, owner: "Agent", my_vote: int, cooperation_prevailed: bool, current_reward: int, context: ReferendumContext) -> int:
        if cooperation_prevailed and my_vote == COOPERATE and owner_has_keyword(owner, "rewards_mutual_coop"):
            return current_reward + 1
        return current_reward


@dataclass(slots=True)
class SaboteurBloc(Powerup):
    name: str = "Saboteur Bloc"
    description: str = "Your referendum vote is forced to defection. If defection prevails, gain +1 referendum point."
    synergy_tags: ClassVar[tuple[str, ...]] = ("referendum_control", "rewards_betrayal", "enabler")

    def self_referendum_directives(self, *, owner: "Agent", context: ReferendumContext) -> list[MoveDirective]:
        return [MoveDirective(move=DEFECT, priority=DirectivePriority.FORCE, source=self.name)]

    def on_referendum_reward(self, *, owner: "Agent", my_vote: int, cooperation_prevailed: bool, current_reward: int, context: ReferendumContext) -> int:
        if not cooperation_prevailed and my_vote == DEFECT:
            return current_reward + 1
        return current_reward


@dataclass(slots=True)
class BlocPolitics(Powerup):
    bonus: int = 2
    name: str = "Bloc Politics"
    description: str = "If cooperation wins and you cooperated, gain bonus referendum points. Gain +1 for coalition trust builds and +1 for referendum-control builds."
    synergy_tags: ClassVar[tuple[str, ...]] = ("rewards_mutual_coop", "referendum_control", "amplifier")

    def on_referendum_reward(self, *, owner: "Agent", my_vote: int, cooperation_prevailed: bool, current_reward: int, context: ReferendumContext) -> int:
        if cooperation_prevailed and my_vote == COOPERATE:
            reward = current_reward + self.bonus
            if owner_has_keyword(owner, "coalition"):
                reward += 1
            if owner_has_keyword(owner, "referendum_control"):
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
