from __future__ import annotations

from dataclasses import dataclass

from prisoners_gambit.core.powerups import (
    ALL_POWERUP_TYPES,
    BlocPolitics,
    CoerciveControl,
    ComplianceDividend,
    ConcordatProtocol,
    CounterIntel,
    GoldenHandshake,
    IronDecree,
    LastLaugh,
    MandateForge,
    MercyShield,
    OpeningGambit,
    PanicButton,
    Powerup,
    SaboteurBloc,
    SchismRitual,
    ShadowSuccession,
    SpiteEngine,
    TrustDividend,
    UnityTicket,
    VendettaStatute,
)


@dataclass(frozen=True, slots=True)
class PowerupPresentationMetadata:
    trigger: str
    effect: str
    role_hint: str
    crown_hint: str | None = None

    @property
    def role_text(self) -> str:
        return self.role_hint


CROWN_HINT = "Crown move"


POWERUP_PRESENTATION_METADATA: dict[type[Powerup], PowerupPresentationMetadata] = {
    OpeningGambit: PowerupPresentationMetadata(
        trigger="Round 1 if you defect",
        effect="Gain bonus points for the opening betrayal",
        role_hint="Tempo opener",
    ),
    TrustDividend: PowerupPresentationMetadata(
        trigger="Any mutual cooperation round",
        effect="Gain bonus points, plus extra when peace was lock-stabilized",
        role_hint="Peace payoff",
    ),
    LastLaugh: PowerupPresentationMetadata(
        trigger="Final-round betrayal into cooperation",
        effect="Gain bonus points, plus extra if your opener was betrayal",
        role_hint="Closing payoff",
    ),
    SpiteEngine: PowerupPresentationMetadata(
        trigger="When retaliation is active",
        effect="Gain bonus points, plus extra in defection spirals",
        role_hint="Retaliation payoff",
    ),
    MercyShield: PowerupPresentationMetadata(
        trigger="After they defect twice in a row",
        effect="Blank their round payoff and add bonus in retaliation lanes",
        role_hint="Defensive amplifier",
    ),
    GoldenHandshake: PowerupPresentationMetadata(
        trigger="Round 1",
        effect="Lock both players into cooperation to seed trust",
        role_hint="Trust anchor",
    ),
    CoerciveControl: PowerupPresentationMetadata(
        trigger="After you betray into cooperation",
        effect="Force opponent cooperation next round and reward the follow-up betrayal",
        role_hint="Control anchor",
    ),
    CounterIntel: PowerupPresentationMetadata(
        trigger="After the opponent defects",
        effect="Force cooperation next round and cash it if the turn lands in peace",
        role_hint="Control bridge",
    ),
    PanicButton: PowerupPresentationMetadata(
        trigger="After mutual defection",
        effect="Lock both players into defection and turn the spiral into score",
        role_hint="Chaos anchor",
    ),
    ComplianceDividend: PowerupPresentationMetadata(
        trigger="Any betrayal into cooperation event",
        effect="Gain scaling bonus from forced cooperation, retaliation conversion, and final-round cashouts",
        role_hint="Forced payoff",
    ),
    UnityTicket: PowerupPresentationMetadata(
        trigger="At referendum resolution",
        effect="Force your vote to cooperate and gain +1 when controlled cooperation wins",
        role_hint="Vote enabler",
    ),
    SaboteurBloc: PowerupPresentationMetadata(
        trigger="At referendum resolution",
        effect="Force your vote to defect and gain +1 when controlled defection wins",
        role_hint="Vote enabler",
    ),
    BlocPolitics: PowerupPresentationMetadata(
        trigger="When the cooperation bloc wins the referendum",
        effect="Gain referendum bonus points, plus extra on controlled-vote wins",
        role_hint="Vote amplifier",
    ),
    ConcordatProtocol: PowerupPresentationMetadata(
        trigger="After mutual cooperation",
        effect="Lock both players into cooperation and gain +2 on locked peace",
        role_hint="Peace anchor",
        crown_hint=CROWN_HINT,
    ),
    IronDecree: PowerupPresentationMetadata(
        trigger="Every third round",
        effect="Force opponent cooperation and gain +2 on forced betrayal conversion",
        role_hint="Control anchor",
        crown_hint=CROWN_HINT,
    ),
    VendettaStatute: PowerupPresentationMetadata(
        trigger="After the opponent defects",
        effect="Lock your next move to defection and gain +2 on retaliation rounds",
        role_hint="Retaliation payoff",
        crown_hint=CROWN_HINT,
    ),
    ShadowSuccession: PowerupPresentationMetadata(
        trigger="Round 1 and the final round",
        effect="Force your betrayal timing and heavily reward betrayal into cooperation",
        role_hint="Succession anchor",
        crown_hint=CROWN_HINT,
    ),
    MandateForge: PowerupPresentationMetadata(
        trigger="At referendum resolution",
        effect="Alternate vote control and gain +2 on controlled bloc wins",
        role_hint="Vote anchor",
        crown_hint=CROWN_HINT,
    ),
    SchismRitual: PowerupPresentationMetadata(
        trigger="Every round",
        effect="Alternate forced stance and gain +2 on non-mirrored outcomes",
        role_hint="Chaos anchor",
        crown_hint=CROWN_HINT,
    ),
}


def presentation_for_powerup(powerup: Powerup) -> PowerupPresentationMetadata:
    powerup_type = type(powerup)
    if powerup_type not in POWERUP_PRESENTATION_METADATA:
        raise KeyError(f"Missing powerup presentation metadata for {powerup_type.__name__}")
    return POWERUP_PRESENTATION_METADATA[powerup_type]


def all_powerups_have_presentation_metadata() -> bool:
    return set(ALL_POWERUP_TYPES) == set(POWERUP_PRESENTATION_METADATA)
