from __future__ import annotations

from prisoners_gambit.core.constants import COOPERATE, DEFECT


def move_symbol(move: int) -> str:
    if move == COOPERATE:
        return "C"
    if move == DEFECT:
        return "D"
    return "?"