from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.scoring import base_payoff


def test_base_payoff_matrix() -> None:
    assert base_payoff(COOPERATE, COOPERATE) == (1, 1)
    assert base_payoff(DEFECT, COOPERATE) == (1, 0)
    assert base_payoff(COOPERATE, DEFECT) == (0, 1)
    assert base_payoff(DEFECT, DEFECT) == (0, 0)


def test_base_payoff_is_symmetric_when_moves_are_swapped() -> None:
    left, right = base_payoff(COOPERATE, DEFECT)
    swapped_left, swapped_right = base_payoff(DEFECT, COOPERATE)

    assert left == swapped_right
    assert right == swapped_left


def test_mutual_outcomes_are_equal_for_both_players() -> None:
    coop_left, coop_right = base_payoff(COOPERATE, COOPERATE)
    defect_left, defect_right = base_payoff(DEFECT, DEFECT)

    assert coop_left == coop_right == 1
    assert defect_left == defect_right == 0


def test_defection_against_cooperation_is_strictly_better_than_cooperating() -> None:
    defect_score, coop_victim_score = base_payoff(DEFECT, COOPERATE)
    coop_score, defect_victim_score = base_payoff(COOPERATE, COOPERATE)

    assert defect_score >= coop_score
    assert coop_victim_score < defect_score
    assert defect_victim_score == 1


def test_all_payoffs_are_non_negative() -> None:
    outcomes = [
        base_payoff(COOPERATE, COOPERATE),
        base_payoff(COOPERATE, DEFECT),
        base_payoff(DEFECT, COOPERATE),
        base_payoff(DEFECT, DEFECT),
    ]

    for left, right in outcomes:
        assert left >= 0
        assert right >= 0