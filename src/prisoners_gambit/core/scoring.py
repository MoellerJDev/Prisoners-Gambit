from __future__ import annotations

from prisoners_gambit.core.constants import COOPERATE, DEFECT


def base_payoff(left_move: int, right_move: int) -> tuple[int, int]:
    if left_move == DEFECT and right_move == COOPERATE:
        return 1, 0

    if left_move == COOPERATE and right_move == DEFECT:
        return 0, 1

    if left_move == COOPERATE and right_move == COOPERATE:
        return 1, 1

    return 0, 0