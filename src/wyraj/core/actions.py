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
class UseItem(Action):
    item: int  # entity id from the actor's inventory


@dataclass(frozen=True)
class WieldItem(Action):
    item: int  # entity id from the actor's inventory
