import pytest

from prisoners_gambit.app.interaction_controller import InteractionController, RunSession
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
    ChooseGenomeEditAction,
    FeaturedMatchPrompt,
    FeaturedRoundDecisionState,
    FloorVoteDecisionState,
    FloorVotePrompt,
    GenomeEditChoiceState,
    PowerupChoiceState,
    FeaturedRoundStanceView,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import TrustDividend
from prisoners_gambit.core.strategy import StrategyGenome


class NewRendererStub:
    def __init__(self) -> None:
        self.powerup_action = ChoosePowerupAction(offer_index=0)
        self.last_powerup_state: PowerupChoiceState | None = None
        self.last_genome_state: GenomeEditChoiceState | None = None

    def show_run_header(self, seed):
        pass

    def resolve_featured_round_decision(self, state):
        return ChooseRoundMoveAction(mode="manual_move", move=DEFECT)

    def resolve_floor_vote_decision(self, state):
        return ChooseFloorVoteAction(mode="autopilot_vote")

    def resolve_powerup_choice(self, state):
        self.last_powerup_state = state
        return self.powerup_action

    def resolve_genome_edit_choice(self, state):
        self.last_genome_state = state
        return ChooseGenomeEditAction(offer_index=0)


class LegacyRendererStub:
    def show_run_header(self, seed):
        pass

    def choose_round_action(self, prompt):
        return COOPERATE

    def choose_floor_vote(self, prompt):
        return DEFECT

    def choose_powerup(self, offers):
        return offers[0]


def _make_agent(name: str, score: int, wins: int, depth: int) -> Agent:
    return Agent(
        name=name,
        genome=StrategyGenome(
            first_move=COOPERATE,
            response_table={
                (COOPERATE, COOPERATE): COOPERATE,
                (COOPERATE, DEFECT): DEFECT,
                (DEFECT, COOPERATE): COOPERATE,
                (DEFECT, DEFECT): DEFECT,
            },
            noise=0.0,
        ),
        lineage_depth=depth,
        lineage_id=1,
        is_player=False,
        score=score,
        wins=wins,
    )


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


def test_powerup_choice_state_uses_structured_offer_views() -> None:
    renderer = NewRendererStub()
    controller = InteractionController(renderer=renderer)
    selected = controller.choose_powerup(3, [TrustDividend()])

    assert selected.name == "Trust Dividend"
    assert renderer.last_powerup_state is not None
    assert renderer.last_powerup_state.floor_number == 3
    assert renderer.last_powerup_state.offers[0].name == "Trust Dividend"
    assert renderer.last_powerup_state.offers[0].description == TrustDividend().description
    assert " - " not in renderer.last_powerup_state.offers[0].name


def test_genome_edit_choice_state_includes_semantic_fields() -> None:
    from prisoners_gambit.core.genome_edits import OpenWithTrust

    renderer = NewRendererStub()
    controller = InteractionController(renderer=renderer)
    edit = controller.choose_genome_edit(2, "Open D", [OpenWithTrust()])

    assert edit.name == "Open With Trust"
    assert renderer.last_genome_state is not None
    assert renderer.last_genome_state.offers[0].current_summary == "Open D"
    assert renderer.last_genome_state.offers[0].description == OpenWithTrust().description


def test_successor_state_and_run_snapshot_are_populated() -> None:
    class SuccessorRenderer(NewRendererStub):
        def resolve_successor_choice(self, state):
            self.last_successor_state = state
            return ChooseSuccessorAction(candidate_index=0)

    renderer = SuccessorRenderer()
    controller = InteractionController(renderer=renderer)
    a = _make_agent("Heir A", score=8, wins=2, depth=1)
    b = _make_agent("Heir B", score=7, wins=1, depth=2)

    choice = controller.choose_successor(5, [a, b])

    assert choice is a
    assert controller.snapshot.successor_options is not None
    assert controller.snapshot.successor_options.floor_number == 5
    assert controller.snapshot.successor_options.candidates[0].name == "Heir A"
    assert controller.snapshot.successor_options.candidates[0].genome_summary


def test_floor_summary_snapshot_uses_structured_entries() -> None:
    renderer = NewRendererStub()
    controller = InteractionController(renderer=renderer)
    ranked = [_make_agent("A", score=5, wins=2, depth=1), _make_agent("B", score=3, wins=1, depth=2)]

    controller.set_floor_summary(4, ranked)

    assert controller.snapshot.floor_summary is not None
    assert controller.snapshot.floor_summary.floor_number == 4
    assert controller.snapshot.floor_summary.entries[0].name == "A"
    assert controller.snapshot.floor_summary.entries[0].score == 5




def test_floor_summary_snapshot_includes_heir_pressure_analysis() -> None:
    renderer = NewRendererStub()
    controller = InteractionController(renderer=renderer)

    player = _make_agent("You", score=7, wins=2, depth=0)
    player.is_player = True
    player.lineage_id = 1

    heir = _make_agent("Heir Beta", score=6, wins=2, depth=1)
    heir.lineage_id = 1

    outsider = _make_agent("Outsider", score=8, wins=3, depth=0)
    outsider.lineage_id = 99

    controller.set_floor_summary(2, [outsider, player, heir])

    assert controller.snapshot.floor_summary is not None
    pressure = controller.snapshot.floor_summary.heir_pressure
    assert pressure is not None
    assert "Lineage trend:" in pressure.branch_doctrine
    assert pressure.successor_candidates[0].name == "Heir Beta"
    assert pressure.successor_candidates[0].branch_role
    assert pressure.future_threats[0].name == "Outsider"
    assert "if current host dies next floor" in pressure.successor_candidates[0].rationale

def test_run_session_can_resume_with_submitted_action() -> None:
    class CoopRendererStub:
        def show_run_header(self, seed: int | None) -> None:
            pass

        def resolve_featured_round_decision(self, state: FeaturedRoundDecisionState) -> ChooseRoundMoveAction:
            return ChooseRoundMoveAction(mode="manual_move", move=COOPERATE)

    controller = InteractionController(renderer=CoopRendererStub())
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

    move = controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))

    assert move == COOPERATE
    assert controller.session.current_decision is None


def test_stance_action_applies_across_multiple_rounds() -> None:
    class StanceRendererStub:
        def show_run_header(self, seed: int | None) -> None:
            pass

        def resolve_featured_round_decision(self, state: FeaturedRoundDecisionState) -> ChooseRoundStanceAction:
            return ChooseRoundStanceAction(
                mode="set_round_stance",
                stance="follow_autopilot_for_n_rounds",
                rounds=2,
            )

    controller = InteractionController(renderer=StanceRendererStub())
    prompt = FeaturedMatchPrompt(
        floor_number=1,
        masked_opponent_label="Unknown",
        round_index=0,
        total_rounds=4,
        my_history=[],
        opp_history=[],
        my_match_score=0,
        opp_match_score=0,
        suggested_move=DEFECT,
        roster_entries=[],
    )

    first = controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))
    assert first == DEFECT
    assert controller.snapshot.active_featured_stance is not None

    next_prompt = FeaturedRoundDecisionState(
        prompt=FeaturedMatchPrompt(
            floor_number=1,
            masked_opponent_label="Unknown",
            round_index=1,
            total_rounds=4,
            my_history=[COOPERATE],
            opp_history=[COOPERATE],
            my_match_score=0,
            opp_match_score=0,
            suggested_move=COOPERATE,
            roster_entries=[],
        )
    )
    assert controller.can_auto_resolve_featured_round() is True
    second = controller.resolve_featured_round_automation(next_prompt)
    assert second == COOPERATE


def test_manual_override_clears_active_stance() -> None:
    renderer = NewRendererStub()
    controller = InteractionController(renderer=renderer)
    controller._featured_stance = controller.snapshot.active_featured_stance = FeaturedRoundStanceView(
        stance="cooperate_until_betrayed",
        rounds_remaining=None,
        locked_move=None,
    )

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
    # NewRendererStub.resolve_featured_round_decision returns ChooseRoundMoveAction(move=DEFECT),
    # which should clear the active stance.
    move = controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))

    assert move == DEFECT
    assert controller.snapshot.active_featured_stance is None


def test_duration_based_stance_requires_positive_rounds() -> None:
    class BadStanceRendererStub:
        def show_run_header(self, seed: int | None) -> None:
            pass

        def resolve_featured_round_decision(self, state: FeaturedRoundDecisionState) -> ChooseRoundStanceAction:
            return ChooseRoundStanceAction(
                mode="set_round_stance",
                stance="follow_autopilot_for_n_rounds",
                rounds=0,
            )

    controller = InteractionController(renderer=BadStanceRendererStub())
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

    with pytest.raises(ValueError, match="requires rounds > 0"):
        controller.choose_round_move(FeaturedRoundDecisionState(prompt=prompt))


def test_reset_featured_match_autopilot_syncs_session_snapshot() -> None:
    class SpySession(RunSession):
        def __init__(self) -> None:
            super().__init__()
            self.update_calls = 0

        def update_snapshot(self, snapshot) -> None:
            self.update_calls += 1
            super().update_snapshot(snapshot)

    renderer = NewRendererStub()
    session = SpySession()
    controller = InteractionController(renderer=renderer, session=session)
    session.update_calls = 0
    controller._autopilot_featured_match = True
    controller._featured_stance = controller.snapshot.active_featured_stance = FeaturedRoundStanceView(
        stance="cooperate_until_betrayed",
        rounds_remaining=None,
        locked_move=None,
    )

    controller.reset_featured_match_autopilot()

    assert controller.should_autopilot_featured_match is False
    assert controller.snapshot.active_featured_stance is None
    assert session.latest_snapshot.active_featured_stance is None
    assert session.update_calls == 1


def test_set_floor_context_rejects_unknown_phase() -> None:
    controller = InteractionController(renderer=NewRendererStub())

    with pytest.raises(ValueError, match="Invalid phase"):
        controller.set_floor_context(floor_number=2, phase="unknown")


def test_complete_run_rejects_unknown_outcome() -> None:
    controller = InteractionController(renderer=NewRendererStub())

    with pytest.raises(ValueError, match="Invalid outcome"):
        controller.complete_run(outcome="draw", floor_number=2, player_name="You", seed=7)


@pytest.mark.parametrize("outcome", ["victory", "eliminated"])
def test_complete_run_accepts_supported_outcomes(outcome: str) -> None:
    controller = InteractionController(renderer=NewRendererStub())

    controller.complete_run(outcome=outcome, floor_number=2, player_name="You", seed=7)

    assert controller.snapshot.completion is not None
    assert controller.snapshot.completion.outcome == outcome
    assert controller.session.status == "completed"
