"""Melee combat resolution. Rolls come from the `combat` RNG stream only."""

import random
from dataclasses import replace

from wyraj.core.components import Health, Melee
from wyraj.core.ecs import Entity, World
from wyraj.core.events import AttackResolved, EventBus, Outcome
from wyraj.core.refs import ref_for
from wyraj.core.systems.death import kill


def attack(
    world: World, bus: EventBus, rng: random.Random, attacker: Entity, defender: Entity
) -> None:
    melee = world.expect(attacker, Melee)
    health = world.expect(defender, Health)
    attacker_ref = ref_for(world, attacker)
    defender_ref = ref_for(world, defender)

    roll = rng.randint(1, 100)
    if roll > melee.to_hit:
        bus.publish(
            AttackResolved(
                attacker=attacker_ref,
                defender=defender_ref,
                weapon=None,
                damage=0,
                outcome=Outcome.MISS,
                defender_hp_frac=health.fraction,
            )
        )
        return

    new_hp = health.hp - melee.damage
    world.add(defender, replace(health, hp=max(new_hp, 0)))
    outcome = Outcome.KILL if new_hp <= 0 else Outcome.HIT
    bus.publish(
        AttackResolved(
            attacker=attacker_ref,
            defender=defender_ref,
            weapon=None,
            damage=melee.damage,
            outcome=outcome,
            defender_hp_frac=max(new_hp, 0) / health.max_hp,
        )
    )
    if outcome is Outcome.KILL:
        kill(world, bus, defender)
