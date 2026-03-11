from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._wildcard_subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        if event_name == "*":
            self._wildcard_subscribers.append(callback)
            return

        self._subscribers.setdefault(event_name, []).append(callback)

    def publish(self, event: Event) -> None:
        for callback in self._subscribers.get(event.name, []):
            callback(event)

        for callback in self._wildcard_subscribers:
            callback(event)