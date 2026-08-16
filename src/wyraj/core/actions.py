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
class BuyItem(Action):
    trader: int  # merchant entity
    item: int  # item entity from the merchant's stock


@dataclass(frozen=True)
class SellItem(Action):
    trader: int  # merchant entity
    item: int  # item entity from the player's inventory


@dataclass(frozen=True)
class DepositItem(Action):
    item: int  # item entity from the player's inventory


@dataclass(frozen=True)
class WithdrawStash(Action):
    index: int  # slot index in the meta stash


@dataclass(frozen=True)
class UpgradeStash(Action):
    pass


@dataclass(frozen=True)
class MakeOffering(Action):
    god: str  # "perun" | "weles"


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
    item: int


@dataclass(frozen=True)
class UnequipSlot(Action):
    slot: str  # "weapon" | "torso" | "head" | "amulet" | "feet"


@dataclass(frozen=True)
class BindQuickslot(Action):
    index: int  # 0-based
    item: int


@dataclass(frozen=True)
class ClearQuickslot(Action):
    index: int


@dataclass(frozen=True)
class UseQuickslot(Action):
    index: int  # entity id from the actor's inventory
