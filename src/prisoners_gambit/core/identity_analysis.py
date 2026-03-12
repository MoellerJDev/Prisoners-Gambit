from __future__ import annotations

from dataclasses import dataclass

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
    descriptor = _build_descriptor(tags)
    return AgentIdentity(tags=tags, descriptor=descriptor)


def _build_descriptor(tags: list[str]) -> str:
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
