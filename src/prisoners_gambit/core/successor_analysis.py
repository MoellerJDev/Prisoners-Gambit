from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prisoners_gambit.core.doctrines import BranchRole
from prisoners_gambit.core.identity_analysis import AgentIdentity, analyze_agent_identity
from prisoners_gambit.core.models import Agent

PressureLevel = Literal["low", "rising", "high"]
DoctrineRelation = Literal["continues", "moderates", "pivots"]


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
    succession_pitch: str
    succession_risk: str
    anti_score_note: str


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


def civil_war_pressure_for_threat_tags(threat_tags: set[str] | None) -> PressureLevel:
    tags = threat_tags or set()
    if not tags:
        return "low"

    weights = {
        "Aggressive": 2,
        "Exploitative": 2,
        "Punishing": 2,
        "Control": 2,
        "Tempo": 2,
        "Unstable": 2,
        "Referendum": 1,
        "Defensive": 1,
        "Cooperative": 1,
    }
    score = sum(weights.get(tag, 0) for tag in tags)
    if score >= 5:
        return "high"
    if score >= 2:
        return "rising"
    return "low"


def assess_successor_candidate(
    agent: Agent,
    *,
    top_score: int,
    threat_tags: set[str] | None = None,
    phase: str | None = None,
    lineage_doctrine: str | None = None,
) -> SuccessorAssessment:
    identity = analyze_agent_identity(agent)
    role = classify_branch_role(agent, identity, top_score=top_score)
    tags = set(identity.tags)
    threat_tags = threat_tags or set()
    doctrine_relation = _doctrine_relation(tags=tags, lineage_doctrine=lineage_doctrine)

    tradeoffs = _build_tradeoffs(agent=agent, tags=tags)
    strengths, liabilities = _build_strengths_and_liabilities(agent=agent, tags=tags)
    attractive_now = _current_fit_reason(tags=tags, threat_tags=threat_tags)
    danger_later = _future_risk_reason(role=role, tags=tags, phase=phase)
    lineage_future = _lineage_future_reason(
        tradeoffs=tradeoffs,
        phase=phase,
        lineage_doctrine=lineage_doctrine,
        doctrine_relation=doctrine_relation,
    )
    succession_pitch = _succession_pitch(tags=tags, phase=phase, threat_tags=threat_tags, doctrine_relation=doctrine_relation)
    succession_risk = _succession_risk(tags=tags, phase=phase, threat_tags=threat_tags)
    anti_score_note = _anti_score_note(
        agent=agent,
        tags=tags,
        top_score=top_score,
        phase=phase,
        threat_tags=threat_tags,
        doctrine_relation=doctrine_relation,
    )

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
        succession_pitch=succession_pitch,
        succession_risk=succession_risk,
        anti_score_note=anti_score_note,
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


def _doctrine_relation(*, tags: set[str], lineage_doctrine: str | None) -> DoctrineRelation:
    if not lineage_doctrine or "Lineage trend:" not in lineage_doctrine:
        return "moderates"

    doctrine_text = lineage_doctrine.lower()
    overlap = sum(1 for tag in tags if tag.lower() in doctrine_text)

    if overlap >= 2:
        return "continues"
    if overlap == 1:
        return "moderates"
    return "pivots"


def _current_fit_reason(*, tags: set[str], threat_tags: set[str]) -> str:
    if not threat_tags:
        return "No dominant threat lane, so this heir gives broad coverage."
    if "Aggressive" in threat_tags and ("Defensive" in tags or "Cooperative" in tags):
        return "Absorbs aggressive table pressure without immediate collapse."
    if "Referendum" in threat_tags and "Referendum" in tags:
        return "Contests referendum value before specialists snowball."
    if "Control" in threat_tags and "Control" in tags:
        return "Can answer directive-heavy opponents on equal footing."
    return "Offers workable matchup coverage against the current threat mix."


def _future_risk_reason(*, role: BranchRole, tags: set[str], phase: str | None) -> str:
    if role == "Future civil-war monster":
        return "Visible power spikes can draw concentrated anti-lineage focus."
    if role == "Unstable heir":
        return "Volatility can flip elimination-thin civil-war rounds against you."
    if phase == "civil_war" and ("Referendum" in tags):
        return "Referendum tools lose relative value once branch mirrors dominate."
    if role == "Safe heir":
        return "Stable pacing can lose race tempo to explosive cousins."
    return "Role specialization can become a liability if the phase pivots."


def _lineage_future_reason(
    *,
    tradeoffs: list[str],
    phase: str | None,
    lineage_doctrine: str | None,
    doctrine_relation: DoctrineRelation,
) -> str:
    phase_side = next((item for item in tradeoffs if item.startswith("Ecosystem vs civil war:")), "")

    relation_text = {
        "continues": "continues the current lineage doctrine",
        "moderates": "moderates the current doctrine",
        "pivots": "pivots sharply away from the current doctrine",
    }[doctrine_relation]

    if phase == "civil_war" or "Civil-war-ready" in phase_side:
        return f"{relation_text} and commits to branch-mirror endgame pressure."
    if lineage_doctrine and "Lineage trend:" in lineage_doctrine:
        return f"{relation_text} relative to '{lineage_doctrine}'."
    return f"{relation_text} while keeping the branch arc open."


def _succession_pitch(*, tags: set[str], phase: str | None, threat_tags: set[str], doctrine_relation: DoctrineRelation) -> str:
    if phase == "civil_war" and {"Punishing", "Control", "Aggressive"} & tags:
        return "Pick this heir to impose duel tempo in branch mirrors now."
    if doctrine_relation == "pivots":
        return "Pick this heir if you want a deliberate doctrine reset next floor."
    if "Referendum" in threat_tags and "Referendum" in tags:
        return "Pick this heir to secure referendum leverage while outsiders remain."
    return "Pick this heir for a balanced transition into the next pressure cycle."


def _succession_risk(*, tags: set[str], phase: str | None, threat_tags: set[str]) -> str:
    if "Unstable" in tags:
        return "Inherits swing-heavy variance, including self-inflicted elimination turns."
    if phase == "ecosystem" and {"Control", "Punishing"} & tags:
        return "Coercive lines can unite outsiders before civil war starts."
    if "Referendum" not in tags and "Referendum" in threat_tags:
        return "Low referendum resilience can leak value every ecosystem floor."
    return "Narrows your fallback plans if incoming threats change profile."


def _anti_score_note(
    *,
    agent: Agent,
    tags: set[str],
    top_score: int,
    phase: str | None,
    threat_tags: set[str],
    doctrine_relation: DoctrineRelation,
) -> str:
    trailing = top_score - agent.score

    if trailing > 0 and "Referendum" in tags and "Referendum" in threat_tags:
        return "Score trails, but referendum resilience can outperform raw duel totals next floor."
    if trailing > 0 and doctrine_relation in {"continues", "moderates"}:
        return "Score trails, but doctrine fit reduces transition risk for the current threat cycle."
    if trailing > 0 and phase == "civil_war" and {"Aggressive", "Control", "Punishing", "Tempo"} & tags:
        return "Score trails, but civil-war readiness is stronger than the current scoreboard suggests."
    if agent.score == top_score and phase == "ecosystem" and {"Aggressive", "Tempo"} & tags and "Defensive" not in tags:
        return "Top score is tempo-driven and may be fragile against retaliation-heavy tables."
    if agent.score == top_score and "Referendum" not in tags and "Referendum" in threat_tags:
        return "Top score hides referendum exposure; floor-value losses can erase that lead quickly."
    return "Score is a signal, but matchup coverage and doctrine trajectory should break ties."
