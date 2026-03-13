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
        return f"Role: {self.role_hint}."


CROWN_HINT = "Crown piece · dynasty-defining"


POWERUP_PRESENTATION_METADATA: dict[type[Powerup], PowerupPresentationMetadata] = {
    OpeningGambit: PowerupPresentationMetadata(
        trigger="Trigger: Round 1 and you defect.",
        effect="Effect: Gain bonus points for the opening betrayal.",
        role_hint="enabler",
    ),
    TrustDividend: PowerupPresentationMetadata(
        trigger="Trigger: This round is mutual cooperation.",
        effect="Effect: Gain bonus points, plus extra when cooperation was lock-stabilized.",
        role_hint="payoff",
    ),
    LastLaugh: PowerupPresentationMetadata(
        trigger="Trigger: Final-round betrayal into opponent cooperation.",
        effect="Effect: Gain bonus points, plus extra if your opener was betrayal.",
        role_hint="payoff",
    ),
    SpiteEngine: PowerupPresentationMetadata(
        trigger="Trigger: Retaliation event is active (you defect after their prior defection).",
        effect="Effect: Gain bonus points, plus extra in defection spirals.",
        role_hint="payoff",
    ),
    MercyShield: PowerupPresentationMetadata(
        trigger="Trigger: Opponent defected last round and defects again.",
        effect="Effect: Nullify their round payoff and gain bonus when retaliation is active.",
        role_hint="amplifier",
    ),
    GoldenHandshake: PowerupPresentationMetadata(
        trigger="Trigger: Round 1.",
        effect="Effect: Lock both players into cooperation to seed trust events.",
        role_hint="anchor",
    ),
    CoerciveControl: PowerupPresentationMetadata(
        trigger="Trigger: Previous round was your betrayal into their cooperation.",
        effect="Effect: Force opponent cooperation next round and reward forced-betrayal conversion.",
        role_hint="anchor",
    ),
    CounterIntel: PowerupPresentationMetadata(
        trigger="Trigger: Opponent defected last round.",
        effect="Effect: Force their cooperation and convert it into trust payoff if peace lands.",
        role_hint="bridge",
    ),
    PanicButton: PowerupPresentationMetadata(
        trigger="Trigger: Previous round was mutual defection.",
        effect="Effect: Lock both players into defection and convert spiral pressure into score.",
        role_hint="anchor",
    ),
    ComplianceDividend: PowerupPresentationMetadata(
        trigger="Trigger: Betrayal into cooperation event.",
        effect="Effect: Gain scaling bonus from forced cooperation, retaliation conversion, and final-round cashouts.",
        role_hint="payoff",
    ),
    UnityTicket: PowerupPresentationMetadata(
        trigger="Trigger: Referendum vote resolution.",
        effect="Effect: Force your vote to cooperation and gain +1 when controlled cooperation wins.",
        role_hint="enabler",
    ),
    SaboteurBloc: PowerupPresentationMetadata(
        trigger="Trigger: Referendum vote resolution.",
        effect="Effect: Force your vote to sabotage and gain +1 when controlled sabotage wins.",
        role_hint="enabler",
    ),
    BlocPolitics: PowerupPresentationMetadata(
        trigger="Trigger: Cooperation bloc wins the referendum.",
        effect="Effect: Gain referendum bonus points, plus extra on controlled-vote wins.",
        role_hint="amplifier",
    ),
    ConcordatProtocol: PowerupPresentationMetadata(
        trigger="Trigger: Last round ended in mutual cooperation.",
        effect="Effect: Lock both players into cooperation and gain +2 on locked peace.",
        role_hint="anchor",
        crown_hint=CROWN_HINT,
    ),
    IronDecree: PowerupPresentationMetadata(
        trigger="Trigger: Every third round.",
        effect="Effect: Force opponent cooperation and gain +2 on forced betrayal conversion.",
        role_hint="anchor",
        crown_hint=CROWN_HINT,
    ),
    VendettaStatute: PowerupPresentationMetadata(
        trigger="Trigger: Opponent defected last round.",
        effect="Effect: Lock your next move to defection and gain +2 on retaliation rounds.",
        role_hint="payoff",
        crown_hint=CROWN_HINT,
    ),
    ShadowSuccession: PowerupPresentationMetadata(
        trigger="Trigger: Round 1 and final round.",
        effect="Effect: Force your betrayal timing and heavily reward betrayal into cooperation.",
        role_hint="anchor",
        crown_hint=CROWN_HINT,
    ),
    MandateForge: PowerupPresentationMetadata(
        trigger="Trigger: Referendum vote resolution.",
        effect="Effect: Alternate vote control and gain +2 on controlled bloc wins.",
        role_hint="anchor",
        crown_hint=CROWN_HINT,
    ),
    SchismRitual: PowerupPresentationMetadata(
        trigger="Trigger: Every round.",
        effect="Effect: Alternate forced stance and gain +2 on non-mirrored outcomes.",
        role_hint="anchor",
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
