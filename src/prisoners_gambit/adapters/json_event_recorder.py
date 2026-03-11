from __future__ import annotations

import json
from pathlib import Path

from prisoners_gambit.core.events import Event


class JsonEventRecorder:
    def __init__(self, output_path: str = "events/run_events.jsonl") -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: Event) -> None:
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"name": event.name, "payload": event.payload}) + "\n")