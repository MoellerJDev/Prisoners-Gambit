from __future__ import annotations

from prisoners_gambit.core.genome_edits import (
    CalmTheNoise,
    EmbraceChaos,
    GenomeEdit,
    OpenWithKnife,
    OpenWithTrust,
    PreservePeace,
    PressAdvantage,
    PunishBetrayal,
)


def build_genome_edit_pool() -> list[GenomeEdit]:
    return [
        OpenWithTrust(),
        OpenWithKnife(),
        PunishBetrayal(),
        PreservePeace(),
        PressAdvantage(),
        CalmTheNoise(),
        EmbraceChaos(),
    ]