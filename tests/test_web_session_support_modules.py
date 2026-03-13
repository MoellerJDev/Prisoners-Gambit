from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import ChooseRoundMoveAction, DynastyBoardState
from prisoners_gambit.web.session_snapshot_support import lineage_cause_phrase, refresh_strategic_snapshot
from prisoners_gambit.web.session_state_codec import export_save_code, import_save_code
from prisoners_gambit.web.web_slice import FeaturedMatchWebSession, SAVE_STATE_VERSION


def test_lineage_cause_phrase_matches_existing_format() -> None:
    assert lineage_cause_phrase(["  pressure wave. "], "fallback") == "because pressure wave"
    assert lineage_cause_phrase([], "fallback reason.") == "because fallback reason"


def test_state_codec_round_trip_payload_integrity() -> None:
    payload_json = "{\"seed\":7,\"version\":1}"
    code = export_save_code(payload_json, b"secret", version=SAVE_STATE_VERSION)
    assert import_save_code(code, b"secret", version=SAVE_STATE_VERSION) == {"seed": 7, "version": 1}


def test_refresh_strategic_snapshot_uses_snapshot_central_rival() -> None:
    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    session.submit_action(ChooseRoundMoveAction(mode="manual_move", move=COOPERATE))
    session.advance()

    strategic = refresh_strategic_snapshot(session.snapshot, player_name=session.player.name, floor_number=session.floor_number)
    assert strategic.headline.startswith("Host")
    assert any(chip.startswith("Rival:") for chip in strategic.chips)
    assert isinstance(session.snapshot.dynasty_board, DynastyBoardState)
