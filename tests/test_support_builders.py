from __future__ import annotations

from support.builders import build_featured_prompt, build_successor_choice_context


def test_build_featured_prompt_supports_richer_histories() -> None:
    prompt = build_featured_prompt(my_history=[0, 1], opp_history=[1, 0], round_index=2, total_rounds=5)

    assert prompt.round_index == 2
    assert prompt.total_rounds == 5
    assert prompt.my_history == [0, 1]
    assert prompt.opp_history == [1, 0]


def test_build_successor_choice_context_produces_phase_aware_views() -> None:
    ranked, views = build_successor_choice_context(include_outsider_threat=True)

    assert len(ranked) >= 3
    assert len(views) >= 2
    for view in views:
        assert view.name
        assert view.branch_role
        assert isinstance(view.shaping_causes, list)
        assert isinstance(view.tradeoffs, list)
