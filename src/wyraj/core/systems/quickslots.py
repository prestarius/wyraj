"""M7 quickslots (spec §5): bind by item key, stack-aware, auto-refilling.

Bindings live in the `Quickslots` component as item *keys*, not entity ids —
using the last of a stack leaves the slot bound-but-empty, and any identical
item entering the pack makes the key live again ("auto-refill" is inherent;
the knob only decides whether an emptied slot unbinds instead).
"""

from wyraj.core.components import Inventory, Item, Quickslots
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EventBus, QuickslotBound, QuickslotCleared, QuickslotRefilled
from wyraj.core.refs import ref_for

SLOT_COUNT = 4


def slots_of(world: World, actor: Entity) -> Quickslots:
    return world.get(actor, Quickslots) or Quickslots()


def count_of(world: World, actor: Entity, key: str) -> int:
    inventory = world.get(actor, Inventory) or Inventory()
    total = 0
    for entity in inventory.items:
        item = world.get(entity, Item)
        if item is not None and item.key == key:
            total += 1
    return total


def bound_entity(world: World, actor: Entity, index: int) -> Entity | None:
    """First inventory entity matching the bound key, or None."""
    key = slots_of(world, actor).key_at(index)
    if key is None:
        return None
    inventory = world.get(actor, Inventory) or Inventory()
    for entity in inventory.items:
        item = world.get(entity, Item)
        if item is not None and item.key == key:
            return entity
    return None


def bind(world: World, bus: EventBus, actor: Entity, index: int, item: Entity) -> bool:
    """Bind a consumable's key to a slot; rebinding overwrites silently."""
    component = world.get(item, Item)
    if component is None or component.kind != "consumable":
        return False
    world.add(actor, slots_of(world, actor).with_key(index, component.key))
    bus.publish(QuickslotBound(actor=ref_for(world, actor), item=ref_for(world, item), index=index))
    return True


def clear(world: World, bus: EventBus, actor: Entity, index: int) -> None:
    slots = slots_of(world, actor)
    if slots.key_at(index) is None:
        return
    world.add(actor, slots.with_key(index, None))
    bus.publish(QuickslotCleared(actor=ref_for(world, actor), index=index))


def note_gained(world: World, bus: EventBus, actor: Entity, item: Entity) -> None:
    """Publish QuickslotRefilled when a bound-but-empty slot gets stock again."""
    component = world.get(item, Item)
    if component is None:
        return
    if count_of(world, actor, component.key) != 1:  # only the 0 → 1 transition
        return
    slots = slots_of(world, actor)
    for index in range(SLOT_COUNT):
        if slots.key_at(index) == component.key:
            bus.publish(
                QuickslotRefilled(
                    actor=ref_for(world, actor), item=ref_for(world, item), index=index
                )
            )
            return
