"""Movement: apply a move intent, emitting facts for narration/UI."""

from wyraj.core.components import Health, OnLevel, Position
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EntityMoved, EventBus, MoveBlocked
from wyraj.core.map import GameMap
from wyraj.core.refs import ref_for


def level_of(world: World, entity: Entity) -> int:
    on_level = world.get(entity, OnLevel)
    return on_level.depth if on_level is not None else 0


def blocking_entity_at(world: World, x: int, y: int, depth: int) -> Entity | None:
    """A living creature occupies the tile (creatures = entities with Health)."""
    for entity, (pos, _health) in world.query(Position, Health):
        if (pos.x, pos.y) == (x, y) and level_of(world, entity) == depth:
            return entity
    return None


def try_move(
    world: World, game_map: GameMap, bus: EventBus, entity: Entity, dx: int, dy: int
) -> bool:
    """Move `entity` by (dx, dy) if the target tile is open. Returns success.

    Bump-attacks are resolved by the caller (combat) before this is reached;
    here a blocked tile just emits MoveBlocked.
    """
    pos = world.expect(entity, Position)
    nx, ny = pos.x + dx, pos.y + dy
    depth = level_of(world, entity)
    if not game_map.is_walkable(nx, ny) or blocking_entity_at(world, nx, ny, depth) is not None:
        bus.publish(MoveBlocked(actor=ref_for(world, entity), to_pos=(nx, ny)))
        return False
    world.add(entity, Position(nx, ny))
    bus.publish(EntityMoved(actor=ref_for(world, entity), from_pos=(pos.x, pos.y), to_pos=(nx, ny)))
    return True
