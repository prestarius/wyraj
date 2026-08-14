"""Status effects: apply, tick damage-over-time, expire. Also light sources."""

from dataclasses import replace

from wyraj.core.components import Health, LightSource, StatusEffect, StatusEffects
from wyraj.core.ecs import Entity, World
from wyraj.core.events import (
    EventBus,
    LightExtinguished,
    StatusApplied,
    StatusExpired,
    StatusTick,
)
from wyraj.core.refs import ref_for
from wyraj.core.systems.death import kill

DOT_KINDS = ("bleeding", "poison")


def apply_status(world: World, bus: EventBus, actor: Entity, effect: StatusEffect) -> None:
    """Apply a status; re-applying the same kind refreshes to the longer run."""
    statuses = world.get(actor, StatusEffects) or StatusEffects()
    existing = {e.kind: e for e in statuses.effects}
    old = existing.get(effect.kind)
    if old is not None:
        effect = StatusEffect(
            kind=effect.kind,
            duration=max(old.duration, effect.duration),
            power=max(old.power, effect.power),
        )
    existing[effect.kind] = effect
    world.add(actor, StatusEffects(effects=tuple(existing.values())))
    if old is None:
        bus.publish(
            StatusApplied(actor=ref_for(world, actor), kind=effect.kind, duration=effect.duration)
        )


def active_kinds(world: World, actor: Entity) -> dict[str, StatusEffect]:
    statuses = world.get(actor, StatusEffects)
    return {e.kind: e for e in statuses.effects} if statuses else {}


def to_hit_modifier(world: World, actor: Entity) -> int:
    kinds = active_kinds(world, actor)
    modifier = 0
    if "fear" in kinds:
        modifier -= kinds["fear"].power
    if "blessing" in kinds:
        modifier += kinds["blessing"].power
    return modifier


def tick(world: World, bus: EventBus, actor: Entity) -> None:
    """One turn's worth of status and light bookkeeping for one actor."""
    statuses = world.get(actor, StatusEffects)
    if statuses is not None and statuses.effects:
        remaining: list[StatusEffect] = []
        for effect in statuses.effects:
            if effect.kind in DOT_KINDS:
                health = world.get(actor, Health)
                if health is not None:
                    new_hp = max(health.hp - effect.power, 0)
                    world.add(actor, replace(health, hp=new_hp))
                    bus.publish(
                        StatusTick(
                            actor=ref_for(world, actor),
                            kind=effect.kind,
                            damage=effect.power,
                            hp_frac=new_hp / health.max_hp,
                        )
                    )
                    if new_hp <= 0:
                        kill(world, bus, actor)
            ticked = replace(effect, duration=effect.duration - 1)
            if ticked.duration <= 0:
                bus.publish(StatusExpired(actor=ref_for(world, actor), kind=effect.kind))
            else:
                remaining.append(ticked)
        world.add(actor, StatusEffects(effects=tuple(remaining)))

    light = world.get(actor, LightSource)
    if light is not None:
        if light.turns <= 1:
            world.remove(actor, LightSource)
            bus.publish(LightExtinguished(actor=ref_for(world, actor)))
        else:
            world.add(actor, LightSource(turns=light.turns - 1))
