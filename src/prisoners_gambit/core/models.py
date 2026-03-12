from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count

from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.core.strategy import StrategyGenome

_AGENT_ID_SEQUENCE = count(1)


@dataclass(slots=True)
class Agent:
    name: str
    genome: StrategyGenome
    public_profile: str = "Unclassified"
    powerups: list[Powerup] = field(default_factory=list)
    score: int = 0
    wins: int = 0
    is_player: bool = False
    lineage_id: int | None = None
    lineage_depth: int = 0
    agent_id: int = field(default_factory=lambda: next(_AGENT_ID_SEQUENCE))

    def reset_for_floor(self) -> None:
        self.score = 0
        self.wins = 0

    def clone_for_offspring(
        self,
        genome: StrategyGenome,
        name_override: str | None = None,
        inherited_powerups: list[Powerup] | None = None,
    ) -> "Agent":
        inherited = inherited_powerups if inherited_powerups is not None else [powerup.clone() for powerup in self.powerups[:3]]
        return Agent(
            name=name_override or f"{self.name}*",
            genome=genome,
            public_profile=self.public_profile,
            powerups=inherited,
            is_player=False,
            lineage_id=self.lineage_id,
            lineage_depth=self.lineage_depth + 1,
        )

    def build_summary(self) -> str:
        powerup_names = ", ".join(powerup.name for powerup in self.powerups)
        if not powerup_names:
            powerup_names = "No powerups"
        player_marker = "[YOU] " if self.is_player else ""
        return f"{player_marker}{self.name} | {self.public_profile} | {self.genome.summary()} | {powerup_names}"
