from __future__ import annotations

import pytest

from prisoners_gambit.core.constants import COOPERATE, DEFECT

from support.builders import build_featured_prompt, build_featured_prompt_scenario, build_successor_choice_context


def test_build_featured_prompt_supports_richer_histories() -> None:
    prompt = build_featured_prompt(my_history=[0, 1], opp_history=[1, 0], round_index=2, total_rounds=5)

    assert prompt.round_index == 2
    assert prompt.total_rounds == 5
    assert prompt.my_history == [0, 1]
    assert prompt.opp_history == [1, 0]


def test_build_featured_prompt_scenario_sets_consistent_history_and_scores() -> None:
    prompt = build_featured_prompt_scenario(my_history=[COOPERATE, DEFECT, DEFECT], opp_history=[COOPERATE, COOPERATE, DEFECT])

    assert prompt.round_index == 3
    assert prompt.my_match_score == 2
    assert prompt.opp_match_score == 1


def test_build_featured_prompt_scenario_requires_equal_history_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        build_featured_prompt_scenario(my_history=[COOPERATE], opp_history=[COOPERATE, DEFECT])


def test_build_successor_choice_context_produces_phase_aware_views() -> None:
    ranked, views = build_successor_choice_context(include_outsider_threat=True, threat_tag="aggressive-outsider", phase="civil_war")

    assert len(ranked) >= 3
    assert len(views) >= 2
    assert "aggressive-outsider" in ranked[0].public_profile
    for view in views:
        assert view.name
        assert view.branch_role
        assert isinstance(view.shaping_causes, list)
        assert isinstance(view.tradeoffs, list)
