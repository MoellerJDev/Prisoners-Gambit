import random

from prisoners_gambit.core.genome_edits import FortressDoctrine, TyrantDoctrine, WildcardDoctrine
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import generate_powerup_offers


def test_genome_offers_include_a_pivot_doctrine_when_count_is_three_plus() -> None:
    offers = generate_genome_edit_offers(3, random.Random(1))

    assert any(isinstance(offer, (FortressDoctrine, TyrantDoctrine, WildcardDoctrine)) for offer in offers)


def test_powerup_offers_keep_requested_count_with_divergence_bias() -> None:
    offers = generate_powerup_offers(4, random.Random(2))

    assert len(offers) == 4
    assert len({offer.name for offer in offers}) >= 3
