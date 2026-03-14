import random, pytest

from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.strategy import StrategyGenome
from prisoners_gambit.systems.progression import ProgressionEngine


def make_agent(name: str, *, is_player: bool = False) -> Agent:
    genome = StrategyGenome(
        first_move=0,
        response_table={
            (0, 0): 0,
            (0, 1): 0,
            (1, 0): 0,
            (1, 1): 0,
        },
        noise=0.0,
    )
    return Agent(
        name=name,
        genome=genome,
        is_player=is_player,
        lineage_id=1 if is_player else None,
    )


def test_floor_one_config_is_expected_baseline() -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    config = engine.build_floor_config(1)

    assert config.floor_number == 1
    assert config.rounds_per_match == 6
    assert config.ai_powerup_chance == pytest.approx(0.25)
    assert config.featured_matches == 3
    assert config.referendum_reward == 3
    assert config.label == "Opening Tables"


def test_floor_labels_change_at_expected_boundaries() -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    assert engine.build_floor_config(5).label == "Opening Tables"
    assert engine.build_floor_config(6).label == "Calculated Risk"
    assert engine.build_floor_config(10).label == "Calculated Risk"
    assert engine.build_floor_config(11).label == "Knife's Edge"
    assert engine.build_floor_config(15).label == "Knife's Edge"
    assert engine.build_floor_config(16).label == "Endgame Spiral"


def test_rounds_per_match_scales_every_three_floors() -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    assert engine.build_floor_config(1).rounds_per_match == 6
    assert engine.build_floor_config(3).rounds_per_match == 6
    assert engine.build_floor_config(4).rounds_per_match == 7
    assert engine.build_floor_config(7).rounds_per_match == 8
    assert engine.build_floor_config(10).rounds_per_match == 9


def test_featured_matches_scale_but_are_capped() -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    assert engine.build_floor_config(1).featured_matches == 3
    assert engine.build_floor_config(5).featured_matches == 3
    assert engine.build_floor_config(6).featured_matches == 4
    assert engine.build_floor_config(11).featured_matches == 5
    assert engine.build_floor_config(50).featured_matches == 5


def test_referendum_reward_scales_every_four_floors() -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    assert engine.build_floor_config(1).referendum_reward == 3
    assert engine.build_floor_config(4).referendum_reward == 3
    assert engine.build_floor_config(5).referendum_reward == 4
    assert engine.build_floor_config(9).referendum_reward == 5


def test_ai_powerup_chance_scales_and_caps_at_point_seven_five() -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    assert engine.build_floor_config(1).ai_powerup_chance == pytest.approx(0.25)
    assert engine.build_floor_config(2).ai_powerup_chance == pytest.approx(0.28)
    assert engine.build_floor_config(10).ai_powerup_chance == min(0.25 + 9 * 0.03, 0.75)
    assert engine.build_floor_config(100).ai_powerup_chance == pytest.approx(0.75)


def test_grant_ai_powerups_gives_none_when_chance_is_zero(monkeypatch) -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    player = make_agent("You", is_player=True)
    ai_a = make_agent("A")
    ai_b = make_agent("B")
    survivors = [player, ai_a, ai_b]

    class FloorConfig:
        ai_powerup_chance = 0.0

    def fake_build_powerup_pool():
        raise AssertionError("Should not build powerup pool when chance is 0.0")

    monkeypatch.setattr("prisoners_gambit.systems.progression.build_powerup_pool", fake_build_powerup_pool)

    engine.grant_ai_powerups(survivors=survivors, player=player, floor_config=FloorConfig())

    assert player.powerups == []
    assert ai_a.powerups == []
    assert ai_b.powerups == []


def test_grant_ai_powerups_gives_all_non_player_survivors_when_chance_is_one(monkeypatch) -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    player = make_agent("You", is_player=True)
    ai_a = make_agent("A")
    ai_b = make_agent("B")
    survivors = [player, ai_a, ai_b]

    from prisoners_gambit.core.powerups import OpeningGambit, TrustDividend

    monkeypatch.setattr(
        "prisoners_gambit.systems.progression.build_powerup_pool",
        lambda: [OpeningGambit(bonus=1), TrustDividend(bonus=1)],
    )

    class FloorConfig:
        ai_powerup_chance = 1.0

    engine.grant_ai_powerups(survivors=survivors, player=player, floor_config=FloorConfig())

    assert player.powerups == []
    assert len(ai_a.powerups) == 1
    assert len(ai_b.powerups) == 1


def test_grant_ai_powerups_never_grants_to_player_even_with_certain_chance(monkeypatch) -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    player = make_agent("You", is_player=True)
    survivors = [player]

    from prisoners_gambit.core.powerups import OpeningGambit

    monkeypatch.setattr(
        "prisoners_gambit.systems.progression.build_powerup_pool",
        lambda: [OpeningGambit(bonus=1)],
    )

    class FloorConfig:
        ai_powerup_chance = 1.0

    engine.grant_ai_powerups(survivors=survivors, player=player, floor_config=FloorConfig())

    assert player.powerups == []


def test_grant_ai_powerups_skips_duplicate_powerup_types(monkeypatch) -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    player = make_agent("You", is_player=True)
    ai = make_agent("A")
    from prisoners_gambit.core.powerups import TrustDividend

    ai.powerups.append(TrustDividend(bonus=1))

    class FloorConfig:
        ai_powerup_chance = 1.0

    monkeypatch.setattr(
        "prisoners_gambit.systems.progression.build_powerup_pool",
        lambda: [TrustDividend(bonus=2), TrustDividend(bonus=3)],
    )

    engine.grant_ai_powerups(survivors=[player, ai], player=player, floor_config=FloorConfig())

    trust_dividends = [powerup for powerup in ai.powerups if isinstance(powerup, TrustDividend)]
    assert len(trust_dividends) == 1


def test_grant_ai_powerups_respects_max_powerup_cap(monkeypatch) -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    player = make_agent("You", is_player=True)
    ai = make_agent("A")
    ai.powerups.extend(
        [
            type("P1", (), {"name": "P1"})(),
            type("P2", (), {"name": "P2"})(),
            type("P3", (), {"name": "P3"})(),
        ]
    )

    class FloorConfig:
        ai_powerup_chance = 1.0

    from prisoners_gambit.core.powerups import OpeningGambit

    monkeypatch.setattr(
        "prisoners_gambit.systems.progression.build_powerup_pool",
        lambda: [OpeningGambit(bonus=1)],
    )

    before = len(ai.powerups)
    engine.grant_ai_powerups(survivors=[player, ai], player=player, floor_config=FloorConfig())

    assert len(ai.powerups) == before


def test_grant_ai_powerups_old_retry_budget_can_still_miss_valid_later_offer() -> None:
    from prisoners_gambit.core.powerups import BlocPolitics, OpeningGambit, TrustDividend

    def old_policy_would_grant(rolls):
        owned = [TrustDividend(bonus=1), OpeningGambit(bonus=1)]
        attempts = 3
        for powerup in rolls[:attempts]:
            if any(type(existing) is type(powerup) for existing in owned):
                continue
            return True
        return False

    duplicate_heavy_rolls = [
        TrustDividend(bonus=2),
        OpeningGambit(bonus=2),
        TrustDividend(bonus=3),
        BlocPolitics(bonus=2),
    ]

    assert old_policy_would_grant(duplicate_heavy_rolls) is False


def test_grant_ai_powerups_grants_valid_non_duplicate_from_filtered_pool(monkeypatch) -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    player = make_agent("You", is_player=True)
    ai = make_agent("A")
    from prisoners_gambit.core.powerups import BlocPolitics, OpeningGambit, TrustDividend

    ai.powerups.extend([TrustDividend(bonus=1), OpeningGambit(bonus=1)])

    class FloorConfig:
        ai_powerup_chance = 1.0

    monkeypatch.setattr(
        "prisoners_gambit.systems.progression.build_powerup_pool",
        lambda: [
            TrustDividend(bonus=2),
            OpeningGambit(bonus=2),
            TrustDividend(bonus=3),
            BlocPolitics(bonus=2),
        ],
    )

    engine.grant_ai_powerups(survivors=[player, ai], player=player, floor_config=FloorConfig())

    assert any(isinstance(powerup, BlocPolitics) for powerup in ai.powerups)


def test_grant_ai_powerups_skips_when_all_powerup_types_are_already_owned(monkeypatch) -> None:
    engine = ProgressionEngine(rng=random.Random(1), offers_per_floor=5, featured_matches_per_floor=3)

    player = make_agent("You", is_player=True)
    ai = make_agent("A")
    from prisoners_gambit.content.powerup_templates import build_powerup_pool

    owned_types = {type(powerup) for powerup in build_powerup_pool()}
    ai.powerups.extend(powerup_type() for powerup_type in owned_types)

    class FloorConfig:
        ai_powerup_chance = 1.0

    monkeypatch.setattr("prisoners_gambit.systems.progression.MAX_AI_POWERUPS", 999)

    before = len(ai.powerups)
    engine.grant_ai_powerups(survivors=[player, ai], player=player, floor_config=FloorConfig())

    assert len(ai.powerups) == before
