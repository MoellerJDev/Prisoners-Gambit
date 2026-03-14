from prisoners_gambit.core.constants import COOPERATE
from prisoners_gambit.core.interaction import (
    CivilWarContext,
    ChooseFloorVoteAction,
    ChooseRoundMoveAction,
    ChooseSuccessorAction,
    DynastyBoardEntryView,
    DynastyBoardState,
    FloorSummaryEntryView,
    FloorSummaryHeirPressureView,
    FloorSummaryPressureEntryView,
    FloorSummaryState,
    RunSnapshot,
    SuccessorCandidateView,
    SuccessorChoiceState,
)
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


def test_dynasty_board_uses_floor_summary_entries_even_during_successor_choice() -> None:
    floor_entries = [
        FloorSummaryEntryView(1, "You", True, 15, 4, 0, ["host"], "Host", "g", []),
        FloorSummaryEntryView(2, "Kin", False, 12, 3, 1, ["kin"], "Kin branch", "g", [], lineage_relation="kin"),
        FloorSummaryEntryView(3, "Outsider", False, 13, 3, 0, ["outsider"], "Outsider", "g", []),
    ]
    snapshot = RunSnapshot(
        current_phase="ecosystem",
        floor_summary=FloorSummaryState(
            floor_number=2,
            entries=floor_entries,
            heir_pressure=FloorSummaryHeirPressureView(
                branch_doctrine="continuity",
                successor_candidates=[FloorSummaryPressureEntryView(name="Kin", branch_role="heir", shaping_causes=["tested"], score=12, wins=3, tags=["kin"], descriptor="Kin branch", rationale="stable")],
                future_threats=[FloorSummaryPressureEntryView(name="Outsider", branch_role="threat", shaping_causes=["volatile"], score=13, wins=3, tags=["outsider"], descriptor="Outsider", rationale="aggressive")],
            ),
        ),
        successor_options=SuccessorChoiceState(
            floor_number=2,
            candidates=[
                SuccessorCandidateView(
                    name="You",
                    lineage_depth=0,
                    score=15,
                    wins=4,
                    branch_role="host",
                    branch_doctrine="continuity",
                    shaping_causes=[],
                    tags=["host"],
                    descriptor="Host",
                    tradeoffs=[],
                    strengths=[],
                    liabilities=[],
                    attractive_now="",
                    danger_later="",
                    lineage_future="",
                    succession_pitch="",
                    succession_risk="",
                    anti_score_note="",
                    genome_summary="g",
                    powerups=[],
                ),
                SuccessorCandidateView(
                    name="Kin",
                    lineage_depth=1,
                    score=12,
                    wins=3,
                    branch_role="heir",
                    branch_doctrine="continuity",
                    shaping_causes=[],
                    tags=["kin"],
                    descriptor="Kin branch",
                    tradeoffs=[],
                    strengths=[],
                    liabilities=[],
                    attractive_now="",
                    danger_later="",
                    lineage_future="",
                    succession_pitch="",
                    succession_risk="",
                    anti_score_note="",
                    genome_summary="g",
                    powerups=[],
                ),
            ],
        ),
    )

    session = FeaturedMatchWebSession(seed=7, rounds=1)
    session.start()
    board = rebuild_dynasty_board(
        DynastyBoardBuildContext(
            snapshot=snapshot,
            player=session.player,
            opponent=session.opponent,
            successor_candidates=session._successor_candidates,
            current_floor_central_rival="Outsider",
            current_floor_new_central_rival="Outsider",
        )
    )

    assert {entry.name for entry in board.entries} == {"You", "Kin", "Outsider"}
    assert any(entry.name == "Outsider" and entry.is_central_rival for entry in board.entries)


def test_refresh_strategic_snapshot_keeps_rival_and_pressure_coherent_with_stable_board() -> None:
    snapshot = RunSnapshot(
        current_phase="ecosystem",
        dynasty_board=DynastyBoardState(
            phase="ecosystem",
            entries=[
                DynastyBoardEntryView(
                    name="Outsider",
                    role="outsider",
                    doctrine_signal="outsider",
                    score=9,
                    wins=2,
                    lineage_depth=0,
                    is_current_host=False,
                    has_successor_pressure=True,
                    has_civil_war_danger=False,
                    successor_pressure_cause="because succession pressure",
                    is_central_rival=True,
                )
            ],
        ),
        successor_options=SuccessorChoiceState(
            floor_number=1,
            candidates=[],
            threat_profile=["threat lane"],
            lineage_doctrine="continuity",
            civil_war_pressure="contested",
        ),
    )

    strategic = refresh_strategic_snapshot(snapshot, player_name="You", floor_number=1)

    assert "Rival: Outsider" in strategic.chips
    assert "Pressure: threat lane" in strategic.chips
    assert any(detail.startswith("Central rival signal: outsider") for detail in strategic.details)
    assert any(detail.startswith("Why dangerous now: because succession pressure") for detail in strategic.details)
