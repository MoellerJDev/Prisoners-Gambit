from prisoners_gambit.core.analysis import analyze_agent_identity, analyze_floor_heir_pressure, assess_successor_candidate
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import (
    BlocPolitics,
    CoerciveControl,
    LastLaugh,
    TrustDividend,
)
from prisoners_gambit.core.strategy import StrategyGenome


def make_agent(
    *,
    first_move: int = COOPERATE,
    cc: int = COOPERATE,
    cd: int = DEFECT,
    dc: int = COOPERATE,
    dd: int = DEFECT,
    noise: float = 0.0,
) -> Agent:
    return Agent(
        name="Test Agent",
        genome=StrategyGenome(
            first_move=first_move,
            response_table={
                (COOPERATE, COOPERATE): cc,
                (COOPERATE, DEFECT): cd,
                (DEFECT, COOPERATE): dc,
                (DEFECT, DEFECT): dd,
            },
            noise=noise,
        ),
    )


def test_analysis_marks_cooperative_and_retaliatory_agent() -> None:
    agent = make_agent(first_move=COOPERATE, cd=DEFECT, dc=COOPERATE, noise=0.0)

    identity = analyze_agent_identity(agent)

    assert "Cooperative" in identity.tags
    assert "Retaliatory" in identity.tags
    assert "Precise" in identity.tags
    assert "Reciprocal" not in identity.tags  # avoid phantom tags
    assert isinstance(identity.descriptor, str) and identity.descriptor


def test_analysis_marks_aggressive_and_exploitative_agent() -> None:
    agent = make_agent(first_move=DEFECT, dc=DEFECT)

    identity = analyze_agent_identity(agent)

    assert "Aggressive" in identity.tags
    assert "Exploitative" in identity.tags


def test_analysis_marks_forgiving_when_dd_returns_to_cooperation() -> None:
    agent = make_agent(dd=COOPERATE)

    identity = analyze_agent_identity(agent)

    assert "Forgiving" in identity.tags


def test_analysis_marks_unstable_for_high_noise() -> None:
    agent = make_agent(noise=0.20)

    identity = analyze_agent_identity(agent)

    assert "Unstable" in identity.tags


def test_analysis_marks_control_when_control_perks_present() -> None:
    agent = make_agent()
    agent.powerups.append(CoerciveControl())

    identity = analyze_agent_identity(agent)

    assert "Control" in identity.tags


def test_analysis_marks_referendum_when_vote_perks_present() -> None:
    agent = make_agent()
    agent.powerups.append(BlocPolitics())

    identity = analyze_agent_identity(agent)

    assert "Referendum" in identity.tags


def test_analysis_marks_consensus_when_trust_dividend_present() -> None:
    agent = make_agent()
    agent.powerups.append(TrustDividend())

    identity = analyze_agent_identity(agent)

    assert "Consensus" in identity.tags


def test_analysis_marks_tempo_when_timing_perks_present() -> None:
    agent = make_agent()
    agent.powerups.append(LastLaugh())

    identity = analyze_agent_identity(agent)

    assert "Tempo" in identity.tags


def test_analysis_limits_tag_count_to_four() -> None:
    agent = make_agent(first_move=DEFECT, cd=DEFECT, dc=DEFECT, dd=COOPERATE, noise=0.20)
    agent.powerups.append(CoerciveControl())
    agent.powerups.append(BlocPolitics())
    agent.powerups.append(TrustDividend())
    agent.powerups.append(LastLaugh())

    identity = analyze_agent_identity(agent)

    assert len(identity.tags) <= 4


def test_branch_role_classification_marks_unstable_successor() -> None:
    agent = make_agent(noise=0.25)
    assessed = assess_successor_candidate(agent, top_score=10)

    assert assessed.branch_role == "Unstable heir"
    assert any("Stable vs volatile" in item for item in assessed.tradeoffs)


def test_heir_pressure_candidates_include_shaping_causes() -> None:
    player = make_agent(first_move=COOPERATE)
    player.is_player = True
    player.lineage_id = 7
    player.score = 10

    heir = make_agent(first_move=DEFECT, dc=DEFECT)
    heir.lineage_id = 7
    heir.score = 9

    outsider = make_agent(noise=0.2)
    outsider.lineage_id = 99
    outsider.score = 11

    pressure = analyze_floor_heir_pressure([outsider, player, heir], player_lineage_id=7)

    assert pressure.successor_candidates
    assert pressure.successor_candidates[0].shaping_causes
    assert pressure.future_threats
    assert pressure.future_threats[0].shaping_causes
