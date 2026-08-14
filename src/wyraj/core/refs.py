"""Build EntityRef snapshots from world state."""

from wyraj.core.components import Lore, Player
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EntityRef


def ref_for(world: World, entity: Entity) -> EntityRef:
    lore = world.get(entity, Lore)
    is_player = world.has(entity, Player)
    if is_player:
        return EntityRef(entity=entity, key="player", name="you", is_player=True)
    if lore is not None:
        return EntityRef(entity=entity, key=lore.key, name=lore.name)
    return EntityRef(entity=entity, key="unknown", name="something")
