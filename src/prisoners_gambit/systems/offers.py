from __future__ import annotations

from collections import Counter
import math
from dataclasses import dataclass
import random
from typing import Literal, Sequence

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.offer_guidance import guidance_for_powerup
from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.core.strategy import StrategyGenome

OfferCategory = Literal["reinforcement", "bridge", "wildcard"]


@dataclass(frozen=True, slots=True)
class PowerupOfferContext:
    owned_powerups: Sequence[Powerup] = ()
    genome: StrategyGenome | None = None
    floor_number: int = 1
    phase: str = "both"


@dataclass(frozen=True, slots=True)
class GeneratedPowerupOffer:
    powerup: Powerup
    category: OfferCategory


@dataclass(frozen=True, slots=True)
class _BuildSignal:
    primary_vectors: frozenset[str]
    secondary_vectors: frozenset[str]
    owned_tags: frozenset[str]
    floor_number: int
    phase: str


_CATEGORY_HINTS: dict[OfferCategory, str] = {
    "reinforcement": "Build fit",
    "bridge": "Pivot option",
    "wildcard": "Wildcard",
}


def offer_category_hint(category: OfferCategory) -> str:
    return _CATEGORY_HINTS.get(category, "Wildcard")


def _signal_from_context(context: PowerupOfferContext | None) -> _BuildSignal:
    if context is None:
        return _BuildSignal(
            primary_vectors=frozenset(),
            secondary_vectors=frozenset(),
            owned_tags=frozenset(),
            floor_number=1,
            phase="both",
        )

    vector_counter: Counter[str] = Counter(guidance_for_powerup(powerup).doctrine_vector for powerup in context.owned_powerups)
    for inferred in _genome_vectors(context.genome):
        vector_counter[inferred] += 1

    ranked_vectors = [vector for vector, _ in vector_counter.most_common()]
    primary = frozenset(ranked_vectors[:2])
    secondary = frozenset(ranked_vectors[2:4])
    owned_tags = frozenset(tag for powerup in context.owned_powerups for tag in powerup.keywords)
    return _BuildSignal(
        primary_vectors=primary,
        secondary_vectors=secondary,
        owned_tags=owned_tags,
        floor_number=max(1, context.floor_number),
        phase=context.phase,
    )


def _genome_vectors(genome: StrategyGenome | None) -> tuple[str, ...]:
    if genome is None:
        return ()

    defect_bias = int(genome.first_move == 1) + sum(1 for move in genome.response_table.values() if move == 1)
    coop_bias = 5 - defect_bias
    vectors: list[str] = []
    if coop_bias >= 3:
        vectors.append("trust / reciprocity")
    if defect_bias >= 4:
        vectors.append("opportunism / betrayal")
    if genome.response_table.get((0, 1)) == 1 or genome.response_table.get((1, 1)) == 1:
        vectors.append("coercion / control")
    if genome.noise >= 0.12:
        vectors.append("volatility / chaos")
    return tuple(vectors)


def _lineage_focus_strength(signal: _BuildSignal) -> float:
    vector_strength = min(1.0, len(signal.primary_vectors) * 0.45)
    tag_strength = min(1.0, len(signal.owned_tags) * 0.08)
    return min(1.0, (vector_strength + tag_strength) / 2)


def _category_mix_weights(signal: _BuildSignal) -> dict[OfferCategory, float]:
    focus = _lineage_focus_strength(signal)
    reinforcement = 0.34 + (0.30 * focus)
    bridge = 0.30 + (0.14 if signal.primary_vectors else 0.0) + (0.06 if signal.owned_tags else 0.0)
    wildcard = 0.36 - (0.20 * focus)
    if signal.floor_number <= 3:
        wildcard += 0.06
    if signal.phase == "both":
        wildcard += 0.04

    raw = {
        "reinforcement": max(0.08, reinforcement),
        "bridge": max(0.08, bridge),
        "wildcard": max(0.08, wildcard),
    }
    total = sum(raw.values())
    return {category: value / total for category, value in raw.items()}  # type: ignore[return-value]


def _category_weight(
    powerup: Powerup,
    category: OfferCategory,
    signal: _BuildSignal,
    chosen_vectors: set[str],
    chosen_phases: set[str],
) -> float:
    guidance = guidance_for_powerup(powerup)
    vector = guidance.doctrine_vector
    tags = set(powerup.keywords)
    shared_tags = len(tags & signal.owned_tags)
    phase_bonus = 0.35 if signal.phase == "both" or guidance.phase_support == "both" or guidance.phase_support == signal.phase else 0.0
    novelty_bonus = (0.7 if vector not in chosen_vectors else 0.0) + (0.25 if guidance.phase_support not in chosen_phases else 0.0)

    if category == "reinforcement":
        weight = 1.0
        if vector in signal.primary_vectors:
            weight += 4.8
        elif vector in signal.secondary_vectors:
            weight += 2.2
        weight += shared_tags * 1.0
        if "payoff" in tags and signal.floor_number >= 8:
            weight += 0.5
        return weight + phase_bonus + novelty_bonus

    if category == "bridge":
        weight = 0.8
        if "bridge" in tags:
            weight += 2.6
        if shared_tags > 0:
            weight += 3.2
        if vector in signal.secondary_vectors:
            weight += 1.6
        if "anchor" in tags and signal.floor_number <= 4:
            weight += 0.8
        return weight + phase_bonus + novelty_bonus

    weight = 0.6
    if vector not in signal.primary_vectors and vector not in signal.secondary_vectors:
        weight += 2.4
    if shared_tags == 0:
        weight += 1.0
    if "anchor" in tags or "amplifier" in tags:
        weight += 0.2
    return weight + novelty_bonus + (0.2 if phase_bonus == 0 else 0.0)


def _weighted_pick(
    rng: random.Random,
    candidates: list[Powerup],
    category: OfferCategory,
    signal: _BuildSignal,
    chosen_vectors: set[str],
    chosen_phases: set[str],
) -> Powerup:
    raw_weights = [
        _category_weight(candidate, category, signal, chosen_vectors=chosen_vectors, chosen_phases=chosen_phases)
        for candidate in candidates
    ]
    weights = [weight if math.isfinite(weight) and weight > 0 else 0.0 for weight in raw_weights]
    if any(weight > 0 for weight in weights):
        return rng.choices(candidates, weights=weights, k=1)[0]

    # Safety fallback only when weights are invalid/non-positive.
    fallback_weight = max(raw_weights) if raw_weights else 0.0
    fallback_candidates = [candidate for candidate, weight in zip(candidates, raw_weights) if weight == fallback_weight]
    return rng.choice(fallback_candidates if fallback_candidates else candidates)


def _choose_offer_category(
    rng: random.Random,
    signal: _BuildSignal,
    counts_by_category: Counter[OfferCategory],
    offers_remaining: int,
) -> OfferCategory:
    mix = _category_mix_weights(signal)
    categories: list[OfferCategory] = ["reinforcement", "bridge", "wildcard"]
    weights = [mix[category] for category in categories]

    for idx, category in enumerate(categories):
        if counts_by_category[category] >= 2:
            weights[idx] *= 0.5

    seen_categories = {category for category, count in counts_by_category.items() if count > 0}
    if offers_remaining == 1 and len(seen_categories) < 2:
        for idx, category in enumerate(categories):
            if category not in seen_categories:
                weights[idx] *= 2.0

    return rng.choices(categories, weights=weights, k=1)[0]


def generate_powerup_offer_set(
    count: int,
    rng: random.Random,
    context: PowerupOfferContext | None = None,
) -> list[GeneratedPowerupOffer]:
    pool = build_powerup_pool()
    if count <= 0:
        return []

    signal = _signal_from_context(context)
    categories: list[OfferCategory] = []
    counts_by_category: Counter[OfferCategory] = Counter()
    for index in range(count):
        category = _choose_offer_category(rng, signal, counts_by_category, offers_remaining=count - index)
        categories.append(category)
        counts_by_category[category] += 1

    chosen: list[GeneratedPowerupOffer] = []
    used_types: set[type[Powerup]] = set()
    chosen_vectors: set[str] = set()
    chosen_phases: set[str] = set()

    for category in categories:
        remaining_pool = [powerup for powerup in pool if type(powerup) not in used_types]
        if not remaining_pool:
            break
        pick = _weighted_pick(
            rng,
            remaining_pool,
            category,
            signal,
            chosen_vectors=chosen_vectors,
            chosen_phases=chosen_phases,
        )
        used_types.add(type(pick))
        chosen.append(GeneratedPowerupOffer(powerup=pick.clone(), category=category))
        pick_guidance = guidance_for_powerup(pick)
        chosen_vectors.add(pick_guidance.doctrine_vector)
        chosen_phases.add(pick_guidance.phase_support)

    while len(chosen) < count:
        fallback = rng.choice(pool).clone()
        chosen.append(GeneratedPowerupOffer(powerup=fallback, category="wildcard"))

    return chosen


def generate_powerup_offers(
    count: int,
    rng: random.Random,
    context: PowerupOfferContext | None = None,
) -> list[Powerup]:
    return [entry.powerup for entry in generate_powerup_offer_set(count, rng, context)]
