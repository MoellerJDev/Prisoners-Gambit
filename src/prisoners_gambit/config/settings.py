from __future__ import annotations

from dataclasses import dataclass
import os


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    population_size: int = 12
    rounds_per_match: int = 6
    survivor_count: int = 6
    offers_per_floor: int = 5
    featured_matches_per_floor: int = 3
    genome_edit_offers_per_floor: int = 3
    floors: int = 20
    mutation_rate: float = 0.15
    descendant_mutation_bonus: float = 1.75
    seed: int | None = None

    auto_choose_powerups: bool = False
    auto_choose_round_actions: bool = False
    auto_choose_genome_edits: bool = False
    auto_choose_floor_vote: bool = False
    auto_choose_successors: bool = False

    log_level: str = "INFO"
    log_to_console: bool = True
    log_to_file: bool = False
    log_file: str = "prisoners_gambit.log"

    @classmethod
    def from_env(cls) -> "Settings":
        seed_raw = os.getenv("PG_SEED")
        return cls(
            population_size=int(os.getenv("PG_POPULATION_SIZE", "12")),
            rounds_per_match=int(os.getenv("PG_ROUNDS_PER_MATCH", "6")),
            survivor_count=int(os.getenv("PG_SURVIVOR_COUNT", "6")),
            offers_per_floor=int(os.getenv("PG_OFFERS_PER_FLOOR", "5")),
            featured_matches_per_floor=int(os.getenv("PG_FEATURED_MATCHES_PER_FLOOR", "3")),
            genome_edit_offers_per_floor=int(os.getenv("PG_GENOME_EDIT_OFFERS_PER_FLOOR", "3")),
            floors=int(os.getenv("PG_FLOORS", "20")),
            mutation_rate=float(os.getenv("PG_MUTATION_RATE", "0.15")),
            descendant_mutation_bonus=float(os.getenv("PG_DESCENDANT_MUTATION_BONUS", "1.75")),
            seed=int(seed_raw) if seed_raw is not None else None,
            auto_choose_powerups=_as_bool(os.getenv("PG_AUTO_CHOOSE_POWERUPS"), False),
            auto_choose_round_actions=_as_bool(os.getenv("PG_AUTO_CHOOSE_ROUND_ACTIONS"), False),
            auto_choose_genome_edits=_as_bool(os.getenv("PG_AUTO_CHOOSE_GENOME_EDITS"), False),
            auto_choose_floor_vote=_as_bool(os.getenv("PG_AUTO_CHOOSE_FLOOR_VOTE"), False),
            auto_choose_successors=_as_bool(os.getenv("PG_AUTO_CHOOSE_SUCCESSORS"), False),
            log_level=os.getenv("PG_LOG_LEVEL", "INFO"),
            log_to_console=_as_bool(os.getenv("PG_LOG_TO_CONSOLE"), True),
            log_to_file=_as_bool(os.getenv("PG_LOG_TO_FILE"), False),
            log_file=os.getenv("PG_LOG_FILE", "prisoners_gambit.log"),
        )
