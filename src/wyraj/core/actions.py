"""Player/AI intents. The engine turns these into system calls and events."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    pass


@dataclass(frozen=True)
class Move(Action):
    dx: int
    dy: int


@dataclass(frozen=True)
class Wait(Action):
    pass


@dataclass(frozen=True)
class Get(Action):
    """Pick up the item on the current tile."""


@dataclass(frozen=True)
class Rest(Action):
    """Sleep it off — only in the safety of the wieś."""


@dataclass(frozen=True)
class TradeItems(Action):
    trader: int  # trader entity
    give: int  # item entity from the player's inventory
    take: int  # item entity from the trader's stock


@dataclass(frozen=True)
class Descend(Action):
    """Take stairs down (must be standing on them)."""


@dataclass(frozen=True)
class Ascend(Action):
    """Take stairs up (must be standing on them)."""


@dataclass(frozen=True)
class UseItem(Action):
    item: int  # entity id from the actor's inventory


@dataclass(frozen=True)
class WieldItem(Action):
    item: int  # entity id from the actor's inventory


@dataclass(frozen=True)
class WearItem(Action):
    item: int  # entity id from the actor's inventory
