from __future__ import annotations

import random


def chance(rng: random.Random, probability: float) -> bool:
    return rng.random() <= probability


def pick_one(rng: random.Random, items: list):
    if not items:
        raise ValueError("Cannot pick from an empty list.")
    return rng.choice(items)