from __future__ import annotations

from dataclasses import dataclass, replace

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import DynastyResourcesState, FloorVoteResult
from prisoners_gambit.core.models import Agent

_MIN_RESOURCE = 0
_MAX_RESOURCE = 9


@dataclass(slots=True)
class DynastyState:
    legitimacy: int = 5
    cohesion: int = 5
    leverage: int = 3
    claimant_agent_id: int | None = None
    claimant_name: str | None = None
    claimant_depth: int | None = None
    contingencies: int = 0


def _clamp_resource(value: int) -> int:
    return max(_MIN_RESOURCE, min(_MAX_RESOURCE, int(value)))


def initial_dynasty_state() -> DynastyState:
    return DynastyState()


def to_view(state: DynastyState) -> DynastyResourcesState:
    return DynastyResourcesState(
        legitimacy=state.legitimacy,
        cohesion=state.cohesion,
        leverage=state.leverage,
        claimant_name=state.claimant_name,
        claimant_depth=state.claimant_depth,
        contingencies=state.contingencies,
    )


def adjust_dynasty_state(
    state: DynastyState,
    *,
    legitimacy_delta: int = 0,
    cohesion_delta: int = 0,
    leverage_delta: int = 0,
    contingencies_delta: int = 0,
) -> DynastyState:
    return replace(
        state,
        legitimacy=_clamp_resource(state.legitimacy + legitimacy_delta),
        cohesion=_clamp_resource(state.cohesion + cohesion_delta),
        leverage=_clamp_resource(state.leverage + leverage_delta),
        contingencies=max(0, state.contingencies + contingencies_delta),
    )


def set_claimant(
    state: DynastyState,
    *,
    agent: Agent,
    allow_contingency: bool = False,
) -> DynastyState:
    contingencies = state.contingencies
    if allow_contingency and contingencies == 0 and state.leverage >= 4 and state.cohesion >= 4:
        contingencies = 1
    return replace(
        state,
        claimant_agent_id=agent.agent_id,
        claimant_name=agent.name,
        claimant_depth=agent.lineage_depth,
        contingencies=contingencies,
    )


def clear_claimant(state: DynastyState) -> DynastyState:
    return replace(
        state,
        claimant_agent_id=None,
        claimant_name=None,
        claimant_depth=None,
        contingencies=0,
    )


def is_claimant_alive(state: DynastyState, survivors: list[Agent]) -> bool:
    if state.claimant_agent_id is None:
        return False
    return any(agent.agent_id == state.claimant_agent_id for agent in survivors)


def can_use_contingency(state: DynastyState) -> bool:
    return state.contingencies > 0 and state.leverage >= 2 and state.cohesion >= 2


def spend_contingency(state: DynastyState) -> DynastyState:
    updated = adjust_dynasty_state(
        state,
        leverage_delta=-2,
        cohesion_delta=-1,
        contingencies_delta=-1,
    )
    return replace(
        updated,
        claimant_agent_id=None,
        claimant_name=None,
        claimant_depth=None,
    )


def apply_host_transition_strain(state: DynastyState, *, voluntary: bool) -> DynastyState:
    if voluntary:
        return adjust_dynasty_state(state, legitimacy_delta=-1, cohesion_delta=-1)
    return adjust_dynasty_state(state, legitimacy_delta=-1, cohesion_delta=-2)


def update_after_floor(
    state: DynastyState,
    *,
    ranked: list[Agent],
    player: Agent,
    vote_result: FloorVoteResult | None,
    phase: str,
    host_changed: bool,
) -> DynastyState:
    next_state = state
    population_size = max(1, len(ranked))
    player_rank = next((index for index, agent in enumerate(ranked, start=1) if agent.agent_id == player.agent_id), population_size)

    if player_rank <= max(1, population_size // 3):
        next_state = adjust_dynasty_state(next_state, legitimacy_delta=1, leverage_delta=1)
    elif player_rank >= max(2, (population_size * 2) // 3):
        next_state = adjust_dynasty_state(next_state, legitimacy_delta=-1)

    if vote_result is not None:
        if vote_result.player_vote == COOPERATE and vote_result.cooperation_prevailed:
            next_state = adjust_dynasty_state(next_state, legitimacy_delta=1)
        elif vote_result.player_vote == DEFECT:
            next_state = adjust_dynasty_state(next_state, leverage_delta=1, legitimacy_delta=-1)

    if phase == "civil_war":
        if player_rank == 1:
            next_state = adjust_dynasty_state(next_state, cohesion_delta=1)
        else:
            next_state = adjust_dynasty_state(next_state, cohesion_delta=-1)

    if host_changed:
        next_state = apply_host_transition_strain(next_state, voluntary=False)

    return next_state
