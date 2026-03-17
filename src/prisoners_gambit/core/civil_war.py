from __future__ import annotations

from prisoners_gambit.core.analysis import analyze_agent_identity
from prisoners_gambit.core.featured_inference import (
    FeaturedInferenceSignals,
    civil_war_featured_inference_context,
)
from prisoners_gambit.core.interaction import CivilWarContext
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.successor_analysis import classify_branch_role


def build_civil_war_context(
    *,
    branches: list[Agent],
    current_host: Agent | None,
    featured_inference_signals: FeaturedInferenceSignals | None = None,
) -> CivilWarContext:
    role_counts: dict[str, int] = {}
    doctrine_lane_counts = {"control": 0, "referendum": 0, "tempo": 0, "unstable": 0}

    top_score = max((branch.score for branch in branches), default=1)

    for branch in branches:
        identity = analyze_agent_identity(branch)
        role = classify_branch_role(branch, identity, top_score=top_score)
        role_counts[role] = role_counts.get(role, 0) + 1
        tags = set(identity.tags)
        if {"Control", "Punishing"} & tags:
            doctrine_lane_counts["control"] += 1
        if "Referendum" in tags:
            doctrine_lane_counts["referendum"] += 1
        if "Tempo" in tags or "Aggressive" in tags:
            doctrine_lane_counts["tempo"] += 1
        if "Unstable" in tags:
            doctrine_lane_counts["unstable"] += 1

    dangerous = sorted(role_counts.items(), key=lambda item: item[1], reverse=True)
    dangerous_branches = [f"{role}: {count} branch(es)" for role, count in dangerous[:3]]

    doctrine_pressure: list[str] = []
    if doctrine_lane_counts["referendum"]:
        doctrine_pressure.append("Referendum perks lose value; no floor vote in civil war.")
    if doctrine_lane_counts["control"]:
        doctrine_pressure.append("Control/Punishing lines gain extra value by breaking cooperative cousins.")
    if doctrine_lane_counts["tempo"]:
        doctrine_pressure.append("Aggressive/Tempo mirrors are high-variance: same-lane duel wins gain rivalry score.")
    if doctrine_lane_counts["unstable"]:
        doctrine_pressure.append("Unstable branches can steal rounds but are brittle under mirror pressure.")

    host_name = current_host.name if current_host is not None else "your current host"
    featured_framing = civil_war_featured_inference_context(featured_inference_signals or FeaturedInferenceSignals((), ()))
    thesis = (
        f"Judgment phase: outsiders are gone. Current host {host_name} now faces sibling branches shaped by your own lineage doctrine."
    )

    return CivilWarContext(
        thesis=thesis,
        scoring_rules=[
            "Referendum is disabled; only duel performance decides survival.",
            "Mirror-lane rivalry: beating a branch with overlapping doctrine tags grants +1 score.",
            "Doctrine clash: Control/Punishing winners over Cooperative/Referendum branches gain +1 score.",
            "Monster check: defeating a Future civil-war monster branch grants +1 score.",
        ],
        dangerous_branches=dangerous_branches,
        doctrine_pressure=[*doctrine_pressure[:2], *featured_framing][:4],
    )
