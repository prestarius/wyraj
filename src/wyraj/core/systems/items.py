"""Item interactions: pick up, use consumables, wield weapons."""

from dataclasses import replace

from wyraj.core.components import (
    Consumable,
    Health,
    Hunger,
    Inventory,
    Item,
    LightSource,
    OnLevel,
    Position,
    StatusEffect,
    Wielding,
)
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EventBus, HungerChanged, ItemPickedUp, ItemUsed, ItemWielded
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


def _remove_from_inventory(world: World, actor: Entity, item: Entity) -> None:
    inventory = world.get(actor, Inventory)
    if inventory is not None:
        world.add(actor, Inventory(items=tuple(i for i in inventory.items if i != item)))
