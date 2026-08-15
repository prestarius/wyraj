"""Death handling: emit the fact, then remove the corpse from play.

The player entity is kept in the world (the UI still needs its components
for the death screen); everyone else is destroyed.
"""

from wyraj.core.components import Position
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EntityDied, EventBus
from wyraj.core.refs import ref_for
from wyraj.core.systems.movement import level_of


def kill(world: World, bus: EventBus, entity: Entity) -> None:
    ref = ref_for(world, entity)
    pos = world.get(entity, Position)
    event = EntityDied(
        entity=ref,
        position=(pos.x, pos.y) if pos is not None else None,
        depth=level_of(world, entity),
    )
    if not ref.is_player:
        world.destroy(entity)
    bus.publish(event)
