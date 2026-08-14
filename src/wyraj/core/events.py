"""Typed game events and the synchronous event bus.

Events carry facts, not text (spec §4.2). They snapshot what narration and
logging need (via EntityRef) so subscribers never reach back into the world.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from wyraj.core.ecs import Entity


@dataclass(frozen=True)
class EntityRef:
    """Snapshot of an entity's identity at emission time."""

    entity: Entity
    key: str  # content id, e.g. "bies"; "player" for the player
    name: str
    is_player: bool = False


class Outcome(Enum):
    HIT = "hit"
    MISS = "miss"
    CRIT = "crit"
    KILL = "kill"
    GRAZE = "graze"


@dataclass(frozen=True)
class GameEvent:
    pass


@dataclass(frozen=True)
class EntityMoved(GameEvent):
    actor: EntityRef
    from_pos: tuple[int, int]
    to_pos: tuple[int, int]


@dataclass(frozen=True)
class MoveBlocked(GameEvent):
    actor: EntityRef
    to_pos: tuple[int, int]


@dataclass(frozen=True)
class AttackResolved(GameEvent):
    attacker: EntityRef
    defender: EntityRef
    weapon: EntityRef | None
    damage: int
    outcome: Outcome
    defender_hp_frac: float


@dataclass(frozen=True)
class EntityDied(GameEvent):
    entity: EntityRef


@dataclass(frozen=True)
class ItemPickedUp(GameEvent):
    actor: EntityRef
    item: EntityRef


@dataclass(frozen=True)
class ItemUsed(GameEvent):
    actor: EntityRef
    item: EntityRef
    effect: str
    power: int


@dataclass(frozen=True)
class ItemWielded(GameEvent):
    actor: EntityRef
    item: EntityRef


@dataclass(frozen=True)
class HungerChanged(GameEvent):
    actor: EntityRef
    band: str  # "sated" | "hungry" | "starving"


@dataclass(frozen=True)
class StarvationHit(GameEvent):
    actor: EntityRef
    damage: int
    hp_frac: float


@dataclass(frozen=True)
class TurnEnded(GameEvent):
    turn: int


E = TypeVar("E", bound=GameEvent)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[GameEvent], list[Callable[[Any], None]]] = {}
        self._catch_all: list[Callable[[GameEvent], None]] = []

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable[[GameEvent], None]) -> None:
        """Receive every event — used by the run logger and golden tests."""
        self._catch_all.append(handler)

    def publish(self, event: GameEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)
        for handler in self._catch_all:
            handler(event)
