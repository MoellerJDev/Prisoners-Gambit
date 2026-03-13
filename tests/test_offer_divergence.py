import random

from prisoners_gambit.content.powerup_templates import build_powerup_pool
from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.offer_guidance import OfferDoctrineGuidance, guidance_for_genome_edit, guidance_for_powerup
from prisoners_gambit.core.powerups import CoerciveControl, ComplianceDividend, SpiteEngine, TrustDividend
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems import genome_offers as genome_offers_module
from prisoners_gambit.systems import offers as offers_module
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import (
    PowerupOfferContext,
    derive_doctrine_state,
    generate_powerup_offer_set,
    generate_powerup_offers,
    seed_house_doctrine,
)


class _FakePowerup:
    name = "Fake"
    description = "Fake"
    keywords = ()

    def clone(self):
        return type(self)()


class _P1(_FakePowerup):
    name = "P1"


class _P2(_FakePowerup):
    name = "P2"


class _P3(_FakePowerup):
    name = "P3"


class _FakeEdit:
    name = "Fake"
    description = "Fake"

    def clone(self):
        return type(self)()


class _E1(_FakeEdit):
    name = "E1"


class _E2(_FakeEdit):
    name = "E2"


class _E3(_FakeEdit):
    name = "E3"


def test_genome_offers_bias_toward_directional_doctrine_choices() -> None:
    offers = generate_genome_edit_offers(3, random.Random(1))
    vectors = {guidance_for_genome_edit(offer).doctrine_vector for offer in offers}

    assert len(offers) == 3
    assert len(vectors) >= 2


def test_powerup_offers_keep_requested_count_with_divergence_bias() -> None:
    offers = generate_powerup_offers(4, random.Random(2))

    assert len(offers) == 4
    assert len({offer.name for offer in offers}) >= 3


def test_powerup_offers_bias_toward_directional_doctrine_choices() -> None:
    offers = generate_powerup_offers(3, random.Random(1))
    vectors = {guidance_for_powerup(offer).doctrine_vector for offer in offers}

    assert len(vectors) >= 2


def test_genome_offers_bias_toward_phase_lane_diversity() -> None:
    offers = generate_genome_edit_offers(3, random.Random(3))
    phases = {guidance_for_genome_edit(offer).phase_support for offer in offers}

    assert len(phases) >= 2


def test_powerup_offers_bias_toward_phase_lane_diversity() -> None:
    offers = generate_powerup_offers(3, random.Random(4))
    phases = {guidance_for_powerup(offer).phase_support for offer in offers}

    assert len(phases) >= 2


def test_weighted_pick_uses_probabilistic_weights_not_argmax(monkeypatch) -> None:
    weights = {"P1": 100.0, "P2": 1.0, "P3": 1.0}

    monkeypatch.setattr(
        offers_module,
        "_category_weight",
        lambda powerup, category, signal, chosen_families: weights[powerup.name],
    )

    picks = []
    for seed in range(250):
        picked = offers_module._weighted_pick(  # pylint: disable=protected-access
            random.Random(seed),
            [_P1(), _P2(), _P3()],
            "familiar_line",
            offers_module._signal_from_context(None),  # pylint: disable=protected-access
            chosen_families=set(),
        )
        picks.append(picked.name)

    assert "P1" in picks
    assert any(name != "P1" for name in picks)




def test_weighted_pick_falls_back_when_all_weights_invalid(monkeypatch) -> None:
    monkeypatch.setattr(
        offers_module,
        "_category_weight",
        lambda powerup, category, signal, chosen_families: float("nan"),
    )

    picks = [
        offers_module._weighted_pick(  # pylint: disable=protected-access
            random.Random(seed),
            [_P1(), _P2(), _P3()],
            "familiar_line",
            offers_module._signal_from_context(None),  # pylint: disable=protected-access
            chosen_families=set(),
        ).name
        for seed in range(12)
    ]

    assert set(picks).issubset({"P1", "P2", "P3"})
    assert len(set(picks)) > 1

def test_genome_offer_novelty_uses_phase_as_secondary_tiebreaker(monkeypatch) -> None:
    def guidance_for(edit: _FakeEdit) -> OfferDoctrineGuidance:
        mapping = {
            "E1": OfferDoctrineGuidance("trust / reciprocity", "b", "t", "ecosystem survival", "s"),
            "E2": OfferDoctrineGuidance("trust / reciprocity", "b", "t", "civil-war readiness", "s"),
            "E3": OfferDoctrineGuidance("trust / reciprocity", "b", "t", "ecosystem survival", "s"),
        }
        return mapping[edit.name]

    monkeypatch.setattr(genome_offers_module, "build_genome_edit_pool", lambda: [_E1(), _E3(), _E2()])
    monkeypatch.setattr(genome_offers_module, "guidance_for_genome_edit", guidance_for)

    offers = genome_offers_module.generate_genome_edit_offers(2, random.Random(0))

    assert offers[1].name == "E2"
    assert offers[0].name in {"E1", "E3"}


def test_powerup_offer_generation_is_deterministic_for_seed() -> None:
    names1 = [offer.name for offer in generate_powerup_offers(3, random.Random(77))]
    names2 = [offer.name for offer in generate_powerup_offers(3, random.Random(77))]

    assert names1 == names2


def test_genome_offer_generation_is_deterministic_for_seed() -> None:
    names1 = [offer.name for offer in generate_genome_edit_offers(3, random.Random(77))]
    names2 = [offer.name for offer in generate_genome_edit_offers(3, random.Random(77))]

    assert names1 == names2


def test_offer_categories_show_variety_without_forced_single_pattern() -> None:
    context = PowerupOfferContext(owned_powerups=(CoerciveControl(), ComplianceDividend(bonus=2)), floor_number=6, phase="civil_war")

    category_patterns = [
        tuple(entry.category for entry in generate_powerup_offer_set(3, random.Random(seed), context=context))
        for seed in range(80)
    ]

    assert len(set(category_patterns)) >= 4
    assert any(len(set(pattern)) == 3 for pattern in category_patterns)
    assert any(len(set(pattern)) < 3 for pattern in category_patterns)


def test_control_lineage_gets_more_relevant_control_synergy_than_flat_random() -> None:
    context = PowerupOfferContext(
        owned_powerups=(CoerciveControl(), ComplianceDividend(bonus=2), SpiteEngine(bonus=2)),
        genome=StrategyGenome(first_move=DEFECT, response_table={(COOPERATE, COOPERATE): COOPERATE, (COOPERATE, DEFECT): DEFECT, (DEFECT, COOPERATE): DEFECT, (DEFECT, DEFECT): DEFECT}, noise=0.03),
        floor_number=8,
        phase="civil_war",
    )
    control_tags = {"creates_force", "rewards_force", "retaliation_payoff"}

    weighted_hits = 0
    flat_hits = 0
    for seed in range(150):
        weighted_offers = generate_powerup_offers(3, random.Random(seed), context=context)
        flat_rng = random.Random(seed)
        flat_pool = build_powerup_pool()
        flat_offers = [flat_rng.choice(flat_pool).clone() for _ in range(3)]
        weighted_hits += sum(bool(set(offer.keywords) & control_tags) for offer in weighted_offers)
        flat_hits += sum(bool(set(offer.keywords) & control_tags) for offer in flat_offers)

    assert weighted_hits > flat_hits


def test_offer_identity_is_still_randomized_across_seeds_for_same_build() -> None:
    context = PowerupOfferContext(owned_powerups=(TrustDividend(bonus=2),), floor_number=3, phase="ecosystem")

    names_per_seed = {
        tuple(offer.name for offer in generate_powerup_offers(3, random.Random(seed), context=context))
        for seed in range(6)
    }

    assert len(names_per_seed) > 1


def test_powerup_pool_has_doctrine_family_for_all_powerups() -> None:
    pool = build_powerup_pool()

    assert pool
    assert all(getattr(powerup, "doctrine_family", None) in {"trust", "control", "retaliation", "opportunist", "referendum", "chaos"} for powerup in pool)


def test_hybrid_pair_support_trust_to_opportunist() -> None:
    context = PowerupOfferContext(
        owned_powerups=(TrustDividend(bonus=2),),
        floor_number=5,
        phase="ecosystem",
        primary_doctrine_family="trust",
        secondary_doctrine_family="opportunist",
    )

    hybrid_hits = 0
    for seed in range(120):
        offers = generate_powerup_offer_set(3, random.Random(seed), context=context)
        hybrid_hits += sum(1 for entry in offers if entry.category == "hybrid_line" and entry.powerup.doctrine_family == "opportunist")

    assert hybrid_hits > 0


def test_hybrid_pair_support_control_to_retaliation() -> None:
    context = PowerupOfferContext(
        owned_powerups=(CoerciveControl(),),
        floor_number=6,
        phase="civil_war",
        primary_doctrine_family="control",
        secondary_doctrine_family="retaliation",
    )

    hybrid_hits = 0
    for seed in range(120):
        offers = generate_powerup_offer_set(3, random.Random(seed), context=context)
        hybrid_hits += sum(1 for entry in offers if entry.category == "hybrid_line" and entry.powerup.doctrine_family == "retaliation")

    assert hybrid_hits > 0


def test_crown_piece_is_seeded_rare_and_non_guaranteed() -> None:
    context = PowerupOfferContext(owned_powerups=(TrustDividend(bonus=1),), floor_number=5, phase="ecosystem")
    runs_with_crown = 0
    for seed in range(200):
        offers = generate_powerup_offers(3, random.Random(seed), context=context)
        if any(powerup.crown_piece for powerup in offers):
            runs_with_crown += 1

    assert runs_with_crown > 0
    assert runs_with_crown < 200


def test_primary_and_secondary_doctrine_influence_offer_mix() -> None:
    trust_context = PowerupOfferContext(floor_number=4, primary_doctrine_family="trust", secondary_doctrine_family="opportunist")
    control_context = PowerupOfferContext(floor_number=4, primary_doctrine_family="control", secondary_doctrine_family="retaliation")

    trust_trust_hits = 0
    control_trust_hits = 0
    for seed in range(100):
        trust_offers = generate_powerup_offers(3, random.Random(seed), context=trust_context)
        control_offers = generate_powerup_offers(3, random.Random(seed), context=control_context)
        trust_trust_hits += sum(1 for offer in trust_offers if offer.doctrine_family == "trust")
        control_trust_hits += sum(1 for offer in control_offers if offer.doctrine_family == "trust")

    assert trust_trust_hits > control_trust_hits


def test_house_doctrine_seed_is_deterministic_and_intentional() -> None:
    a = seed_house_doctrine(seed=17, floor_number=1, phase="ecosystem")
    b = seed_house_doctrine(seed=17, floor_number=1, phase="ecosystem")
    c = seed_house_doctrine(seed=18, floor_number=1, phase="ecosystem")

    assert a == b
    assert a in {"trust", "control", "retaliation", "opportunist", "referendum", "chaos"}
    assert a != c


def test_doctrine_state_tracking_is_not_pick_order_dependent() -> None:
    house = "trust"
    forward = derive_doctrine_state(
        owned_powerups=(CoerciveControl(), TrustDividend(), CoerciveControl(), SpiteEngine()),
        genome=None,
        house_doctrine_family=house,
    )
    reverse = derive_doctrine_state(
        owned_powerups=(SpiteEngine(), CoerciveControl(), TrustDividend(), CoerciveControl()),
        genome=None,
        house_doctrine_family=house,
    )

    assert forward == reverse
    assert forward.primary_doctrine_family == "control"
    assert forward.secondary_doctrine_family in {"retaliation", "trust"}
