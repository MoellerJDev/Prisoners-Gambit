COOPERATE = 0
DEFECT = 1


def move_to_text(move: int) -> str:
    return "C" if move == COOPERATE else "D"