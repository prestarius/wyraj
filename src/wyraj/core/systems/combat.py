"""Melee combat resolution. Rolls come from the `combat` RNG stream only."""

import random
from dataclasses import replace

from wyraj.core.components import Health, Melee, WeaponStats, Wielding
from wyraj.core.ecs import Entity, World
from wyraj.core.events import AttackResolved, EventBus, Outcome
from wyraj.core.refs import ref_for
from wyraj.core.systems.death import kill


def _weapon(world: World, attacker: Entity) -> tuple[Entity | None, int | None]:
    """Return (weapon entity, weapon damage) for the attacker's wielded item."""
    wielding = world.get(attacker, Wielding)
    if wielding is None or wielding.item is None:
        return None, None
    stats = world.get(wielding.item, WeaponStats)
    if stats is None:
        return None, None
    return wielding.item, stats.damage


def attack(
    world: World, bus: EventBus, rng: random.Random, attacker: Entity, defender: Entity
) -> None:
    melee = world.expect(attacker, Melee)
    health = world.expect(defender, Health)
    attacker_ref = ref_for(world, attacker)
    defender_ref = ref_for(world, defender)
    weapon_entity, weapon_damage = _weapon(world, attacker)
    weapon_ref = ref_for(world, weapon_entity) if weapon_entity is not None else None
    damage = weapon_damage if weapon_damage is not None else melee.damage

    roll = rng.randint(1, 100)
    if roll > melee.to_hit:
        bus.publish(
            AttackResolved(
                attacker=attacker_ref,
                defender=defender_ref,
                weapon=weapon_ref,
                damage=0,
                outcome=Outcome.MISS,
                defender_hp_frac=health.fraction,
            )
        )
        return

    new_hp = health.hp - damage
    world.add(defender, replace(health, hp=max(new_hp, 0)))
    outcome = Outcome.KILL if new_hp <= 0 else Outcome.HIT
    bus.publish(
        AttackResolved(
            attacker=attacker_ref,
            defender=defender_ref,
            weapon=weapon_ref,
            damage=damage,
            outcome=outcome,
            defender_hp_frac=max(new_hp, 0) / health.max_hp,
        )
    )
    if outcome is Outcome.KILL:
        kill(world, bus, defender)
