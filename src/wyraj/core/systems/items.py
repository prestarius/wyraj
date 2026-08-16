"""Item interactions: pick up, use consumables, wield weapons."""

from dataclasses import replace

from wyraj.core.components import (
    ArmorStats,
    Consumable,
    Health,
    Hunger,
    Inventory,
    Item,
    ItemMemory,
    LightSource,
    OnLevel,
    Position,
    StatusEffect,
    Wearing,
    Wielding,
    WornExtras,
)
from wyraj.core.ecs import Entity, World
from wyraj.core.events import (
    EventBus,
    HeirloomWielded,
    HungerChanged,
    ItemPickedUp,
    ItemUnequipped,
    ItemUsed,
    ItemWielded,
    ItemWorn,
    LightExtinguished,
)
from wyraj.core.refs import ref_for
from wyraj.core.systems.movement import level_of
from wyraj.core.systems.status import apply_status

BLESSING_TO_HIT = 15


def item_at(world: World, x: int, y: int, depth: int) -> Entity | None:
    for entity, (pos, _item) in world.query(Position, Item):
        if (pos.x, pos.y) == (x, y) and level_of(world, entity) == depth:
            return entity
    return None


def pick_up(world: World, bus: EventBus, actor: Entity) -> bool:
    pos = world.expect(actor, Position)
    item = item_at(world, pos.x, pos.y, level_of(world, actor))
    if item is None:
        return False
    inventory = world.get(actor, Inventory) or Inventory()
    item_ref = ref_for(world, item)
    world.remove(item, Position)
    world.remove(item, OnLevel)
    world.add(actor, Inventory(items=(*inventory.items, item)))
    bus.publish(ItemPickedUp(actor=ref_for(world, actor), item=item_ref))
    return True


def use_item(world: World, bus: EventBus, actor: Entity, item: Entity) -> bool:
    consumable = world.get(item, Consumable)
    if consumable is None:
        return False
    actor_ref = ref_for(world, actor)
    item_ref = ref_for(world, item)

    if consumable.effect == "heal":
        health = world.expect(actor, Health)
        world.add(actor, replace(health, hp=min(health.hp + consumable.power, health.max_hp)))
    elif consumable.effect == "bless":
        # power = duration in turns; the to-hit bonus is fixed.
        apply_status(
            world,
            bus,
            actor,
            StatusEffect(kind="blessing", duration=consumable.power, power=BLESSING_TO_HIT),
        )
    elif consumable.effect == "light":
        if world.get(actor, LightSource) is not None:
            # Already burning: using a light again douses the flame instead
            # (M8 §2.3 — under the gaze, going dark is survival). The candle
            # in the pack is untouched; the burning one is forfeit.
            world.remove(actor, LightSource)
            bus.publish(LightExtinguished(actor=actor_ref))
            return True
        world.add(actor, LightSource(turns=consumable.power))
    elif consumable.effect == "feed":
        hunger = world.get(actor, Hunger)
        if hunger is not None:
            old_band = hunger.band
            new_hunger = replace(
                hunger,
                satiation=min(hunger.satiation + consumable.power, hunger.max_satiation),
            )
            world.add(actor, new_hunger)
            if new_hunger.band != old_band:
                bus.publish(HungerChanged(actor=actor_ref, band=new_hunger.band))

    _remove_from_inventory(world, actor, item)
    wielding = world.get(actor, Wielding)
    if wielding is not None and wielding.item == item:
        world.add(actor, Wielding(item=None))
    world.destroy(item)
    bus.publish(
        ItemUsed(actor=actor_ref, item=item_ref, effect=consumable.effect, power=consumable.power)
    )
    return True


def wield(world: World, bus: EventBus, actor: Entity, item: Entity) -> None:
    world.add(actor, Wielding(item=item))
    bus.publish(ItemWielded(actor=ref_for(world, actor), item=ref_for(world, item)))
    memory = world.get(item, ItemMemory)
    if memory is not None:
        # The blade remembers — once per withdrawal.
        world.remove(item, ItemMemory)
        bus.publish(HeirloomWielded(actor=ref_for(world, actor), item=ref_for(world, item)))


def wear(world: World, bus: EventBus, actor: Entity, item: Entity, slot: str = "torso") -> None:
    if slot == "torso":
        world.add(actor, Wearing(item=item))
    else:
        extras = world.get(actor, WornExtras) or WornExtras()
        world.add(actor, replace(extras, **{slot: item}))
    bus.publish(ItemWorn(actor=ref_for(world, actor), item=ref_for(world, item)))


def unequip(world: World, bus: EventBus, actor: Entity, slot: str) -> bool:
    """Empty a paper-doll slot; the item stays in the pack. True if something left it."""
    item: Entity | None = None
    if slot == "weapon":
        wielding = world.get(actor, Wielding)
        if wielding is not None and wielding.item is not None:
            item = wielding.item
            world.add(actor, Wielding(item=None))
    elif slot == "torso":
        wearing = world.get(actor, Wearing)
        if wearing is not None and wearing.item is not None:
            item = wearing.item
            world.add(actor, Wearing(item=None))
    elif slot in ("head", "amulet", "feet"):
        extras = world.get(actor, WornExtras)
        if extras is not None and getattr(extras, slot) is not None:
            item = getattr(extras, slot)
            world.add(actor, replace(extras, **{slot: None}))
    if item is None:
        return False
    bus.publish(ItemUnequipped(actor=ref_for(world, actor), item=ref_for(world, item)))
    return True


def protection_of(world: World, actor: Entity) -> int:
    worn: list[Entity] = []
    wearing = world.get(actor, Wearing)
    if wearing is not None and wearing.item is not None:
        worn.append(wearing.item)
    extras = world.get(actor, WornExtras)
    if extras is not None:
        worn += [e for e in (extras.head, extras.amulet, extras.feet) if e is not None]
    total = 0
    for item in worn:
        stats = world.get(item, ArmorStats)
        if stats is not None:
            total += stats.protection
    return total


def _remove_from_inventory(world: World, actor: Entity, item: Entity) -> None:
    inventory = world.get(actor, Inventory)
    if inventory is not None:
        world.add(actor, Inventory(items=tuple(i for i in inventory.items if i != item)))
