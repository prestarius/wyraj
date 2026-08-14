"""Narration engine: subscribes to the event bus, turns facts into prose.

M0 pipeline: GameEvent → Narrator.compose() → NarrationLine → sinks.
ContextEnricher and TurnComposer (coalescing) arrive in M1.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from wyraj.core.events import EventBus, GameEvent


@dataclass(frozen=True)
class NarrationLine:
    text: str
    importance: str = "normal"  # "normal" | "high"


class Narrator(Protocol):
    def compose(self, event: GameEvent) -> list[NarrationLine]: ...


class NarrationEngine:
    def __init__(self, bus: EventBus, narrator: Narrator) -> None:
        self.narrator = narrator
        self.lines: list[NarrationLine] = []
        self._sinks: list[Callable[[NarrationLine], None]] = []
        bus.subscribe_all(self._on_event)

    def add_sink(self, sink: Callable[[NarrationLine], None]) -> None:
        """UI panes register here to receive lines as they are composed."""
        self._sinks.append(sink)

    def _on_event(self, event: GameEvent) -> None:
        for line in self.narrator.compose(event):
            self.lines.append(line)
            for sink in self._sinks:
                sink(line)
