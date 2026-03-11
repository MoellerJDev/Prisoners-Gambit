from __future__ import annotations

import logging
import secrets

from prisoners_gambit.adapters.logging_event_listener import LoggingEventListener
from prisoners_gambit.app.service_container import build_run_application
from prisoners_gambit.config.logging_config import configure_logging
from prisoners_gambit.config.settings import Settings

logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings.from_env()

    if settings.seed is None:
        settings.seed = secrets.randbelow(2**63)

    configure_logging(settings)

    logger.info("Bootstrapping Prisoner's Gambit")
    logger.info("Resolved run seed: %s", settings.seed)
    logger.debug("Loaded settings: %s", settings)

    app = build_run_application(settings)
    app.event_bus.subscribe("*", LoggingEventListener(logger=logger))
    app.run()