import random

from prisoners_gambit.core.offer_guidance import guidance_for_genome_edit, guidance_for_powerup
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import generate_powerup_offers


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
