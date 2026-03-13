from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import CivilWarContext, ChooseFloorVoteAction, ChooseRoundMoveAction, ChooseSuccessorAction, DynastyBoardState
from prisoners_gambit.web.floor_summary_support import FloorContinuityContext, synthesize_floor_summary
from prisoners_gambit.web.session_snapshot_support import (
    DynastyBoardBuildContext,
    lineage_cause_phrase,
    rebuild_dynasty_board,
    refresh_strategic_snapshot,
)
from prisoners_gambit.web.session_state_codec import export_save_code, import_save_code
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession, SAVE_STATE_VERSION


def test_lineage_cause_phrase_matches_existing_format() -> None:
    assert lineage_cause_phrase(["  pressure wave. "], "fallback") == "because pressure wave"
    assert lineage_cause_phrase([], "fallback reason.") == "because fallback reason"


def test_state_codec_round_trip_payload_integrity() -> None:
    payload_json = "{\"seed\":7,\"version\":1}"
    code = export_save_code(payload_json, b"secret", version=SAVE_STATE_VERSION)
    assert import_save_code(code, b"secret", version=SAVE_STATE_VERSION) == {"seed": 7, "version": 1}


def test_refresh_strategic_snapshot_uses_typed_snapshot_and_central_rival() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()

    strategic = refresh_strategic_snapshot(session.snapshot, player_name=session.player.name, floor_number=session.floor_number)
    assert strategic.headline.startswith("Host")
    assert any(chip.startswith("Rival:") for chip in strategic.chips)
    assert isinstance(session.snapshot.dynasty_board, DynastyBoardState)


def test_floor_summary_synthesis_accepts_continuity_context() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()

    synthesis = synthesize_floor_summary(
        floor_number=session.floor_number,
        summary_agents=session._branch_floor_ranking(),
        player=session.player,
        floor_clue_log=session._floor_clue_log,
        continuity=FloorContinuityContext(
            previous_floor_names=session._previous_floor_names,
            branch_continuity_streaks=session._branch_continuity_streaks,
            previous_branch_stats=session._previous_branch_stats,
            previous_pressure_levels=session._previous_pressure_levels,
            previous_central_rival=session._previous_central_rival,
        ),
    )

    assert synthesis.summary.floor_number == session.floor_number
    assert synthesis.continuity.previous_central_rival == synthesis.central_rival_name


def test_dynasty_board_rebuild_accepts_context_object() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()

    board = rebuild_dynasty_board(
        DynastyBoardBuildContext(
            snapshot=session.snapshot,
            player=session.player,
            opponent=session.opponent,
            successor_candidates=session._successor_candidates,
            current_floor_central_rival=session._current_floor_central_rival,
            current_floor_new_central_rival=session._current_floor_new_central_rival,
        )
    )

    assert isinstance(board, DynastyBoardState)


def test_refresh_strategic_snapshot_surfaces_floor_identity_consequence_cause() -> None:
    session = FeaturedMatchWebSession(seed=17, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()
    session.submit_action(ChooseFloorVoteAction(mode="manual_vote", vote=COOPERATE))
    session.advance()
    session.advance()
    session.submit_action(ChooseSuccessorAction(candidate_index=0))
    session.advance()

    strategic = refresh_strategic_snapshot(session.snapshot, player_name=session.player.name, floor_number=session.floor_number)
    assert any(line.startswith("Why dangerous now: ") for line in strategic.details)


def test_refresh_strategic_snapshot_surfaces_civil_war_buildup_signal_deterministically() -> None:
    session_a = FeaturedMatchWebSession(seed=7, rounds=1)
    session_a.start()
    session_a.snapshot.civil_war_context = CivilWarContext(
        thesis="Judgment arrives",
        scoring_rules=["Rule"],
        dangerous_branches=["Directive bloc"],
        doctrine_pressure=["retaliation risk is compounding"],
    )

    session_b = FeaturedMatchWebSession(seed=7, rounds=1)
    session_b.start()
    session_b.snapshot.civil_war_context = CivilWarContext(
        thesis="Judgment arrives",
        scoring_rules=["Rule"],
        dangerous_branches=["Directive bloc"],
        doctrine_pressure=["retaliation risk is compounding"],
    )

    strategic_a = refresh_strategic_snapshot(session_a.snapshot, player_name=session_a.player.name, floor_number=session_a.floor_number)
    strategic_b = refresh_strategic_snapshot(session_b.snapshot, player_name=session_b.player.name, floor_number=session_b.floor_number)

    buildup_a = [line for line in strategic_a.details if line.startswith("Civil-war buildup: ")]
    buildup_b = [line for line in strategic_b.details if line.startswith("Civil-war buildup: ")]
    assert buildup_a == buildup_b == ["Civil-war buildup: retaliation risk is compounding"]
