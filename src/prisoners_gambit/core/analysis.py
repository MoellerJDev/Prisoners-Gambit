from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent


@dataclass(slots=True)
class AgentIdentity:
    tags: list[str]
    descriptor: str


def analyze_agent_identity(agent: Agent) -> AgentIdentity:
    tags: list[str] = []

    genome = agent.genome
    perks = agent.powerups
    perk_names = {powerup.name for powerup in perks}

    if genome.first_move == COOPERATE:
        tags.append("Cooperative")
    else:
        tags.append("Aggressive")

    if genome.response_table[(COOPERATE, DEFECT)] == DEFECT:
        tags.append("Retaliatory")

    if genome.response_table[(DEFECT, COOPERATE)] == DEFECT:
        tags.append("Exploitative")

    if genome.response_table[(DEFECT, DEFECT)] == COOPERATE:
        tags.append("Forgiving")

    if genome.noise >= 0.18:
        tags.append("Unstable")
    elif genome.noise <= 0.03:
        tags.append("Precise")

    if {"Golden Handshake", "Coercive Control", "Counter-Intel", "Panic Button"} & perk_names:
        tags.append("Control")

    if {"Unity Ticket", "Saboteur Bloc", "Bloc Politics"} & perk_names:
        tags.append("Referendum")

    if {"Last Laugh", "Opening Gambit"} & perk_names:
        tags.append("Tempo")

    if {"Trust Dividend"} & perk_names:
        tags.append("Consensus")

    if {"Mercy Shield"} & perk_names:
        tags.append("Defensive")

    if {"Spite Engine", "Compliance Dividend"} & perk_names:
        tags.append("Punishing")

    tags = _dedupe_preserve_order(tags)[:4]

    descriptor = _build_descriptor(tags, agent)

    return AgentIdentity(tags=tags, descriptor=descriptor)


@dataclass(slots=True)
class HeirPressureCandidate:
    name: str
    branch_role: str
    score: int
    wins: int
    tags: list[str]
    descriptor: str
    rationale: str


@dataclass(slots=True)
class FloorHeirPressure:
    branch_doctrine: str
    successor_candidates: list[HeirPressureCandidate]
    future_threats: list[HeirPressureCandidate]


@dataclass(slots=True)
class SuccessorAssessment:
    branch_role: str
    branch_doctrine: str
    tradeoffs: list[str]
    strengths: list[str]
    liabilities: list[str]
    attractive_now: str
    danger_later: str
    lineage_future: str


def analyze_floor_heir_pressure(ranked: list[Agent], player_lineage_id: int | None) -> FloorHeirPressure:
    if not ranked:
        return FloorHeirPressure(
            branch_doctrine="No floor data yet.",
            successor_candidates=[],
            future_threats=[],
        )

    lineage_agents = [a for a in ranked if a.lineage_id == player_lineage_id] if player_lineage_id is not None else []
    tag_counts: Counter[str] = Counter()
    for agent in lineage_agents:
        tag_counts.update(analyze_agent_identity(agent).tags)

    if lineage_agents:
        top_tags = [tag for tag, _ in tag_counts.most_common(3)]
        doctrine = f"Lineage trend: {', '.join(top_tags) if top_tags else 'Mixed'} across {len(lineage_agents)} active branch(es)."
    else:
        doctrine = "Lineage trend unavailable: no active branch survived this floor summary."

    successors: list[HeirPressureCandidate] = []
    for agent in ranked:
        if agent.lineage_id != player_lineage_id or agent.is_player:
            continue
        identity = analyze_agent_identity(agent)
        successors.append(
            HeirPressureCandidate(
                name=agent.name,
                branch_role=_classify_branch_role(agent, identity, top_score=ranked[0].score),
                score=agent.score,
                wins=agent.wins,
                tags=identity.tags,
                descriptor=identity.descriptor,
                rationale="Viable successor branch if current host dies next floor.",
            )
        )
    successors = successors[:3]

    threats: list[HeirPressureCandidate] = []
    for agent in ranked:
        if agent.lineage_id == player_lineage_id:
            continue
        identity = analyze_agent_identity(agent)
        threats.append(
            HeirPressureCandidate(
                name=agent.name,
                branch_role=_classify_branch_role(agent, identity, top_score=ranked[0].score),
                score=agent.score,
                wins=agent.wins,
                tags=identity.tags,
                descriptor=identity.descriptor,
                rationale="External pressure likely to shape upcoming heir choices.",
            )
        )
    threats = threats[:3]

    return FloorHeirPressure(
        branch_doctrine=doctrine,
        successor_candidates=successors,
        future_threats=threats,
    )


def _classify_branch_role(agent: Agent, identity: AgentIdentity, top_score: int) -> str:
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


def assess_successor_candidate(
    agent: Agent,
    *,
    top_score: int,
    threat_tags: set[str] | None = None,
    phase: str | None = None,
) -> SuccessorAssessment:
    identity = analyze_agent_identity(agent)
    tags = set(identity.tags)
    threat_tags = threat_tags or set()

    role = _classify_branch_role(agent, identity, top_score=top_score)
    doctrine = identity.descriptor

    safe_side = "Safe edge" if ("Cooperative" in tags or "Defensive" in tags) and "Unstable" not in tags else "Explosive edge"
    phase_side = "Civil-war-ready" if ({"Aggressive", "Exploitative", "Control", "Punishing", "Tempo"} & tags) else "Ecosystem-ready"
    stability_side = "Volatile" if "Unstable" in tags or agent.genome.noise >= 0.20 else "Stable"
    control_side = "Coercive" if ({"Control", "Punishing"} & tags) else "Trust-based"
    referendum_side = "Referendum value" if "Referendum" in tags else "Duel value"

    tradeoffs = [
        f"Safe vs explosive: {safe_side}",
        f"Ecosystem vs civil war: {phase_side}",
        f"Stable vs volatile: {stability_side}",
        f"Trust vs coercion: {control_side}",
        f"Referendum vs duel: {referendum_side}",
    ]

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

    attractive_now = "Strong immediate fit against current table pressure."
    if "Aggressive" in threat_tags and "Defensive" in tags:
        attractive_now = "Attractive now: defensive profile counters aggressive external pressure."
    elif "Referendum" in threat_tags and "Referendum" in tags:
        attractive_now = "Attractive now: can contest referendum specialists immediately."
    elif "Control" in threat_tags and "Control" in tags:
        attractive_now = "Attractive now: can answer control lines with control of its own."

    danger_later = "Danger later: this branch may over-specialize before civil war."
    if role == "Future civil-war monster":
        danger_later = "Danger later: power spikes may provoke anti-you focus once outsiders collapse."
    elif role == "Unstable heir":
        danger_later = "Danger later: volatility can backfire in elimination-thin civil-war rounds."
    elif role == "Safe heir":
        danger_later = "Danger later: safer pacing can lose races to explosive cousins in civil war."

    lineage_future = "Implies a balanced lineage future."
    if phase == "civil_war" or phase_side == "Civil-war-ready":
        lineage_future = "Implies a succession path built to dominate branch mirrors late."
    elif referendum_side == "Referendum value":
        lineage_future = "Implies a lineage future that farms macro floor incentives over pure duels."
    elif safe_side == "Safe edge":
        lineage_future = "Implies a slower, survivable lineage arc with fewer catastrophic swings."
    else:
        lineage_future = "Implies a high-risk lineage arc that can end runs quickly either way."

    return SuccessorAssessment(
        branch_role=role,
        branch_doctrine=doctrine,
        tradeoffs=tradeoffs,
        strengths=strengths[:3],
        liabilities=liabilities[:3],
        attractive_now=attractive_now,
        danger_later=danger_later,
        lineage_future=lineage_future,
    )


def _build_descriptor(tags: list[str], agent: Agent) -> str:
    parts: list[str] = []

    if "Cooperative" in tags and "Retaliatory" in tags:
        parts.append("Reciprocal cooperator")
    elif "Aggressive" in tags and "Exploitative" in tags:
        parts.append("Predatory opener")
    elif "Cooperative" in tags:
        parts.append("Trust-leaning strategist")
    elif "Aggressive" in tags:
        parts.append("Pressure-oriented strategist")
    else:
        parts.append("Adaptive strategist")

    if "Control" in tags:
        parts.append("with move control")
    elif "Referendum" in tags:
        parts.append("with group-vote pressure")
    elif "Consensus" in tags:
        parts.append("with cooperation incentives")
    elif "Punishing" in tags:
        parts.append("with harsh punishments")
    elif "Defensive" in tags:
        parts.append("with defensive tools")

    if "Unstable" in tags:
        parts.append("and volatile behavior")
    elif "Tempo" in tags:
        parts.append("and timing spikes")
    elif "Precise" in tags:
        parts.append("and low-noise execution")

    return " ".join(parts)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)

    return result
