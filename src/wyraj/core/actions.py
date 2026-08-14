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
