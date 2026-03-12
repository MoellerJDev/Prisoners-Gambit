from prisoners_gambit.core.civil_war import build_civil_war_context
from prisoners_gambit.core.featured_inference import normalize_featured_inference_signals
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import OpeningGambit
from prisoners_gambit.core.strategy import StrategyGenome


def _agent(name: str, score: int) -> Agent:
    agent = Agent(
        name=name,
        genome=StrategyGenome(
            first_move=1,
            response_table={(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0},
            noise=0.0,
        ),
        is_player=False,
        lineage_id=1,
    )
    agent.score = score
    agent.powerups.append(OpeningGambit())
    return agent


def test_build_civil_war_context_uses_shared_top_score_for_role_classification() -> None:
    apex = _agent("Apex", score=20)
    low_control = _agent("Low Control", score=3)

    context = build_civil_war_context(branches=[apex, low_control], current_host=apex)

    assert "Future civil-war monster: 1 branch(es)" in context.dangerous_branches


def test_build_civil_war_context_adds_featured_inference_pressure() -> None:
    apex = _agent("Apex", score=20)
    context = build_civil_war_context(
        branches=[apex],
        current_host=apex,
        featured_inference_signals=normalize_featured_inference_signals([
            "Opened with D and pressed directive tempo across rounds.",
            "Punished cooperation windows after one betrayal.",
        ]),
    )

    assert any("force-heavy pressure" in line for line in context.doctrine_pressure)
    assert any("retaliation risk" in line for line in context.doctrine_pressure)
