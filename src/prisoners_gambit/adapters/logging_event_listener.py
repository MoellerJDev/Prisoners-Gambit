from __future__ import annotations

import logging

from prisoners_gambit.core.events import Event


class LoggingEventListener:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def __call__(self, event: Event) -> None:
        self.logger.debug(
            "Domain event emitted | name=%s | payload=%s",
            event.name,
            event.payload,
        )