"""Melee combat resolution. Rolls come from the `combat` RNG stream only."""

import random
from dataclasses import replace

from wyraj.core.components import (
    AttackStatus,
    Health,
    Melee,
    StatusEffect,
    WeaponStats,
    Wielding,
)
from wyraj.core.ecs import Entity, World
from wyraj.core.events import AttackResolved, EventBus, Outcome
from wyraj.core.refs import ref_for
from wyraj.core.systems.death import kill
from wyraj.core.systems.items import protection_of
from wyraj.core.systems.status import apply_status, to_hit_modifier


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
    world: World,
    bus: EventBus,
    rng: random.Random,
    attacker: Entity,
    defender: Entity,
    to_hit_bonus: int = 0,
) -> None:
    melee = world.expect(attacker, Melee)
    health = world.expect(defender, Health)
    attacker_ref = ref_for(world, attacker)
    defender_ref = ref_for(world, defender)
    weapon_entity, weapon_damage = _weapon(world, attacker)
    weapon_ref = ref_for(world, weapon_entity) if weapon_entity is not None else None
    damage = weapon_damage if weapon_damage is not None else melee.damage
    damage = max(damage - protection_of(world, defender), 0)

    to_hit = max(5, min(95, melee.to_hit + to_hit_modifier(world, attacker) + to_hit_bonus))
    roll = rng.randint(1, 100)
    if roll > to_hit:
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

    if damage == 0:
        # Armor soaked the whole blow.
        bus.publish(
            AttackResolved(
                attacker=attacker_ref,
                defender=defender_ref,
                weapon=weapon_ref,
                damage=0,
                outcome=Outcome.GRAZE,
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
        return

    attack_status = world.get(attacker, AttackStatus)
    if attack_status is not None and rng.randint(1, 100) <= attack_status.chance:
        apply_status(
            world,
            bus,
            defender,
            StatusEffect(
                kind=attack_status.kind,
                duration=attack_status.duration,
                power=attack_status.power,
            ),
        )
