from __future__ import annotations

from prisoners_gambit.core.models import Agent

PLAYER_LINEAGE_ID = 1


def detect_player_lineage_id(agents: list[Agent]) -> int | None:
    player = next((agent for agent in agents if agent.is_player and agent.lineage_id is not None), None)
    return player.lineage_id if player else None


def is_player_lineage(lineage_id: int | None, player_lineage_id: int | None) -> bool:
    return lineage_id is not None and player_lineage_id is not None and lineage_id == player_lineage_id
