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
    # Where the body fell (M6 drops); None for positionless deaths.
    position: tuple[int, int] | None = None
    depth: int = 0


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
class ItemWorn(GameEvent):
    actor: EntityRef
    item: EntityRef


@dataclass(frozen=True)
class ItemUnequipped(GameEvent):
    actor: EntityRef
    item: EntityRef


@dataclass(frozen=True)
class QuickslotBound(GameEvent):
    actor: EntityRef
    item: EntityRef
    index: int  # 0-based slot


@dataclass(frozen=True)
class QuickslotCleared(GameEvent):
    actor: EntityRef
    index: int


@dataclass(frozen=True)
class QuickslotUsed(GameEvent):
    actor: EntityRef
    item: EntityRef
    index: int


@dataclass(frozen=True)
class QuickslotRefilled(GameEvent):
    actor: EntityRef
    item: EntityRef
    index: int


@dataclass(frozen=True)
class BliznaEarned(GameEvent):
    """Survived a dying state (<10% HP): a scar the run will keep (M7 §2.5)."""

    actor: EntityRef
    count: int  # blizny total, this one included


@dataclass(frozen=True)
class WeaponNamed(GameEvent):
    """A weapon earned its epithet after enough kills of one species (M7 §6.2)."""

    actor: EntityRef
    weapon: EntityRef
    species: str


@dataclass(frozen=True)
class WeaponRecognized(GameEvent):
    """The dziad greets a named weapon by its name (M7 §6.2, M6 bridge)."""

    weapon: EntityRef
    species: str


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
class StatusApplied(GameEvent):
    actor: EntityRef
    kind: str
    duration: int


@dataclass(frozen=True)
class StatusTick(GameEvent):
    actor: EntityRef
    kind: str
    damage: int
    hp_frac: float


@dataclass(frozen=True)
class StatusExpired(GameEvent):
    actor: EntityRef
    kind: str


@dataclass(frozen=True)
class LightExtinguished(GameEvent):
    actor: EntityRef


@dataclass(frozen=True)
class MetaTransaction(GameEvent):
    """A defined mutation of the persistent meta-state (M6 spec §2.3)."""

    kind: str  # e.g. "bank", "stash_deposit", "purchase", "offering", "death"
    detail: str = ""


@dataclass(frozen=True)
class CraneSummonStarted(GameEvent):
    actor: EntityRef
    turns: int


@dataclass(frozen=True)
class CraneSummonInterrupted(GameEvent):
    actor: EntityRef
    reason: str  # "moved" | "damage"


@dataclass(frozen=True)
class CraneSummonCompleted(GameEvent):
    actor: EntityRef
    from_depth: int


@dataclass(frozen=True)
class CraneRefused(GameEvent):
    actor: EntityRef
    reason: str  # "watched" | "no_sky" | "in_village"


@dataclass(frozen=True)
class ZnamiePlaced(GameEvent):
    depth: int
    position: tuple[int, int]


@dataclass(frozen=True)
class CraneReturn(GameEvent):
    actor: EntityRef
    depth: int


@dataclass(frozen=True)
class StashOpened(GameEvent):
    actor: EntityRef


@dataclass(frozen=True)
class StashDeposited(GameEvent):
    item: EntityRef


@dataclass(frozen=True)
class StashWithdrawn(GameEvent):
    item: EntityRef
    heirloom: bool = False


@dataclass(frozen=True)
class StashUpgraded(GameEvent):
    slots: int
    price: int


@dataclass(frozen=True)
class HeirloomWielded(GameEvent):
    actor: EntityRef
    item: EntityRef


@dataclass(frozen=True)
class ShrineVisited(GameEvent):
    actor: EntityRef
    god: str


@dataclass(frozen=True)
class DziadRecognized(GameEvent):
    """The dziad knows this soul — or one very like it (rep ≥ 3)."""

    reputation: int


@dataclass(frozen=True)
class OfferingMade(GameEvent):
    actor: EntityRef
    god: str
    cost: int


@dataclass(frozen=True)
class TalkedTo(GameEvent):
    villager: EntityRef
    role: str


@dataclass(frozen=True)
class Rested(GameEvent):
    actor: EntityRef


@dataclass(frozen=True)
class CoinsPicked(GameEvent):
    actor: EntityRef
    amount: int
    purse_total: int


@dataclass(frozen=True)
class CoinsBanked(GameEvent):
    amount: int
    wallet_total: int


@dataclass(frozen=True)
class ItemBought(GameEvent):
    actor: EntityRef
    item: EntityRef
    price: int


@dataclass(frozen=True)
class ItemSold(GameEvent):
    actor: EntityRef
    item: EntityRef
    price: int


@dataclass(frozen=True)
class LevelChanged(GameEvent):
    depth: int  # level arrived at
    direction: str  # "down" | "up"


@dataclass(frozen=True)
class LoreDiscovered(GameEvent):
    """First time the player lays eyes on a kind of creature."""

    entity: EntityRef


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
