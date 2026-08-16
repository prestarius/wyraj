"""Narration engine: subscribes to the event bus, turns facts into prose.

M1 pipeline: GameEvent → enrich (context tags) → buffer → on TurnEnded the
TurnComposer flushes the whole turn as one composed paragraph (spec §5.2:
coalescing is the single biggest quality lever over classic roguelike logs).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from wyraj.core.events import EventBus, GameEvent, TurnEnded

# Maps an event to its context tags at capture time.
Enricher = Callable[[GameEvent], frozenset[str]]

NO_TAGS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class NarrationLine:
    text: str
    importance: str = "normal"  # "normal" | "high"
    category: str = "ambient"  # "combat" | "lore" | "loot" | "ambient" — UI tint only


class Narrator(Protocol):
    def compose(self, event: GameEvent, tags: frozenset[str] = ...) -> list[NarrationLine]: ...

    def compose_turn(
        self, batch: list[tuple[GameEvent, frozenset[str]]]
    ) -> list[NarrationLine]: ...


class NarrationEngine:
    def __init__(self, bus: EventBus, narrator: Narrator, enricher: Enricher | None = None) -> None:
        self.narrator = narrator
        self.enricher = enricher
        self.lines: list[NarrationLine] = []
        self._sinks: list[Callable[[NarrationLine], None]] = []
        self._buffer: list[tuple[GameEvent, frozenset[str]]] = []
        bus.subscribe_all(self._on_event)

    def add_sink(self, sink: Callable[[NarrationLine], None]) -> None:
        """UI panes register here to receive composed paragraphs."""
        self._sinks.append(sink)

    def _on_event(self, event: GameEvent) -> None:
        if isinstance(event, TurnEnded):
            self._flush()
            return
        tags = self.enricher(event) if self.enricher else NO_TAGS
        self._buffer.append((event, tags))

    def _flush(self) -> None:
        for line in self.narrator.compose_turn(self._buffer):
            self.lines.append(line)
            for sink in self._sinks:
                sink(line)
        self._buffer.clear()
