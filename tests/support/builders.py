from __future__ import annotations

"""Small builders that keep tests focused on behavior instead of dataclass setup.

These helpers intentionally expose only a few knobs. If a test needs uncommon fields,
it can still construct objects directly; this layer is for common, readable defaults.
"""

from prisoners_gambit.app.heir_view_mapping import to_floor_summary_heir_pressure_view
from prisoners_gambit.core.analysis import analyze_floor_heir_pressure
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import FeaturedMatchPrompt, FloorSummaryEntryView, FloorSummaryState
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.strategy import StrategyGenome

_STATES = (
    (COOPERATE, COOPERATE),
    (COOPERATE, DEFECT),
    (DEFECT, COOPERATE),
    (DEFECT, DEFECT),
)


def build_genome(*, first_move: int = COOPERATE, table_bits: str = "CCDD", noise: float = 0.0) -> StrategyGenome:
    """Create a deterministic strategy genome from compact bits.

    `table_bits` order is (CC, CD, DC, DD) and should contain only C/D.
    """
    bit_map = {"C": COOPERATE, "D": DEFECT}
    if len(table_bits) != 4 or any(bit not in bit_map for bit in table_bits):
        raise ValueError("table_bits must be four characters from {'C', 'D'}")
    return StrategyGenome(
        first_move=first_move,
        response_table={state: bit_map[bit] for state, bit in zip(_STATES, table_bits, strict=True)},
        noise=noise,
    )


def build_agent(
    name: str,
    *,
    is_player: bool = False,
    lineage_id: int | None = None,
    lineage_depth: int = 0,
    score: int = 0,
    wins: int = 0,
    genome: StrategyGenome | None = None,
) -> Agent:
    return Agent(
        name=name,
        genome=genome or build_genome(),
        is_player=is_player,
        lineage_id=(1 if is_player and lineage_id is None else lineage_id),
        lineage_depth=lineage_depth,
        score=score,
        wins=wins,
    )


def build_featured_prompt(*, floor_number: int = 1, round_index: int = 0, total_rounds: int = 3) -> FeaturedMatchPrompt:
    return FeaturedMatchPrompt(
        floor_number=floor_number,
        masked_opponent_label="Unknown Opponent",
        round_index=round_index,
        total_rounds=total_rounds,
        my_history=[],
        opp_history=[],
        my_match_score=0,
        opp_match_score=0,
        suggested_move=COOPERATE,
        roster_entries=[],
    )


def build_successor_candidates() -> list[Agent]:
    return [
        build_agent("Heir Alpha", lineage_id=1, lineage_depth=1, score=12, wins=3),
        build_agent("Heir Beta", lineage_id=1, lineage_depth=2, score=10, wins=2, genome=build_genome(table_bits="CDDD")),
    ]


def build_floor_summary_state(*, floor_number: int = 1, ranked: list[Agent], player_lineage_id: int | None = 1) -> FloorSummaryState:
    entries = [
        FloorSummaryEntryView(
            agent_id=agent.agent_id,
            name=agent.name,
            is_player=agent.is_player,
            score=agent.score,
            wins=agent.wins,
            tags=[],
            descriptor=agent.public_profile,
            genome_summary=agent.genome.summary(),
            powerups=[powerup.name for powerup in agent.powerups],
        )
        for agent in ranked
    ]
    pressure = analyze_floor_heir_pressure(ranked, player_lineage_id=player_lineage_id)
    return FloorSummaryState(
        floor_number=floor_number,
        entries=entries,
        heir_pressure=to_floor_summary_heir_pressure_view(pressure),
    )
