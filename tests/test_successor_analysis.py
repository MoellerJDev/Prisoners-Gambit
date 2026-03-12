from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.identity_analysis import analyze_agent_identity
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.core.successor_analysis import (
    assess_successor_candidate,
    classify_branch_role,
    shaping_causes_for_agent,
)


def _agent(*, first_move=COOPERATE, noise=0.0, score=5) -> Agent:
    return Agent(
        name="Candidate",
        genome=StrategyGenome(
            first_move=first_move,
            response_table={
                (COOPERATE, COOPERATE): COOPERATE,
                (COOPERATE, DEFECT): DEFECT,
                (DEFECT, COOPERATE): DEFECT,
                (DEFECT, DEFECT): DEFECT,
            },
            noise=noise,
        ),
        score=score,
    )


def test_classify_branch_role_prefers_unstable_with_high_noise() -> None:
    agent = _agent(noise=0.22)
    identity = analyze_agent_identity(agent)

    assert classify_branch_role(agent, identity, top_score=10) == "Unstable heir"


def test_shaping_causes_reports_control_and_variance() -> None:
    agent = _agent(noise=0.22)
    identity = analyze_agent_identity(agent)

    causes = shaping_causes_for_agent(agent, identity)

    assert causes
    assert any("variance" in cause for cause in causes)


def test_assess_successor_candidate_returns_structured_tradeoffs() -> None:
    agent = _agent(first_move=DEFECT, score=9)

    assessment = assess_successor_candidate(agent, top_score=10, threat_tags={"Aggressive"}, phase="ecosystem")

    assert assessment.branch_role in {
        "Safe heir",
        "Ruthless heir",
        "Unstable heir",
        "Referendum heir",
        "Future civil-war monster",
    }
    assert len(assessment.tradeoffs) == 5
    assert assessment.strengths
    assert assessment.liabilities
    assert assessment.succession_pitch
    assert assessment.succession_risk
    assert assessment.anti_score_note


def test_assessment_can_recommend_lower_score_for_matchup_coverage() -> None:
    agent = _agent(first_move=COOPERATE, score=7)

    assessment = assess_successor_candidate(
        agent,
        top_score=10,
        threat_tags={"Aggressive", "Referendum"},
        phase="ecosystem",
        lineage_doctrine="Lineage trend: Aggressive, Tempo across 3 active branch(es).",
    )

    assert "Do not pick by score alone" in assessment.anti_score_note
    assert "Implies" in assessment.lineage_future
