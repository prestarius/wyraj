"""Death handling: emit the fact, then remove the corpse from play.

The player entity is kept in the world (the UI still needs its components
for the death screen); everyone else is destroyed.
"""

from wyraj.core.ecs import Entity, World
from wyraj.core.events import EntityDied, EventBus
from wyraj.core.refs import ref_for


def kill(world: World, bus: EventBus, entity: Entity) -> None:
    ref = ref_for(world, entity)
    bus.publish(EntityDied(entity=ref))
    if not ref.is_player:
        world.destroy(entity)
