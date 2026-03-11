from __future__ import annotations

from dataclasses import dataclass
import random

from prisoners_gambit.core.constants import COOPERATE, DEFECT

State = tuple[int, int]


@dataclass(slots=True)
class StrategyGenome:
    first_move: int
    response_table: dict[State, int]
    noise: float = 0.0

    def choose_move(
        self,
        my_history: list[int],
        opp_history: list[int],
        rng: random.Random,
    ) -> int:
        if not my_history:
            intended = self.first_move
        else:
            state = (my_history[-1], opp_history[-1])
            intended = self.response_table[state]

        if rng.random() < self.noise:
            return COOPERATE if intended == DEFECT else DEFECT

        return intended

    def mutate(self, rng: random.Random, mutation_rate: float) -> "StrategyGenome":
        new_first_move = self.first_move
        new_response_table = dict(self.response_table)
        new_noise = self.noise

        if rng.random() < mutation_rate:
            new_first_move = COOPERATE if self.first_move == DEFECT else DEFECT

        for state in new_response_table:
            if rng.random() < mutation_rate:
                new_response_table[state] = (
                    COOPERATE if new_response_table[state] == DEFECT else DEFECT
                )

        if rng.random() < mutation_rate:
            new_noise = max(0.0, min(0.35, self.noise + rng.uniform(-0.05, 0.05)))

        return StrategyGenome(
            first_move=new_first_move,
            response_table=new_response_table,
            noise=new_noise,
        )

    def summary(self) -> str:
        states = [
            (COOPERATE, COOPERATE),
            (COOPERATE, DEFECT),
            (DEFECT, COOPERATE),
            (DEFECT, DEFECT),
        ]
        table_bits = "".join(
            "C" if self.response_table[state] == COOPERATE else "D"
            for state in states
        )
        first = "C" if self.first_move == COOPERATE else "D"
        return f"F:{first} T:{table_bits} N:{self.noise:.2f}"


def random_genome(rng: random.Random) -> StrategyGenome:
    states = [
        (COOPERATE, COOPERATE),
        (COOPERATE, DEFECT),
        (DEFECT, COOPERATE),
        (DEFECT, DEFECT),
    ]

    return StrategyGenome(
        first_move=rng.choice([COOPERATE, DEFECT]),
        response_table={state: rng.choice([COOPERATE, DEFECT]) for state in states},
        noise=rng.uniform(0.0, 0.1),
    )