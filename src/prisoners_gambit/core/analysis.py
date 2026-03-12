from __future__ import annotations

"""Compatibility facade for analysis APIs.

This module preserves existing import paths while delegating to focused analysis modules:
- identity analysis
- floor heir-pressure analysis
- successor assessment analysis
"""

from prisoners_gambit.core.heir_pressure import FloorHeirPressure, HeirPressureCandidate, analyze_floor_heir_pressure
from prisoners_gambit.core.identity_analysis import AgentIdentity, analyze_agent_identity
from prisoners_gambit.core.successor_analysis import SuccessorAssessment, assess_successor_candidate, classify_branch_role, shaping_causes_for_agent

__all__ = [
    "AgentIdentity",
    "HeirPressureCandidate",
    "FloorHeirPressure",
    "SuccessorAssessment",
    "analyze_agent_identity",
    "analyze_floor_heir_pressure",
    "assess_successor_candidate",
    "classify_branch_role",
    "shaping_causes_for_agent",
]
