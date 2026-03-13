from __future__ import annotations

from collections import Counter
import math
from dataclasses import dataclass
import random
from typing import Literal, Sequence

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.core.strategy import StrategyGenome

OfferCategory = Literal["familiar_line", "hybrid_line", "temptation"]
_DOCTRINE_FAMILIES: tuple[str, ...] = ("trust", "control", "retaliation", "opportunist", "referendum", "chaos")

_HYBRID_PAIRS: dict[str, tuple[str, ...]] = {
    "trust": ("opportunist",),
    "control": ("retaliation",),
    "referendum": ("control",),
    "chaos": ("opportunist",),
    "retaliation": ("control",),
    "opportunist": ("trust", "chaos"),
}


@dataclass(frozen=True, slots=True)
class PowerupOfferContext:
    owned_powerups: Sequence[Powerup] = ()
    genome: StrategyGenome | None = None
    floor_number: int = 1
    phase: str = "both"
    primary_doctrine_family: str | None = None
    secondary_doctrine_family: str | None = None


@dataclass(frozen=True, slots=True)
class GeneratedPowerupOffer:
    powerup: Powerup
    category: OfferCategory


@dataclass(frozen=True, slots=True)
class _BuildSignal:
    primary_family: str
    secondary_family: str | None
    owned_families: frozenset[str]
    owned_tags: frozenset[str]
    floor_number: int
    phase: str


_CATEGORY_HINTS: dict[OfferCategory, str] = {
    "familiar_line": "Deepen house",
    "hybrid_line": "Mutate lineage",
    "temptation": "Power risk",
}


def offer_category_hint(category: OfferCategory) -> str:
    return _CATEGORY_HINTS.get(category, "Power risk")


def _normalize_family(family: str | None) -> str | None:
    if family in _DOCTRINE_FAMILIES:
        return family
    return None


def _infer_primary_from_owned(owned_powerups: Sequence[Powerup]) -> str | None:
    family_counter: Counter[str] = Counter(p.doctrine_family for p in owned_powerups)
    if not family_counter:
        return None
    return family_counter.most_common(1)[0][0]


def _infer_from_genome(genome: StrategyGenome | None) -> tuple[str | None, str | None]:
    if genome is None:
        return None, None
    defect_bias = int(genome.first_move == 1) + sum(1 for move in genome.response_table.values() if move == 1)
    coop_bias = 5 - defect_bias
    primary: str | None = None
    secondary: str | None = None
    if coop_bias >= 3:
        primary = "trust"
    if defect_bias >= 4:
        primary = primary or "opportunist"
        secondary = secondary or "retaliation"
    if genome.response_table.get((0, 1)) == 1 or genome.response_table.get((1, 1)) == 1:
        primary = primary or "control"
    if genome.noise >= 0.12:
        secondary = secondary or "chaos"
    return primary, secondary


def _deterministic_house_seed(*, floor_number: int, phase: str) -> str:
    phase_idx = {"ecosystem": 0, "civil_war": 1, "both": 2}.get(phase, 2)
    return _DOCTRINE_FAMILIES[(floor_number + phase_idx) % len(_DOCTRINE_FAMILIES)]


def _signal_from_context(context: PowerupOfferContext | None) -> _BuildSignal:
    if context is None:
        return _BuildSignal(
            primary_family=_deterministic_house_seed(floor_number=1, phase="both"),
            secondary_family=None,
            owned_families=frozenset(),
            owned_tags=frozenset(),
            floor_number=1,
            phase="both",
        )

    owned_families = frozenset(p.doctrine_family for p in context.owned_powerups)
    owned_tags = frozenset(tag for powerup in context.owned_powerups for tag in powerup.keywords)

    genome_primary, genome_secondary = _infer_from_genome(context.genome)
    primary = (
        _normalize_family(context.primary_doctrine_family)
        or _infer_primary_from_owned(context.owned_powerups)
        or genome_primary
        or _deterministic_house_seed(floor_number=context.floor_number, phase=context.phase)
    )
    secondary = (
        _normalize_family(context.secondary_doctrine_family)
        or (genome_secondary if genome_secondary != primary else None)
    )

    if secondary is None:
        possible = _HYBRID_PAIRS.get(primary, ())
        secondary = possible[0] if possible else None
    if secondary == primary:
        secondary = None

    return _BuildSignal(
        primary_family=primary,
        secondary_family=secondary,
        owned_families=owned_families,
        owned_tags=owned_tags,
        floor_number=max(1, context.floor_number),
        phase=context.phase,
    )


def _lineage_focus_strength(signal: _BuildSignal) -> float:
    family_strength = min(1.0, len(signal.owned_families) * 0.25)
    tag_strength = min(1.0, len(signal.owned_tags) * 0.08)
    return min(1.0, (family_strength + tag_strength) / 2)


def _category_mix_weights(signal: _BuildSignal) -> dict[OfferCategory, float]:
    focus = _lineage_focus_strength(signal)
    familiar = 0.38 + (0.30 * focus)
    hybrid = 0.30 + (0.15 if signal.secondary_family else 0.0)
    temptation = 0.32 - (0.22 * focus)
    if signal.floor_number <= 3:
        familiar += 0.18
        temptation -= 0.08
    elif signal.floor_number >= 7:
        hybrid += 0.07
        temptation += 0.06
    if signal.phase == "civil_war":
        temptation += 0.05

    raw = {
        "familiar_line": max(0.08, familiar),
        "hybrid_line": max(0.08, hybrid),
        "temptation": max(0.08, temptation),
    }
    total = sum(raw.values())
    return {category: value / total for category, value in raw.items()}  # type: ignore[return-value]


def _category_weight(
    powerup: Powerup,
    category: OfferCategory,
    signal: _BuildSignal,
    chosen_families: set[str],
) -> float:
    family = powerup.doctrine_family
    tags = set(powerup.keywords)
    shared_tags = len(tags & signal.owned_tags)
    novelty_bonus = 0.4 if family not in chosen_families else 0.0
    hybrid_targets = set(_HYBRID_PAIRS.get(signal.primary_family, ()))

    if category == "familiar_line":
        weight = 0.8
        if family == signal.primary_family:
            weight += 6.0
        if signal.floor_number <= 3 and "anchor" in tags:
            weight += 0.8
        weight += shared_tags * 0.8
        if powerup.crown_piece:
            weight *= 0.55
        return weight + novelty_bonus

    if category == "hybrid_line":
        weight = 0.6
        if family in hybrid_targets:
            weight += 6.4
        if signal.secondary_family and family == signal.secondary_family:
            weight += 4.8
        if family == signal.primary_family:
            weight += 0.4
        if shared_tags > 0:
            weight += shared_tags * 1.8
        if powerup.crown_piece:
            weight *= 0.65
        return weight + novelty_bonus

    weight = 0.5
    if family != signal.primary_family and (signal.secondary_family is None or family != signal.secondary_family):
        weight += 2.2
    if powerup.crown_piece:
        weight += 6.5
    if shared_tags == 0:
        weight += 0.5
    if signal.floor_number <= 3 and powerup.crown_piece:
        weight *= 0.6
    return weight + novelty_bonus


def _weighted_pick(
    rng: random.Random,
    candidates: list[Powerup],
    category: OfferCategory,
    signal: _BuildSignal,
    chosen_families: set[str],
) -> Powerup:
    raw_weights = [
        _category_weight(candidate, category, signal, chosen_families=chosen_families)
        for candidate in candidates
    ]
    weights = [weight if math.isfinite(weight) and weight > 0 else 0.0 for weight in raw_weights]
    if any(weight > 0 for weight in weights):
        return rng.choices(candidates, weights=weights, k=1)[0]

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
    categories: list[OfferCategory] = ["familiar_line", "hybrid_line", "temptation"]
    weights = [mix[category] for category in categories]

    for idx, category in enumerate(categories):
        if counts_by_category[category] >= 2:
            weights[idx] *= 0.5

    if signal.floor_number <= 3 and counts_by_category["familiar_line"] == 0:
        weights[categories.index("familiar_line")] *= 1.8
    if signal.floor_number >= 6 and counts_by_category["hybrid_line"] == 0:
        weights[categories.index("hybrid_line")] *= 1.4

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
    chosen_families: set[str] = set()

    for category in categories:
        remaining_pool = [powerup for powerup in pool if type(powerup) not in used_types]
        if not remaining_pool:
            break
        pick = _weighted_pick(rng, remaining_pool, category, signal, chosen_families=chosen_families)
        used_types.add(type(pick))
        chosen.append(GeneratedPowerupOffer(powerup=pick.clone(), category=category))
        chosen_families.add(pick.doctrine_family)

    while len(chosen) < count:
        fallback = rng.choice(pool).clone()
        chosen.append(GeneratedPowerupOffer(powerup=fallback, category="temptation"))

    return chosen


def generate_powerup_offers(
    count: int,
    rng: random.Random,
    context: PowerupOfferContext | None = None,
) -> list[Powerup]:
    return [entry.powerup for entry in generate_powerup_offer_set(count, rng, context)]
