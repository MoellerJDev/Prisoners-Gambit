import copy
import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    FloorVoteDecisionState,
    FloorVotePrompt,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import BlocPolitics, SaboteurBloc, UnityTicket
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.progression import FloorConfig
from prisoners_gambit.systems.tournament import TournamentEngine
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession


class StubInteractionController:
    def __init__(self, vote: int) -> None:
        self.vote = vote
        self.floor_vote_result = None

    def choose_floor_vote(self, state: FloorVoteDecisionState) -> int:
        return self.vote

    def set_floor_vote_result(self, result) -> None:
        self.floor_vote_result = result



def _static_agent(name: str, move: int, *, is_player: bool = False) -> Agent:
    genome = StrategyGenome(
        first_move=move,
        response_table={
            (COOPERATE, COOPERATE): move,
            (COOPERATE, DEFECT): move,
            (DEFECT, COOPERATE): move,
            (DEFECT, DEFECT): move,
        },
        noise=0.0,
    )
    return Agent(name=name, genome=genome, is_player=is_player, lineage_id=1 if is_player else 2)



def _run_core(population: list[Agent], *, player_vote: int, floor_number: int = 1) -> dict:
    floor_config = FloorConfig(
        floor_number=floor_number,
        rounds_per_match=1,
        ai_powerup_chance=0.0,
        featured_matches=1,
        referendum_reward=3,
        label=f"Floor {floor_number}",
    )
    controller = StubInteractionController(player_vote)
    engine = TournamentEngine(base_rounds_per_match=1, rng=random.Random(1), interaction_controller=controller)
    before_scores = {agent.name: agent.score for agent in population}

    engine._run_floor_referendum(population, floor_number, floor_config)

    assert controller.floor_vote_result is not None
    return {
        "result": controller.floor_vote_result,
        "scores": {agent.name: agent.score for agent in population},
        "score_delta": {agent.name: agent.score - before_scores[agent.name] for agent in population},
    }



def _run_web(population: list[Agent], *, player_vote: int, floor_number: int = 1) -> dict:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    player = next(agent for agent in population if agent.is_player)
    session.player = player
    session.floor_number = floor_number
    session.player_score = player.score
    session._branch_roster = population
    session._advance_branch_roster_for_floor = lambda: None

    decision = FloorVoteDecisionState(
        prompt=FloorVotePrompt(
            floor_number=floor_number,
            floor_label=f"Floor {floor_number}",
            suggested_vote=COOPERATE,
            current_floor_score=player.score,
            powerups=[powerup.name for powerup in player.powerups],
        )
    )
    session.session.begin_decision(decision, (ChooseFloorVoteAction,), session.snapshot)
    session.session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=player_vote))

    before_scores = {agent.name: agent.score for agent in population}
    session._resolve_floor_vote(decision)

    assert session.snapshot.floor_vote_result is not None
    return {
        "result": session.snapshot.floor_vote_result,
        "scores": {agent.name: agent.score for agent in population},
        "score_delta": {agent.name: agent.score - before_scores[agent.name] for agent in population},
    }



def _run_parity(population: list[Agent], *, player_vote: int, floor_number: int = 1) -> tuple[dict, dict]:
    core_population = copy.deepcopy(population)
    web_population = copy.deepcopy(population)
    return (
        _run_core(core_population, player_vote=player_vote, floor_number=floor_number),
        _run_web(web_population, player_vote=player_vote, floor_number=floor_number),
    )



def test_tie_handling_and_vote_tallies_match_between_core_and_web() -> None:
    population = [
        _static_agent("You", COOPERATE, is_player=True),
        _static_agent("Rival A", COOPERATE),
        _static_agent("Rival B", DEFECT),
        _static_agent("Rival C", DEFECT),
    ]

    core, web = _run_parity(population, player_vote=COOPERATE)

    assert core["result"].cooperators == web["result"].cooperators == 2
    assert core["result"].defectors == web["result"].defectors == 2
    assert core["result"].cooperation_prevailed is True
    assert web["result"].cooperation_prevailed is True



def test_player_sabotage_combo_reward_is_gated_the_same_as_core() -> None:
    player = _static_agent("You", COOPERATE, is_player=True)
    player.powerups.append(SaboteurBloc())
    population = [
        player,
        _static_agent("Rival A", DEFECT),
        _static_agent("Rival B", COOPERATE),
    ]

    core, web = _run_parity(population, player_vote=COOPERATE)

    assert core["result"].player_reward == 0
    assert web["result"].player_reward == core["result"].player_reward
    assert web["score_delta"]["You"] == core["score_delta"]["You"]



def test_rival_referendum_reward_behavior_matches_between_core_and_web() -> None:
    population = [
        _static_agent("You", COOPERATE, is_player=True),
        _static_agent("Rival A", COOPERATE),
        _static_agent("Rival B", DEFECT),
    ]
    population[1].powerups.extend([UnityTicket(), BlocPolitics()])

    core, web = _run_parity(population, player_vote=COOPERATE, floor_number=2)

    assert core["scores"]["Rival A"] == web["scores"]["Rival A"]
    assert core["score_delta"]["Rival A"] == web["score_delta"]["Rival A"]



def test_combo_sensitive_player_reward_matches_between_core_and_web() -> None:
    player = _static_agent("You", DEFECT, is_player=True)
    player.powerups.extend([UnityTicket(), BlocPolitics()])
    population = [
        player,
        _static_agent("Rival A", COOPERATE),
        _static_agent("Rival B", DEFECT),
    ]

    core, web = _run_parity(population, player_vote=DEFECT, floor_number=2)

    assert core["result"].player_vote == web["result"].player_vote == COOPERATE
    assert core["result"].player_reward == web["result"].player_reward
    assert core["score_delta"]["You"] == web["score_delta"]["You"]
