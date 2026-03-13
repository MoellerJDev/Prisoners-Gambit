from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import ChooseFloorVoteAction, ChooseRoundMoveAction, DynastyBoardState
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
