from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prisoners_gambit.content.strategic_text import (
    doctrine_relation_text,
    successor_anti_score_text,
    successor_current_fit_text,
    successor_future_risk_text,
    successor_lineage_future_text,
    successor_liability_text,
    successor_shaping_cause,
    successor_succession_pitch_text,
    successor_succession_risk_text,
    successor_strength_text,
    successor_tradeoff_text,
)
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
        causes.append(successor_shaping_cause("cooperative"))
    if "Aggressive" in identity.tags:
        causes.append(successor_shaping_cause("aggressive"))
    if "Referendum" in identity.tags:
        causes.append(successor_shaping_cause("referendum"))
    if "Control" in identity.tags:
        causes.append(successor_shaping_cause("control"))
    if "Unstable" in identity.tags or agent.genome.noise >= 0.20:
        causes.append(successor_shaping_cause("unstable"))
    if not causes:
        causes.append(successor_shaping_cause("default"))
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
        tags=tags,
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
        successor_tradeoff_text("safety", safe_side),
        successor_tradeoff_text("phase", phase_side),
        successor_tradeoff_text("stability", stability_side),
        successor_tradeoff_text("control", control_side),
        successor_tradeoff_text("referendum", referendum_side),
    ]


def _build_strengths_and_liabilities(*, agent: Agent, tags: set[str]) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    if "Cooperative" in tags or "Consensus" in tags:
        strengths.append(successor_strength_text("coalition"))
    if {"Aggressive", "Exploitative", "Tempo"} & tags:
        strengths.append(successor_strength_text("tempo"))
    if "Referendum" in tags:
        strengths.append(successor_strength_text("referendum"))
    if "Control" in tags:
        strengths.append(successor_strength_text("control"))
    if not strengths:
        strengths.append(successor_strength_text("default"))

    liabilities: list[str] = []
    if "Unstable" in tags or agent.genome.noise >= 0.20:
        liabilities.append(successor_liability_text("volatility"))
    if "Aggressive" in tags and "Defensive" not in tags:
        liabilities.append(successor_liability_text("retaliation"))
    if "Referendum" not in tags:
        liabilities.append(successor_liability_text("referendum"))
    if "Cooperative" in tags and "Retaliatory" not in tags:
        liabilities.append(successor_liability_text("exploitation"))
    if not liabilities:
        liabilities.append(successor_liability_text("default"))

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
        if {"Aggressive", "Exploitative", "Tempo"} & tags:
            return successor_current_fit_text("no_threat_tempo")
        if "Referendum" in tags:
            return successor_current_fit_text("no_threat_referendum")
        if {"Cooperative", "Defensive"} & tags:
            return successor_current_fit_text("no_threat_stability")
        return successor_current_fit_text("no_threat_flexible")
    if "Aggressive" in threat_tags and ("Defensive" in tags or "Cooperative" in tags):
        return successor_current_fit_text("vs_aggressive_absorb")
    if "Aggressive" in threat_tags and ({"Control", "Punishing"} & tags):
        return successor_current_fit_text("vs_aggressive_discipline")
    if "Referendum" in threat_tags and "Referendum" in tags:
        return successor_current_fit_text("vs_referendum_contest")
    if "Control" in threat_tags and "Control" in tags:
        return successor_current_fit_text("vs_control_answer")
    if "Cooperative" in threat_tags and {"Aggressive", "Exploitative"} & tags:
        return successor_current_fit_text("vs_cooperative_punish")
    if "Unstable" in threat_tags and {"Precise", "Defensive"} & tags:
        return successor_current_fit_text("vs_unstable_contain")
    if {"Aggressive", "Exploitative", "Tempo"} & tags:
        return successor_current_fit_text("default_tempo")
    if "Referendum" in tags:
        return successor_current_fit_text("default_referendum")
    return successor_current_fit_text("default_flexible")


def _future_risk_reason(*, role: BranchRole, tags: set[str], phase: str | None) -> str:
    if role == "Future civil-war monster":
        return successor_future_risk_text("civil_war_monster")
    if role == "Unstable heir":
        return successor_future_risk_text("unstable")
    if phase == "civil_war" and ("Referendum" in tags):
        return successor_future_risk_text("referendum_in_civil_war")
    if {"Control", "Punishing"} & tags and phase == "ecosystem":
        return successor_future_risk_text("hardline_in_ecosystem")
    if "Cooperative" in tags and "Retaliatory" not in tags:
        return successor_future_risk_text("pure_trust")
    if role == "Safe heir":
        return successor_future_risk_text("safe_heir")
    return successor_future_risk_text("default")


def _lineage_future_reason(
    *,
    tradeoffs: list[str],
    tags: set[str],
    phase: str | None,
    lineage_doctrine: str | None,
    doctrine_relation: DoctrineRelation,
) -> str:
    phase_side = next((item for item in tradeoffs if item.startswith("Ecosystem vs civil war:")), "")

    relation_text = doctrine_relation_text(doctrine_relation)

    if phase == "civil_war" or "Civil-war-ready" in phase_side:
        if {"Control", "Punishing", "Aggressive"} & tags:
            return successor_lineage_future_text("civil_war_force", relation_text=relation_text)
        return successor_lineage_future_text("civil_war_survival", relation_text=relation_text)
    if "Referendum" in tags:
        return successor_lineage_future_text("referendum", relation_text=relation_text)
    if {"Cooperative", "Consensus", "Forgiving"} & tags:
        return successor_lineage_future_text("legitimacy", relation_text=relation_text)
    if {"Aggressive", "Exploitative", "Tempo"} & tags:
        return successor_lineage_future_text("tempo", relation_text=relation_text)
    if "Unstable" in tags:
        return successor_lineage_future_text("unstable", relation_text=relation_text)
    if lineage_doctrine and "Lineage trend:" in lineage_doctrine:
        return successor_lineage_future_text("quoted_lineage", relation_text=relation_text, lineage_doctrine=lineage_doctrine)
    return successor_lineage_future_text("default", relation_text=relation_text)


def _succession_pitch(*, tags: set[str], phase: str | None, threat_tags: set[str], doctrine_relation: DoctrineRelation) -> str:
    if phase == "civil_war" and {"Punishing", "Control", "Aggressive"} & tags:
        return successor_succession_pitch_text("civil_war_force")
    if doctrine_relation == "pivots":
        return successor_succession_pitch_text("pivot")
    if "Referendum" in threat_tags and "Referendum" in tags:
        return successor_succession_pitch_text("referendum_contest")
    if {"Cooperative", "Retaliatory"} <= tags:
        return successor_succession_pitch_text("reciprocal")
    if {"Aggressive", "Exploitative"} <= tags:
        return successor_succession_pitch_text("knife_first")
    if {"Control", "Punishing"} & tags:
        return successor_succession_pitch_text("discipline")
    if "Referendum" in tags:
        return successor_succession_pitch_text("referendum")
    return successor_succession_pitch_text("default")


def _succession_risk(*, tags: set[str], phase: str | None, threat_tags: set[str]) -> str:
    if "Unstable" in tags:
        return successor_succession_risk_text("unstable")
    if phase == "ecosystem" and {"Control", "Punishing"} & tags:
        return successor_succession_risk_text("hardline_in_ecosystem")
    if "Referendum" not in tags and "Referendum" in threat_tags:
        return successor_succession_risk_text("weak_referendum")
    if {"Aggressive", "Exploitative"} & tags and "Defensive" not in tags:
        return successor_succession_risk_text("thin_recovery")
    if {"Cooperative", "Consensus"} & tags and "Retaliatory" not in tags:
        return successor_succession_risk_text("peace_without_punish")
    return successor_succession_risk_text("default")


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
        return successor_anti_score_text("referendum_trail")
    if trailing > 0 and doctrine_relation in {"continues", "moderates"}:
        return successor_anti_score_text("fit_trail")
    if trailing > 0 and phase == "civil_war" and {"Aggressive", "Control", "Punishing", "Tempo"} & tags:
        return successor_anti_score_text("war_ready_trail")
    if agent.score == top_score and phase == "ecosystem" and {"Aggressive", "Tempo"} & tags and "Defensive" not in tags:
        return successor_anti_score_text("tempo_lead_brittle")
    if agent.score == top_score and "Referendum" not in tags and "Referendum" in threat_tags:
        return successor_anti_score_text("referendum_lead_exposed")
    return successor_anti_score_text("default")
