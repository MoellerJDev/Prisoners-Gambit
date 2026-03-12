import random

from prisoners_gambit.core.offer_guidance import OfferDoctrineGuidance, guidance_for_genome_edit, guidance_for_powerup
from prisoners_gambit.systems import genome_offers as genome_offers_module
from prisoners_gambit.systems import offers as offers_module
from prisoners_gambit.systems.genome_offers import generate_genome_edit_offers
from prisoners_gambit.systems.offers import generate_powerup_offers


class _FirstChoiceRng:
    def choice(self, seq):
        return seq[0]


class _FakePowerup:
    name = "Fake"
    description = "Fake"

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


def test_powerup_offer_novelty_prioritizes_doctrine_before_phase(monkeypatch) -> None:
    def guidance_for(powerup: _FakePowerup) -> OfferDoctrineGuidance:
        mapping = {
            "P1": OfferDoctrineGuidance("trust / reciprocity", "b", "t", "ecosystem survival", "s"),
            "P2": OfferDoctrineGuidance("coercion / control", "b", "t", "ecosystem survival", "s"),
            "P3": OfferDoctrineGuidance("trust / reciprocity", "b", "t", "civil-war readiness", "s"),
        }
        return mapping[powerup.name]

    monkeypatch.setattr(offers_module, "build_powerup_pool", lambda: [_P1(), _P3(), _P2()])
    monkeypatch.setattr(offers_module, "guidance_for_powerup", guidance_for)

    offers = offers_module.generate_powerup_offers(2, _FirstChoiceRng())

    assert [offer.name for offer in offers] == ["P1", "P2"]


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

    offers = genome_offers_module.generate_genome_edit_offers(2, _FirstChoiceRng())

    assert [offer.name for offer in offers] == ["E1", "E2"]


def test_powerup_offer_generation_is_deterministic_for_seed() -> None:
    names1 = [offer.name for offer in generate_powerup_offers(3, random.Random(77))]
    names2 = [offer.name for offer in generate_powerup_offers(3, random.Random(77))]

    assert names1 == names2


def test_genome_offer_generation_is_deterministic_for_seed() -> None:
    names1 = [offer.name for offer in generate_genome_edit_offers(3, random.Random(77))]
    names2 = [offer.name for offer in generate_genome_edit_offers(3, random.Random(77))]

    assert names1 == names2
