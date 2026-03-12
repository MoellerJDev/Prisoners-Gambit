from __future__ import annotations

from dataclasses import dataclass

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.strategy import StrategyGenome


class GenomeEdit:
    name: str = "Unnamed Edit"
    description: str = "No description."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        return genome

    def clone(self) -> "GenomeEdit":
        return type(self)()


def _copy_genome(genome: StrategyGenome) -> StrategyGenome:
    return StrategyGenome(
        first_move=genome.first_move,
        response_table=dict(genome.response_table),
        noise=genome.noise,
    )


@dataclass(slots=True)
class OpenWithTrust(GenomeEdit):
    name: str = "Open With Trust"
    description: str = "Your autopilot opens matches with cooperation."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.first_move = COOPERATE
        return updated


@dataclass(slots=True)
class OpenWithKnife(GenomeEdit):
    name: str = "Open With Knife"
    description: str = "Your autopilot opens matches with defection."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.first_move = DEFECT
        return updated


@dataclass(slots=True)
class PunishBetrayal(GenomeEdit):
    name: str = "Punish Betrayal"
    description: str = "If you cooperated and they defected, defect next round."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.response_table[(COOPERATE, DEFECT)] = DEFECT
        return updated


@dataclass(slots=True)
class PreservePeace(GenomeEdit):
    name: str = "Preserve Peace"
    description: str = "If both cooperated, cooperate again next round."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.response_table[(COOPERATE, COOPERATE)] = COOPERATE
        return updated


@dataclass(slots=True)
class PressAdvantage(GenomeEdit):
    name: str = "Press Advantage"
    description: str = "If you defected and they cooperated, defect again next round."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.response_table[(DEFECT, COOPERATE)] = DEFECT
        return updated


@dataclass(slots=True)
class CalmTheNoise(GenomeEdit):
    name: str = "Calm the Noise"
    description: str = "Reduce autopilot randomness."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.noise = max(0.0, updated.noise - 0.05)
        return updated


@dataclass(slots=True)
class EmbraceChaos(GenomeEdit):
    name: str = "Embrace Chaos"
    description: str = "Increase autopilot randomness a little."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.noise = min(0.35, updated.noise + 0.05)
        return updated


@dataclass(slots=True)
class FortressDoctrine(GenomeEdit):
    name: str = "Fortress Doctrine"
    description: str = "Become a safer heir: open C, preserve C/C, forgive D/D, and lower noise."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.first_move = COOPERATE
        updated.response_table[(COOPERATE, COOPERATE)] = COOPERATE
        updated.response_table[(DEFECT, DEFECT)] = COOPERATE
        updated.noise = max(0.0, updated.noise - 0.08)
        return updated


@dataclass(slots=True)
class TyrantDoctrine(GenomeEdit):
    name: str = "Tyrant Doctrine"
    description: str = "Become a ruthless heir: open D and keep pressing after advantage or betrayal."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.first_move = DEFECT
        updated.response_table[(COOPERATE, DEFECT)] = DEFECT
        updated.response_table[(DEFECT, COOPERATE)] = DEFECT
        updated.response_table[(DEFECT, DEFECT)] = DEFECT
        updated.noise = min(0.35, updated.noise + 0.02)
        return updated


@dataclass(slots=True)
class WildcardDoctrine(GenomeEdit):
    name: str = "Wildcard Doctrine"
    description: str = "Become an unstable heir: increase noise sharply and flip core responses."

    def apply(self, genome: StrategyGenome) -> StrategyGenome:
        updated = _copy_genome(genome)
        updated.response_table[(COOPERATE, COOPERATE)] = DEFECT
        updated.response_table[(COOPERATE, DEFECT)] = DEFECT
        updated.response_table[(DEFECT, COOPERATE)] = COOPERATE
        updated.noise = min(0.35, updated.noise + 0.12)
        return updated
