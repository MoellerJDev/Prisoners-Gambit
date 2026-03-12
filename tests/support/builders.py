from __future__ import annotations

"""Small builders that keep tests focused on behavior instead of dataclass setup.

These helpers intentionally expose only a few knobs. If a test needs uncommon fields,
it can still construct objects directly; this layer is for common, readable defaults.
"""

import random

from prisoners_gambit.app.heir_view_mapping import to_floor_summary_heir_pressure_view, to_successor_candidate_view
from prisoners_gambit.core.analysis import analyze_agent_identity, analyze_floor_heir_pressure, assess_successor_candidate
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import FeaturedMatchPrompt, FloorSummaryEntryView, FloorSummaryState, SuccessorCandidateView
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import CounterIntel, OpeningGambit, TrustDividend
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


def build_featured_prompt(
    *,
    floor_number: int = 1,
    round_index: int = 0,
    total_rounds: int = 3,
    my_history: list[int] | None = None,
    opp_history: list[int] | None = None,
) -> FeaturedMatchPrompt:
    """Build a featured prompt with optional histories for richer round scenarios."""
    my_hist = list(my_history) if my_history is not None else []
    opp_hist = list(opp_history) if opp_history is not None else []
    return FeaturedMatchPrompt(
        floor_number=floor_number,
        masked_opponent_label="Unknown Opponent",
        round_index=round_index,
        total_rounds=total_rounds,
        my_history=my_hist,
        opp_history=opp_hist,
        my_match_score=0,
        opp_match_score=0,
        suggested_move=COOPERATE,
        roster_entries=[],
    )


def build_successor_candidates() -> list[Agent]:
    alpha = build_agent("Heir Alpha", lineage_id=1, lineage_depth=1, score=12, wins=3)
    alpha.powerups.append(TrustDividend())
    beta = build_agent("Heir Beta", lineage_id=1, lineage_depth=2, score=10, wins=2, genome=build_genome(table_bits="CDDD"))
    beta.powerups.append(OpeningGambit())
    return [alpha, beta]


def build_successor_choice_context(*, include_outsider_threat: bool = True) -> tuple[list[Agent], list[SuccessorCandidateView]]:
    """Return ranked agents and successor views to test phase-aware successor framing."""
    player = build_agent("You", is_player=True, lineage_id=1, score=11, wins=2)
    candidates = build_successor_candidates()
    ranked = [player, *candidates]
    if include_outsider_threat:
        threat = build_agent("Threat Node", lineage_id=9, score=13, wins=4, genome=build_genome(table_bits="DDDD", noise=0.05))
        threat.powerups.append(CounterIntel())
        ranked.insert(0, threat)

    top_score = max(agent.score for agent in ranked)
    views = []
    for agent in candidates:
        identity = analyze_agent_identity(agent)
        assessment = assess_successor_candidate(agent, top_score=top_score, phase="ecosystem")
        views.append(to_successor_candidate_view(agent=agent, identity=identity, assessment=assessment))
    return ranked, views


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


def build_seeded_session(*, seed: int = 7, rounds: int = 2):
    from prisoners_gambit.web.web_slice import FeaturedMatchWebSession

    session = FeaturedMatchWebSession(seed=seed, rounds=rounds)
    session.start()
    return session


def random_seed_set(*, base: int = 7, size: int = 4) -> list[int]:
    rng = random.Random(base)
    return [rng.randint(1, 10_000) for _ in range(size)]
