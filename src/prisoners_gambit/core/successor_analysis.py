from __future__ import annotations

from dataclasses import dataclass

from prisoners_gambit.core.doctrines import BranchRole
from prisoners_gambit.core.identity_analysis import AgentIdentity, analyze_agent_identity
from prisoners_gambit.core.models import Agent


@dataclass(slots=True)
class SuccessorAssessment:
    branch_role: BranchRole
    branch_doctrine: str
    shaping_causes: list[str]
    tradeoffs: list[str]
    strengths: list[str]
    liabilities: list[str]
    attractive_now: str
    danger_later: str
    lineage_future: str


def classify_branch_role(agent: Agent, identity: AgentIdentity, top_score: int) -> BranchRole:
    tags = set(identity.tags)
    if agent.score >= max(1, top_score - 1) and ({"Control", "Punishing"} & tags or "Tempo" in tags):
        return "Future civil-war monster"
    if "Referendum" in tags:
        return "Referendum heir"
    if "Unstable" in tags or agent.genome.noise >= 0.20:
        return "Unstable heir"
    if "Aggressive" in tags and ("Exploitative" in tags or "Tempo" in tags):
        return "Ruthless heir"
    return "Safe heir"


def shaping_causes_for_agent(agent: Agent, identity: AgentIdentity) -> list[str]:
    causes: list[str] = []
    if "Cooperative" in identity.tags:
        causes.append("Cooperative opener and reciprocity bias")
    if "Aggressive" in identity.tags:
        causes.append("Aggressive opener with duel pressure")
    if "Referendum" in identity.tags:
        causes.append("Referendum-oriented perk package")
    if "Control" in identity.tags:
        causes.append("Control directives shaping move outcomes")
    if "Unstable" in identity.tags or agent.genome.noise >= 0.20:
        causes.append("High-noise behavior increases variance")
    if not causes:
        causes.append("Mixed profile from prior edits and inheritance")
    return causes[:3]


def assess_successor_candidate(
    agent: Agent,
    *,
    top_score: int,
    threat_tags: set[str] | None = None,
    phase: str | None = None,
) -> SuccessorAssessment:
    identity = analyze_agent_identity(agent)
    role = classify_branch_role(agent, identity, top_score=top_score)
    tags = set(identity.tags)
    threat_tags = threat_tags or set()

    tradeoffs = _build_tradeoffs(agent=agent, tags=tags)
    strengths, liabilities = _build_strengths_and_liabilities(agent=agent, tags=tags)
    attractive_now = _current_fit_reason(tags=tags, threat_tags=threat_tags)
    danger_later = _future_risk_reason(role)
    lineage_future = _lineage_future_reason(tradeoffs=tradeoffs, phase=phase)

    return SuccessorAssessment(
        branch_role=role,
        branch_doctrine=identity.descriptor,
        shaping_causes=shaping_causes_for_agent(agent, identity),
        tradeoffs=tradeoffs,
        strengths=strengths,
        liabilities=liabilities,
        attractive_now=attractive_now,
        danger_later=danger_later,
        lineage_future=lineage_future,
    )


def _build_tradeoffs(*, agent: Agent, tags: set[str]) -> list[str]:
    safe_side = "Safe edge" if ("Cooperative" in tags or "Defensive" in tags) and "Unstable" not in tags else "Explosive edge"
    phase_side = "Civil-war-ready" if ({"Aggressive", "Exploitative", "Control", "Punishing", "Tempo"} & tags) else "Ecosystem-ready"
    stability_side = "Volatile" if "Unstable" in tags or agent.genome.noise >= 0.20 else "Stable"
    control_side = "Coercive" if ({"Control", "Punishing"} & tags) else "Trust-based"
    referendum_side = "Referendum value" if "Referendum" in tags else "Duel value"
    return [
        f"Safe vs explosive: {safe_side}",
        f"Ecosystem vs civil war: {phase_side}",
        f"Stable vs volatile: {stability_side}",
        f"Trust vs coercion: {control_side}",
        f"Referendum vs duel: {referendum_side}",
    ]


def _build_strengths_and_liabilities(*, agent: Agent, tags: set[str]) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    if "Cooperative" in tags or "Consensus" in tags:
        strengths.append("Can stabilize alliances and referendum pacing")
    if {"Aggressive", "Exploitative", "Tempo"} & tags:
        strengths.append("Punishes passivity and can swing duels quickly")
    if "Referendum" in tags:
        strengths.append("Can convert floor vote dynamics into value")
    if "Control" in tags:
        strengths.append("Applies directive pressure that scales in branch mirrors")
    if not strengths:
        strengths.append("Balanced profile with flexible adaptation")

    liabilities: list[str] = []
    if "Unstable" in tags or agent.genome.noise >= 0.20:
        liabilities.append("Volatility can throw critical successor turns")
    if "Aggressive" in tags and "Defensive" not in tags:
        liabilities.append("Can trigger retaliation spirals in long rounds")
    if "Referendum" not in tags:
        liabilities.append("May underperform in referendum-heavy floors")
    if "Cooperative" in tags and "Retaliatory" not in tags:
        liabilities.append("May get farmed by exploiters before adapting")
    if not liabilities:
        liabilities.append("No obvious hard weakness, but ceiling may be lower")

    return strengths[:3], liabilities[:3]


def _current_fit_reason(*, tags: set[str], threat_tags: set[str]) -> str:
    if "Aggressive" in threat_tags and "Defensive" in tags:
        return "Attractive now: defensive profile counters aggressive external pressure."
    if "Referendum" in threat_tags and "Referendum" in tags:
        return "Attractive now: can contest referendum specialists immediately."
    if "Control" in threat_tags and "Control" in tags:
        return "Attractive now: can answer control lines with control of its own."
    return "Strong immediate fit against current table pressure."


def _future_risk_reason(role: BranchRole) -> str:
    if role == "Future civil-war monster":
        return "Danger later: power spikes may provoke anti-you focus once outsiders collapse."
    if role == "Unstable heir":
        return "Danger later: volatility can backfire in elimination-thin civil-war rounds."
    if role == "Safe heir":
        return "Danger later: safer pacing can lose races to explosive cousins in civil war."
    return "Danger later: this branch may over-specialize before civil war."


def _lineage_future_reason(*, tradeoffs: list[str], phase: str | None) -> str:
    phase_side = next((item for item in tradeoffs if item.startswith("Ecosystem vs civil war:")), "")
    referendum_side = next((item for item in tradeoffs if item.startswith("Referendum vs duel:")), "")
    safe_side = next((item for item in tradeoffs if item.startswith("Safe vs explosive:")), "")

    if phase == "civil_war" or "Civil-war-ready" in phase_side:
        return "Implies a succession path built to dominate branch mirrors late."
    if "Referendum value" in referendum_side:
        return "Implies a lineage future that farms macro floor incentives over pure duels."
    if "Safe edge" in safe_side:
        return "Implies a slower, survivable lineage arc with fewer catastrophic swings."
    return "Implies a high-risk lineage arc that can end runs quickly either way."
