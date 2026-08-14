"""Hunger clock: satiation drains each turn; starving grinds down HP."""

from dataclasses import replace

from wyraj.core.components import Health, Hunger
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EventBus, HungerChanged, StarvationHit
from wyraj.core.refs import ref_for
from wyraj.core.systems.death import kill

STARVATION_PERIOD = 5  # one HP lost every N turns while starving
STARVATION_DAMAGE = 1


def tick(world: World, bus: EventBus, actor: Entity, turn: int) -> None:
    hunger = world.get(actor, Hunger)
    if hunger is None:
        return
    old_band = hunger.band
    hunger = replace(hunger, satiation=max(hunger.satiation - 1, 0))
    world.add(actor, hunger)
    if hunger.band != old_band:
        bus.publish(HungerChanged(actor=ref_for(world, actor), band=hunger.band))

    if hunger.band == "starving" and turn % STARVATION_PERIOD == 0:
        health = world.expect(actor, Health)
        new_hp = max(health.hp - STARVATION_DAMAGE, 0)
        world.add(actor, replace(health, hp=new_hp))
        bus.publish(
            StarvationHit(
                actor=ref_for(world, actor),
                damage=STARVATION_DAMAGE,
                hp_frac=new_hp / health.max_hp,
            )
        )
        if new_hp <= 0:
            kill(world, bus, actor)
