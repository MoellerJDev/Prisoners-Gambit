from __future__ import annotations

from dataclasses import dataclass

from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.powerups import Powerup


@dataclass(frozen=True, slots=True)
class OfferDoctrineGuidance:
    doctrine_vector: str
    branch_identity: str
    tradeoff: str
    phase_support: str
    successor_pressure: str


_POWERUP_GUIDANCE_BY_NAME: dict[str, OfferDoctrineGuidance] = {
    "Trust Dividend": OfferDoctrineGuidance(
        doctrine_vector="trust / reciprocity",
        branch_identity="Reciprocal stabilizers",
        tradeoff="Higher ecosystem trust, slower duel tempo when betrayed.",
        phase_support="ecosystem survival",
        successor_pressure="Future heirs trend toward safe successors and doctrine continuity.",
    ),
    "Mercy Shield": OfferDoctrineGuidance(
        doctrine_vector="survivability / stabilization",
        branch_identity="Defensive stabilizers",
        tradeoff="Blunts retaliation spirals, gives up explosive punish windows.",
        phase_support="ecosystem survival",
        successor_pressure="Pushes heir pool toward stable responders over civil-war enforcers.",
    ),
    "Golden Handshake": OfferDoctrineGuidance(
        doctrine_vector="trust / reciprocity",
        branch_identity="Consensus architects",
        tradeoff="Secures opening peace, reduces first-round opportunism.",
        phase_support="ecosystem survival",
        successor_pressure="Reinforces cooperative lineage trend and moderates doctrine drift.",
    ),
    "Opening Gambit": OfferDoctrineGuidance(
        doctrine_vector="opportunism / betrayal",
        branch_identity="Tempo raiders",
        tradeoff="Fast scoreboard spikes, invites counter-punish coalitions.",
        phase_support="civil-war readiness",
        successor_pressure="Selects for heirs with ruthless opener DNA.",
    ),
    "Spite Engine": OfferDoctrineGuidance(
        doctrine_vector="coercion / control",
        branch_identity="Retaliation enforcers",
        tradeoff="Converts grudges into value, narrows reconciliation lanes.",
        phase_support="civil-war readiness",
        successor_pressure="Raises chance of punishing successors and branch-mirror escalation.",
    ),
    "Compliance Dividend": OfferDoctrineGuidance(
        doctrine_vector="coercion / control",
        branch_identity="Compliance extractors",
        tradeoff="Rewards forced obedience, can unify outsiders against you.",
        phase_support="civil-war readiness",
        successor_pressure="Drifts toward control-heavy heirs with higher civil-war pressure.",
    ),
    "Last Laugh": OfferDoctrineGuidance(
        doctrine_vector="opportunism / betrayal",
        branch_identity="Endgame betrayers",
        tradeoff="Reliable final-round theft, weaker long-cycle trust building.",
        phase_support="civil-war readiness",
        successor_pressure="Cultivates heirs built for decisive betrayals.",
    ),
    "Unity Ticket": OfferDoctrineGuidance(
        doctrine_vector="referendum leverage",
        branch_identity="Referendum loyalists",
        tradeoff="Secures bloc cooperation value, sacrifices vote flexibility.",
        phase_support="ecosystem survival",
        successor_pressure="Keeps successor dilemmas centered on floor-vote doctrine.",
    ),
    "Saboteur Bloc": OfferDoctrineGuidance(
        doctrine_vector="referendum leverage",
        branch_identity="Referendum saboteurs",
        tradeoff="Denies cooperation payouts, weakens coalition trust.",
        phase_support="both",
        successor_pressure="Favors heirs who weaponize referendum deadlocks.",
    ),
    "Bloc Politics": OfferDoctrineGuidance(
        doctrine_vector="referendum leverage",
        branch_identity="Vote-market brokers",
        tradeoff="Strong if blocs align, low value in duel-only pacing.",
        phase_support="ecosystem survival",
        successor_pressure="Increases pull toward referendum-specialist successors.",
    ),
    "Coercive Control": OfferDoctrineGuidance(
        doctrine_vector="coercion / control",
        branch_identity="Behavior controllers",
        tradeoff="Locks opponents into scripts, exposes you if control breaks.",
        phase_support="both",
        successor_pressure="Signals doctrine drift toward control-tagged heirs.",
    ),
    "Counter-Intel": OfferDoctrineGuidance(
        doctrine_vector="coercion / control",
        branch_identity="Counter-coercion wardens",
        tradeoff="Punishes defect loops, lower payoff when tables stay peaceful.",
        phase_support="both",
        successor_pressure="Supports heirs who can answer control mirrors in civil war.",
    ),
    "Panic Button": OfferDoctrineGuidance(
        doctrine_vector="volatility / chaos",
        branch_identity="Spiral accelerants",
        tradeoff="Prevents exploitation streaks, magnifies chaos once fights ignite.",
        phase_support="civil-war readiness",
        successor_pressure="Pulls doctrine toward unstable successor pools.",
    ),
    "Concordat Protocol": OfferDoctrineGuidance(
        doctrine_vector="trust / reciprocity",
        branch_identity="Concordat monarchs",
        tradeoff="Creates peace lock-in engines, weaker when trust chain is broken.",
        phase_support="ecosystem survival",
        successor_pressure="Hard-commits heirs to high-trust doctrine loops.",
    ),
    "Iron Decree": OfferDoctrineGuidance(
        doctrine_vector="coercion / control",
        branch_identity="Decree enforcers",
        tradeoff="Reliable scripted compliance, expensive when forced tempo whiffs.",
        phase_support="both",
        successor_pressure="Pushes successors toward command-and-control lineages.",
    ),
    "Vendetta Statute": OfferDoctrineGuidance(
        doctrine_vector="coercion / control",
        branch_identity="Vendetta jurists",
        tradeoff="Turns grievances into guaranteed retaliation lanes.",
        phase_support="civil-war readiness",
        successor_pressure="Escalates branch-mirror feud doctrine in heirs.",
    ),
    "Shadow Succession": OfferDoctrineGuidance(
        doctrine_vector="opportunism / betrayal",
        branch_identity="Succession conspirators",
        tradeoff="Explosive betrayal timing, severe trust erosion at the table.",
        phase_support="civil-war readiness",
        successor_pressure="Selects heirs built for high-lethality betrayal pivots.",
    ),
    "Mandate Forge": OfferDoctrineGuidance(
        doctrine_vector="referendum leverage",
        branch_identity="Mandate smiths",
        tradeoff="High referendum swing power, predictable parity cadence.",
        phase_support="ecosystem survival",
        successor_pressure="Strengthens floor-vote specialist successor doctrine.",
    ),
    "Schism Ritual": OfferDoctrineGuidance(
        doctrine_vector="volatility / chaos",
        branch_identity="Schism celebrants",
        tradeoff="Huge volatility spikes, can fracture consistency under pressure.",
        phase_support="both",
        successor_pressure="Mutates succession pools toward unstable doctrine branches.",
    ),
}

_GENOME_GUIDANCE_BY_NAME: dict[str, OfferDoctrineGuidance] = {
    "Open With Trust": OfferDoctrineGuidance("trust / reciprocity", "Reciprocal openers", "Safer openings, softer first-hit pressure.", "ecosystem survival", "Biases heirs toward safe doctrine continuity."),
    "Open With Knife": OfferDoctrineGuidance("opportunism / betrayal", "Aggressive openers", "Wins early tempo, escalates retaliation risk.", "civil-war readiness", "Selects heirs that pivot lineage toward ruthless starts."),
    "Punish Betrayal": OfferDoctrineGuidance("coercion / control", "Punishment codifiers", "Deters exploiters, can trap branch in feud loops.", "both", "Increases punishing-heir frequency in later successor pools."),
    "Preserve Peace": OfferDoctrineGuidance("survivability / stabilization", "Peace preservers", "Stabilizes alliances, lowers burst conversion.", "ecosystem survival", "Moderates doctrine drift and keeps successor options broad."),
    "Press Advantage": OfferDoctrineGuidance("opportunism / betrayal", "Exploit consolidators", "Converts leads harder, weakens reconciliation options.", "civil-war readiness", "Pushes heir pressure toward ruthless branch roles."),
    "Calm the Noise": OfferDoctrineGuidance("survivability / stabilization", "Order keepers", "Reduces throw turns, sacrifices upset volatility.", "both", "Improves doctrine continuity and predictable heir fit."),
    "Embrace Chaos": OfferDoctrineGuidance("volatility / chaos", "Wildcard breeders", "Creates upset potential, increases self-inflicted collapse.", "civil-war readiness", "Expands unstable successor pool and harder succession dilemmas."),
    "Fortress Doctrine": OfferDoctrineGuidance("survivability / stabilization", "Safe-heir doctrine", "High resilience, lower duel ceiling versus tempo lines.", "ecosystem survival", "Strongly reinforces safe-heir lineage identity."),
    "Tyrant Doctrine": OfferDoctrineGuidance("coercion / control", "Ruthless-heir doctrine", "Dominates compliant tables, attracts anti-lineage focus.", "civil-war readiness", "Hard pivot toward civil-war enforcer successors."),
    "Wildcard Doctrine": OfferDoctrineGuidance("volatility / chaos", "Unstable-heir doctrine", "Maximum unpredictability, minimum reliability.", "civil-war readiness", "Sharp doctrine drift toward unstable successors."),
}


def _guidance_or_error(guidance_by_name: dict[str, OfferDoctrineGuidance], name: str, *, kind: str) -> OfferDoctrineGuidance:
    guidance = guidance_by_name.get(name)
    if guidance is None:
        raise KeyError(f"Missing doctrine guidance for {kind} '{name}'")
    return guidance


def guidance_for_powerup(powerup: Powerup) -> OfferDoctrineGuidance:
    return _guidance_or_error(_POWERUP_GUIDANCE_BY_NAME, powerup.name, kind="powerup")


def guidance_for_genome_edit(edit: GenomeEdit) -> OfferDoctrineGuidance:
    return _guidance_or_error(_GENOME_GUIDANCE_BY_NAME, edit.name, kind="genome edit")


def guidance_for_dynamic_powerup(name: str) -> OfferDoctrineGuidance | None:
    return _POWERUP_GUIDANCE_BY_NAME.get(name)


def guidance_for_dynamic_genome_edit(name: str) -> OfferDoctrineGuidance | None:
    return _GENOME_GUIDANCE_BY_NAME.get(name)


def validate_declared_guidance_coverage(*, powerup_names: set[str], genome_edit_names: set[str]) -> None:
    missing_powerups = sorted(powerup_names - set(_POWERUP_GUIDANCE_BY_NAME))
    missing_edits = sorted(genome_edit_names - set(_GENOME_GUIDANCE_BY_NAME))
    if missing_powerups or missing_edits:
        problems: list[str] = []
        if missing_powerups:
            problems.append(f"powerups={missing_powerups}")
        if missing_edits:
            problems.append(f"genome_edits={missing_edits}")
        raise ValueError("Missing doctrine guidance coverage: " + "; ".join(problems))


_COMMITMENT_BY_VECTOR: dict[str, str] = {
    "trust / reciprocity": "Builds heirs that profit from trust loops and reciprocal play.",
    "coercion / control": "Builds heirs that win by scripting compliance and punish windows.",
    "opportunism / betrayal": "Builds heirs that seize tempo through sharp betrayal timing.",
    "referendum leverage": "Builds heirs that control blocs and referendum leverage.",
    "volatility / chaos": "Builds heirs that trade stability for upset potential.",
    "survivability / stabilization": "Builds heirs that absorb shocks and preserve branch continuity.",
}


def lineage_commitment_text(guidance: OfferDoctrineGuidance) -> str:
    return _COMMITMENT_BY_VECTOR.get(guidance.doctrine_vector, "Keeps the house flexible without hard specialization.")


def doctrine_drift_text(guidance: OfferDoctrineGuidance) -> str:
    phase = guidance.phase_support or "both"
    if phase == "ecosystem survival":
        return "Shift: favors heirs built for ecosystem stewardship."
    if phase == "civil-war readiness":
        return "Shift: favors heirs built for civil-war mirrors."
    return "Shift: keeps both ecosystem and civil-war lanes active."
