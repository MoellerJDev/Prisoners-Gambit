from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import (
    GenomeEditChoiceState,
    GenomeEditOfferView,
    PowerupChoiceState,
    PowerupOfferView,
    SuccessorCandidateView,
    SuccessorChoiceState,
)
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
                    tags=["Cooperative", "Retaliatory"],
                    descriptor="Reliable reciprocal responder",
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
    assert "Build: Open C, retaliate D" in out
    assert "Powerups: Trust Dividend" in out
