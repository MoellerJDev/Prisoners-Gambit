from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.interaction import (
    ChooseRoundAutopilotAction,
    ChooseRoundStanceAction,
    FeaturedMatchPrompt,
    GenomeEditChoiceState,
    GenomeEditOfferView,
    PowerupChoiceState,
    PowerupOfferView,
    SuccessorCandidateView,
    SuccessorChoiceState,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.ui.terminal import TerminalRenderer


def test_terminal_powerup_choice_displays_name_and_description(monkeypatch, capsys) -> None:
    renderer = TerminalRenderer()
    monkeypatch.setattr("builtins.input", lambda _: "1")

    renderer.resolve_powerup_choice(
        PowerupChoiceState(
            floor_number=1,
            offers=[PowerupOfferView(name="Trust Dividend", description="Mutual cooperation gives bonus")],
        )
    )

    out = capsys.readouterr().out
    assert "Trust Dividend" in out
    assert "Mutual cooperation gives bonus" in out


def test_terminal_genome_edit_choice_displays_name_and_description(monkeypatch, capsys) -> None:
    renderer = TerminalRenderer()
    monkeypatch.setattr("builtins.input", lambda _: "1")

    renderer.resolve_genome_edit_choice(
        GenomeEditChoiceState(
            floor_number=2,
            current_summary="Tit-for-tat",
            offers=[GenomeEditOfferView(name="Open with D", description="Set first move to defect")],
        )
    )

    out = capsys.readouterr().out
    assert "Open with D" in out
    assert "Set first move to defect" in out


def test_terminal_successor_choice_displays_rich_candidate_fields(monkeypatch, capsys) -> None:
    renderer = TerminalRenderer()
    monkeypatch.setattr("builtins.input", lambda _: "1")

    renderer.resolve_successor_choice(
        SuccessorChoiceState(
            floor_number=3,
            candidates=[
                SuccessorCandidateView(
                    name="Heir Alpha",
                    lineage_depth=2,
                    score=13,
                    wins=4,
                    branch_role="Safe heir",
                    branch_doctrine="Reciprocal cooperator",
                    tags=["Cooperative", "Retaliatory"],
                    descriptor="Reliable reciprocal responder",
                    tradeoffs=["Safe vs explosive: Safe edge"],
                    strengths=["Can stabilize alliances"],
                    liabilities=["May lose to high-tempo cousins"],
                    attractive_now="Attractive now: counters current aggression.",
                    danger_later="Danger later: may be outpaced in civil war.",
                    lineage_future="Implies slower stable lineage future.",
                    genome_summary="Open C, retaliate D",
                    powerups=["Trust Dividend"],
                )
            ],
        )
    )

    out = capsys.readouterr().out
    assert "Heir Alpha" in out
    assert "depth=2" in out
    assert "Tags: Cooperative, Retaliatory" in out
    assert "Role: Safe heir" in out
    assert "Tradeoffs:" in out
    assert "Danger later:" in out
    assert "Build: Open C, retaliate D" in out
    assert "Powerups: Trust Dividend" in out


def test_choose_round_action_warns_when_match_autopilot_unavailable(monkeypatch, capsys) -> None:
    renderer = TerminalRenderer()
    monkeypatch.setattr(
        renderer,
        "resolve_featured_round_decision",
        lambda state: ChooseRoundAutopilotAction(mode="autopilot_match"),
    )

    move = renderer.choose_round_action(
        FeaturedMatchPrompt(
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
    )

    out = capsys.readouterr().out
    assert move == COOPERATE
    assert "Match autopilot requires an interaction controller" in out


def test_choose_round_action_warns_when_stance_unavailable(monkeypatch, capsys) -> None:
    renderer = TerminalRenderer()
    monkeypatch.setattr(
        renderer,
        "resolve_featured_round_decision",
        lambda state: ChooseRoundStanceAction(mode="set_round_stance", stance="cooperate_until_betrayed"),
    )

    move = renderer.choose_round_action(
        FeaturedMatchPrompt(
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
    )

    out = capsys.readouterr().out
    assert move == DEFECT
    assert "Stance choices require an interaction controller" in out


def _agent(name: str, score: int, wins: int, lineage_id: int, is_player: bool = False) -> Agent:
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
        score=score,
        wins=wins,
        lineage_id=lineage_id,
        is_player=is_player,
    )


def test_floor_summary_surfaces_future_successor_pressure(capsys) -> None:
    renderer = TerminalRenderer()
    ranked = [
        _agent("Outsider Prime", score=12, wins=4, lineage_id=99),
        _agent("You", score=10, wins=3, lineage_id=1, is_player=True),
        _agent("Heir Alpha", score=9, wins=3, lineage_id=1),
    ]

    renderer.show_floor_summary(3, ranked)

    out = capsys.readouterr().out
    assert "[Future Successor Pressure]" in out
    assert "Potential successors if you die next floor" in out
    assert "Heir Alpha" in out
    assert "Emerging external threats" in out
    assert "Outsider Prime" in out
