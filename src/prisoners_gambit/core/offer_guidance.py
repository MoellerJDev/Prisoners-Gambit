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


_DEFAULT_GUIDANCE = OfferDoctrineGuidance(
    doctrine_vector="survivability / stabilization",
    branch_identity="Mixed doctrine",
    tradeoff="Balanced adaptation with no extreme commitment.",
    phase_support="both",
    successor_pressure="Keeps succession pressure mixed rather than polarized.",
)


def guidance_for_powerup(powerup: Powerup) -> OfferDoctrineGuidance:
    return _POWERUP_GUIDANCE_BY_NAME.get(powerup.name, _DEFAULT_GUIDANCE)


def guidance_for_genome_edit(edit: GenomeEdit) -> OfferDoctrineGuidance:
    return _GENOME_GUIDANCE_BY_NAME.get(edit.name, _DEFAULT_GUIDANCE)


_COMMITMENT_BY_VECTOR: dict[str, str] = {
    "trust / reciprocity": "Choose if you want heirs to bank value through reciprocal trust loops.",
    "coercion / control": "Choose if you want heirs to win by enforcing compliance and punish lanes.",
    "opportunism / betrayal": "Choose if you want heirs to seize tempo through sharp betray windows.",
    "referendum leverage": "Choose if you want heirs to control blocs and referendum bargaining power.",
    "volatility / chaos": "Choose if you want heirs to embrace instability for upset potential.",
    "survivability / stabilization": "Choose if you want heirs to absorb shocks and preserve branch continuity.",
}


def lineage_commitment_text(guidance: OfferDoctrineGuidance) -> str:
    return _COMMITMENT_BY_VECTOR.get(guidance.doctrine_vector, "Choose if you want a balanced doctrine without a hard specialization.")


def doctrine_drift_text(guidance: OfferDoctrineGuidance) -> str:
    phase = guidance.phase_support or "both"
    if phase == "ecosystem survival":
        return "Favors heirs optimized for ecosystem stewardship."
    if phase == "civil-war readiness":
        return "Favors heirs optimized for branch-mirror conflict."
    return "Keeps both ecosystem and civil-war successor lanes active."
