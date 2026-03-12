from __future__ import annotations

from prisoners_gambit.core.genome_edits import (
    CalmTheNoise,
    EmbraceChaos,
    FortressDoctrine,
    GenomeEdit,
    OpenWithKnife,
    OpenWithTrust,
    PreservePeace,
    PressAdvantage,
    PunishBetrayal,
    TyrantDoctrine,
    WildcardDoctrine,
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
        FortressDoctrine(),
        TyrantDoctrine(),
        WildcardDoctrine(),
    ]
