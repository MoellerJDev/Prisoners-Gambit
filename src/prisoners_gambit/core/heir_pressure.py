from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from prisoners_gambit.core.doctrines import BranchRole
from prisoners_gambit.core.identity_analysis import analyze_agent_identity
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.successor_analysis import classify_branch_role, shaping_causes_for_agent


@dataclass(slots=True)
class HeirPressureCandidate:
    name: str
    branch_role: BranchRole
    score: int
    wins: int
    tags: list[str]
    descriptor: str
    shaping_causes: list[str]
    rationale: str


@dataclass(slots=True)
class FloorHeirPressure:
    branch_doctrine: str
    successor_candidates: list[HeirPressureCandidate]
    future_threats: list[HeirPressureCandidate]


def analyze_floor_heir_pressure(ranked: list[Agent], player_lineage_id: int | None) -> FloorHeirPressure:
    if not ranked:
        return FloorHeirPressure(
            branch_doctrine="No floor data yet.",
            successor_candidates=[],
            future_threats=[],
        )

    doctrine = _lineage_doctrine_text(ranked, player_lineage_id)
    top_score = ranked[0].score

    successors = [
        _pressure_candidate(agent, top_score=top_score, rationale="Viable successor branch if current host dies next floor.")
        for agent in ranked
        if agent.lineage_id == player_lineage_id and not agent.is_player
    ][:3]

    threats = [
        _pressure_candidate(agent, top_score=top_score, rationale="External pressure likely to shape upcoming heir choices.")
        for agent in ranked
        if agent.lineage_id != player_lineage_id
    ][:3]

    return FloorHeirPressure(
        branch_doctrine=doctrine,
        successor_candidates=successors,
        future_threats=threats,
    )


def _lineage_doctrine_text(ranked: list[Agent], player_lineage_id: int | None) -> str:
    lineage_agents = [a for a in ranked if a.lineage_id == player_lineage_id] if player_lineage_id is not None else []
    tag_counts: Counter[str] = Counter()
    for agent in lineage_agents:
        tag_counts.update(analyze_agent_identity(agent).tags)

    if not lineage_agents:
        return "Lineage trend unavailable: no active branch survived this floor summary."

    top_tags = [tag for tag, _ in tag_counts.most_common(3)]
    return f"Lineage trend: {', '.join(top_tags) if top_tags else 'Mixed'} across {len(lineage_agents)} active branch(es)."


def _pressure_candidate(agent: Agent, *, top_score: int, rationale: str) -> HeirPressureCandidate:
    identity = analyze_agent_identity(agent)
    return HeirPressureCandidate(
        name=agent.name,
        branch_role=classify_branch_role(agent, identity, top_score=top_score),
        score=agent.score,
        wins=agent.wins,
        tags=identity.tags,
        descriptor=identity.descriptor,
        shaping_causes=shaping_causes_for_agent(agent, identity),
        rationale=rationale,
    )
