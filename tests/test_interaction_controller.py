from prisoners_gambit.app.interaction_controller import InteractionController
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    FeaturedMatchPrompt,
    FeaturedRoundDecisionState,
    FloorVoteDecisionState,
    FloorVotePrompt,
)
from prisoners_gambit.core.powerups import TrustDividend


class NewRendererStub:
    def __init__(self) -> None:
        self.powerup_action = ChoosePowerupAction(offer_index=0)

    def show_run_header(self, seed):
        pass

    def resolve_featured_round_decision(self, state):
        return ChooseRoundMoveAction(mode="manual_move", move=DEFECT)

    def resolve_floor_vote_decision(self, state):
        return ChooseFloorVoteAction(mode="autopilot_vote")

    def resolve_powerup_choice(self, state):
        return self.powerup_action


class LegacyRendererStub:
    def show_run_header(self, seed):
        pass

    def choose_round_action(self, prompt):
        return COOPERATE

    def choose_floor_vote(self, prompt):
        return DEFECT

    def choose_powerup(self, offers):
        return offers[0]


def test_controller_uses_typed_actions_for_round_and_vote() -> None:
    renderer = NewRendererStub()
    controller = InteractionController(renderer=renderer)
    prompt = FeaturedMatchPrompt(
        floor_number=1,
        masked_opponent_label="Unknown",
        round_index=0,
        total_rounds=3,
        my_history=[],
        opp_history=[],
        my_match_score=0,
        opp_match_score=0,
        suggested_move=COOPERATE,
        roster_entries=[],
    )

    round_move = controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))
    vote = controller.choose_floor_vote(
        FloorVoteDecisionState(
            prompt=FloorVotePrompt(
                floor_number=1,
                floor_label="Test",
                suggested_vote=COOPERATE,
                current_floor_score=0,
                powerups=[],
            )
        )
    )

    assert round_move == DEFECT
    assert vote == COOPERATE


def test_controller_falls_back_to_legacy_renderer_methods() -> None:
    controller = InteractionController(renderer=LegacyRendererStub())
    prompt = FeaturedMatchPrompt(
        floor_number=1,
        masked_opponent_label="Unknown",
        round_index=0,
        total_rounds=3,
        my_history=[],
        opp_history=[],
        my_match_score=0,
        opp_match_score=0,
        suggested_move=DEFECT,
        roster_entries=[],
    )

    move = controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))
    vote = controller.choose_floor_vote(
        FloorVoteDecisionState(
            prompt=FloorVotePrompt(
                floor_number=1,
                floor_label="Test",
                suggested_vote=COOPERATE,
                current_floor_score=0,
                powerups=[],
            )
        )
    )

    offers = [TrustDividend()]
    selected = controller.choose_powerup(1, offers)

    assert move == COOPERATE
    assert vote == DEFECT
    assert selected is offers[0]


def test_autopilot_match_flag_is_set_by_action() -> None:
    class AutoRenderer(NewRendererStub):
        def resolve_featured_round_decision(self, state):
            return ChooseRoundAutopilotAction(mode="autopilot_match")

    controller = InteractionController(renderer=AutoRenderer())
    prompt = FeaturedMatchPrompt(
        floor_number=1,
        masked_opponent_label="Unknown",
        round_index=0,
        total_rounds=3,
        my_history=[],
        opp_history=[],
        my_match_score=0,
        opp_match_score=0,
        suggested_move=COOPERATE,
        roster_entries=[],
    )

    assert controller.should_autopilot_featured_match is False
    move = controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))
    assert move == COOPERATE
    assert controller.should_autopilot_featured_match is True
