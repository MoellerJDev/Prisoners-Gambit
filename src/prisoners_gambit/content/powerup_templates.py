from __future__ import annotations

from prisoners_gambit.core.powerups import (
    BlocPolitics,
    CoerciveControl,
    ComplianceDividend,
    CounterIntel,
    GoldenHandshake,
    LastLaugh,
    MercyShield,
    OpeningGambit,
    PanicButton,
    Powerup,
    SaboteurBloc,
    SpiteEngine,
    TrustDividend,
    UnityTicket,
)


def build_powerup_pool() -> list[Powerup]:
    return [
        OpeningGambit(bonus=1),
        OpeningGambit(bonus=2),
        TrustDividend(bonus=1),
        TrustDividend(bonus=2),
        LastLaugh(),
        SpiteEngine(bonus=1),
        SpiteEngine(bonus=2),
        MercyShield(),
        GoldenHandshake(),
        CoerciveControl(),
        CounterIntel(),
        PanicButton(),
        ComplianceDividend(bonus=1),
        ComplianceDividend(bonus=2),
        UnityTicket(),
        SaboteurBloc(),
        BlocPolitics(bonus=2),
        BlocPolitics(bonus=3),
    ]