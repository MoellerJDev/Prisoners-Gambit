from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.genome_edits import OpenWithTrust
from prisoners_gambit.core.interaction import (
    FeaturedMatchPrompt,
    FeaturedRoundResult,
    FloorVotePrompt,
    FloorVoteResult,
    RoundDirectiveResolution,
    RoundResolutionBreakdown,
    RosterEntry,
    ScoreAdjustment,
)
from prisoners_gambit.core.powerups import MoveDirective
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import TrustDividend
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.ui.view_models import (
    format_agent_line,
    format_featured_prompt,
    format_floor_vote_prompt,
    format_floor_vote_result,
    format_genome_edit_line,
    format_powerup_line,
    format_roster_line,
    format_round_result,
    format_successor_line,
)


def make_agent(*, is_player: bool = False) -> Agent:
    return Agent(
        name="You" if is_player else "Bot",
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
        is_player=is_player,
        lineage_id=1 if is_player else None,
        lineage_depth=2 if is_player else 0,
    )


def test_format_agent_line_marks_player_and_shows_tags() -> None:
    line = format_agent_line(1, make_agent(is_player=True))
    assert "[YOU]" in line
    assert "score=" in line
    assert "wins=" in line
    assert "Cooperative" in line


def test_format_agent_line_for_non_player_has_no_you_marker() -> None:
    line = format_agent_line(2, make_agent(is_player=False))
    assert "[YOU]" not in line


def test_format_powerup_line_includes_name_and_description() -> None:
    powerup = TrustDividend(bonus=2)
    line = format_powerup_line(1, powerup)

    assert "Trust Dividend" in line
    assert powerup.description in line


def test_format_roster_line_includes_tags_descriptor_and_powerups() -> None:
    entry = RosterEntry(
        name="Bot",
        public_profile="Reactive",
        known_powerups=["Trust Dividend", "Spite Engine"],
        tags=["Cooperative", "Retaliatory"],
        descriptor="Reciprocal cooperator with cooperation incentives and low-noise execution",
    )
    line = format_roster_line(1, entry)

    assert "Bot" in line
    assert "Reactive" in line
    assert "Tags:" in line
    assert "Cooperative, Retaliatory" in line
    assert "Read:" in line
    assert "Visible powerups:" in line


def test_format_genome_edit_line_includes_name_and_description() -> None:
    edit = OpenWithTrust()
    line = format_genome_edit_line(1, edit)

    assert edit.name in line
    assert edit.description in line


def test_format_featured_prompt_includes_histories_and_autopilot_suggestion() -> None:
    prompt = FeaturedMatchPrompt(
        floor_number=2,
        masked_opponent_label="Unknown Opponent 1",
        round_index=1,
        total_rounds=5,
        my_history=[COOPERATE, DEFECT],
        opp_history=[DEFECT, COOPERATE],
        my_match_score=3,
        opp_match_score=2,
        suggested_move=COOPERATE,
        roster_entries=[],
    )
    text = format_featured_prompt(prompt)

    assert "Unknown Opponent 1" in text
    assert "Round 2/5" in text
    assert "Your history:" in text
    assert "Their history:" in text
    assert "Autopilot suggests: C" in text


def test_format_round_result_includes_reasons_and_totals() -> None:
    result = FeaturedRoundResult(
        masked_opponent_label="Unknown Opponent 2",
        round_index=0,
        total_rounds=4,
        player_move=COOPERATE,
        opponent_move=DEFECT,
        player_delta=0,
        opponent_delta=2,
        player_total=0,
        opponent_total=2,
        player_reason="base",
        opponent_reason="Saboteur Bloc@200",
        breakdown=RoundResolutionBreakdown(
            player_plan=COOPERATE,
            opponent_plan=DEFECT,
            player_directives=RoundDirectiveResolution(
                base_move=COOPERATE,
                final_move=COOPERATE,
                reason="base",
                directives=[],
            ),
            opponent_directives=RoundDirectiveResolution(
                base_move=DEFECT,
                final_move=DEFECT,
                reason="Saboteur Bloc@200",
                directives=[MoveDirective(move=DEFECT, priority=200, source="Saboteur Bloc")],
            ),
            base_player_points=0,
            base_opponent_points=1,
            score_adjustments=[
                ScoreAdjustment(source="Spite Engine", player_delta=0, opponent_delta=1),
            ],
            final_player_points=0,
            final_opponent_points=2,
        ),
    )
    text = format_round_result(result)

    assert "Autopilot planned: You=C, Opp=D" in text
    assert "Directives: You=base | Opp=Saboteur Bloc@200" in text
    assert "Score modifiers: Spite Engine: +0/+1" in text
    assert "Match total: 0 / 2" in text


def test_format_floor_vote_prompt_includes_label_and_powerups() -> None:
    prompt = FloorVotePrompt(
        floor_number=4,
        floor_label="Opening Tables",
        suggested_vote=DEFECT,
        current_floor_score=12,
        powerups=["Bloc Politics", "Mercy Shield"],
    )
    text = format_floor_vote_prompt(prompt)

    assert "Floor 4 - Opening Tables" in text
    assert "Bloc Politics" in text
    assert "Mercy Shield" in text
    assert "Autopilot suggests: D" in text


def test_format_floor_vote_result_includes_outcome_counts_and_reward() -> None:
    result = FloorVoteResult(
        floor_number=4,
        cooperation_prevailed=True,
        cooperators=7,
        defectors=5,
        player_vote=COOPERATE,
        player_reward=5,
    )
    text = format_floor_vote_result(result)

    assert "Cooperation prevailed" in text
    assert "Cooperators: 7 | Defectors: 5" in text
    assert "Your vote: C | Your reward: 5" in text


def test_format_successor_line_includes_tags_descriptor_stats_summary_and_powerups() -> None:
    agent = make_agent(is_player=True)
    agent.name = "Heir Gamma"
    agent.score = 18
    agent.wins = 4
    agent.powerups.append(TrustDividend(bonus=2))

    text = format_successor_line(1, agent)

    assert "Heir Gamma" in text
    assert "depth=2" in text
    assert "score=18" in text
    assert "wins=4" in text
    assert "Tags:" in text
    assert "Read:" in text
    assert "Build:" in text
    assert "Powerups:" in text
    assert "Trust Dividend" in text


def test_format_featured_prompt_and_round_result_include_inference_channels() -> None:
    prompt = FeaturedMatchPrompt(
        floor_number=2,
        masked_opponent_label="Unknown Opponent 1",
        round_index=1,
        total_rounds=5,
        my_history=[COOPERATE, DEFECT],
        opp_history=[DEFECT, COOPERATE],
        my_match_score=3,
        opp_match_score=2,
        suggested_move=COOPERATE,
        roster_entries=[],
        clue_channels=["Profile signal: Volatile tactician", "Known powerups: Counter-Intel"],
        floor_clue_log=["Opened with D", "Retaliated after pressure"],
        inference_focus="Pattern read",
    )
    text = format_featured_prompt(prompt)
    assert "Clues in play:" in text
    assert "Floor clue memory:" in text
    assert "Inference focus: Pattern read" in text

    result = FeaturedRoundResult(
        masked_opponent_label="Unknown Opponent 2",
        round_index=0,
        total_rounds=4,
        player_move=COOPERATE,
        opponent_move=DEFECT,
        player_delta=0,
        opponent_delta=2,
        player_total=0,
        opponent_total=2,
        player_reason="base",
        opponent_reason="Saboteur Bloc@200",
        inference_update=["Exploitative pressure read strengthened."],
        breakdown=RoundResolutionBreakdown(
            player_plan=COOPERATE,
            opponent_plan=DEFECT,
            player_directives=RoundDirectiveResolution(base_move=COOPERATE, final_move=COOPERATE, reason="base", directives=[]),
            opponent_directives=RoundDirectiveResolution(
                base_move=DEFECT,
                final_move=DEFECT,
                reason="Saboteur Bloc@200",
                directives=[MoveDirective(move=DEFECT, priority=200, source="Saboteur Bloc")],
            ),
            base_player_points=0,
            base_opponent_points=1,
            score_adjustments=[ScoreAdjustment(source="Spite Engine", player_delta=0, opponent_delta=1)],
            final_player_points=0,
            final_opponent_points=2,
        ),
    )
    result_text = format_round_result(result)
    assert "Inference update:" in result_text
    assert "Exploitative pressure read strengthened." in result_text
