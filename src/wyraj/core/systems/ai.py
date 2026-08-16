"""AI behaviors, dispatched on the bestiary `behavior` field.

- approach: walk toward the player, bite when adjacent
- pack:     approach, with a to-hit bonus per packmate also flanking the target
- ambush:   hold still until the player comes close (or it gets hurt), then approach
- flee:     keep away from the player; bite only when cornered
"""

import random

from wyraj.core.components import AI, Health, Lifting, Lore, Peaceful, Player, Position, Swimmer
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EventBus
from wyraj.core.map import GameMap, Tile
from wyraj.core.systems.combat import attack
from wyraj.core.systems.movement import blocking_entity_at, level_of

AMBUSH_RADIUS = 4
PACK_BONUS_PER_ALLY = 10


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)


def _find_player(world: World) -> Entity | None:
    players = world.entities_with(Player, Position)
    return players[0] if players else None


def _step(world: World, game_map: GameMap, entity: Entity, dx: int, dy: int) -> bool:
    pos = world.expect(entity, Position)
    nx, ny = pos.x + dx, pos.y + dy
    depth = level_of(world, entity)
    passable = game_map.is_walkable(nx, ny) or (
        game_map.in_bounds(nx, ny)
        and game_map.tiles[ny][nx] is Tile.WATER
        and world.has(entity, Swimmer)
    )
    if passable and blocking_entity_at(world, nx, ny, depth) is None:
        world.add(entity, Position(nx, ny))
        return True
    return False


def _walk_toward(world: World, game_map: GameMap, entity: Entity, tx: int, ty: int) -> None:
    pos = world.expect(entity, Position)
    dx, dy = tx - pos.x, ty - pos.y
    sx, sy = _sign(dx), _sign(dy)
    candidates = [(sx, sy)]
    candidates += [(sx, 0), (0, sy)] if abs(dx) >= abs(dy) else [(0, sy), (sx, 0)]
    for mx, my in candidates:
        if (mx, my) != (0, 0) and _step(world, game_map, entity, mx, my):
            return


def _walk_away(world: World, game_map: GameMap, entity: Entity, tx: int, ty: int) -> bool:
    pos = world.expect(entity, Position)
    dx, dy = pos.x - tx, pos.y - ty
    sx, sy = _sign(dx) or random_free_sign(), _sign(dy)
    candidates = [(sx, sy), (sx, 0), (0, sy), (-sy, sx), (sy, -sx)]
    for mx, my in candidates:
        if (mx, my) != (0, 0) and _step(world, game_map, entity, mx, my):
            return True
    return False


def random_free_sign() -> int:
    # Deterministic tie-break when fleeing from an identical column/row.
    return 1


def _pack_bonus(world: World, entity: Entity, player: Entity) -> int:
    """+to-hit per same-kind packmate also adjacent to the player."""
    lore = world.get(entity, Lore)
    if lore is None:
        return 0
    ppos = world.expect(player, Position)
    depth = level_of(world, entity)
    allies = 0
    for other, (_ai, other_lore, pos) in world.query(AI, Lore, Position):
        if other == entity or other_lore.key != lore.key:
            continue
        if level_of(world, other) != depth:
            continue
        if max(abs(pos.x - ppos.x), abs(pos.y - ppos.y)) <= 1:
            allies += 1
    return allies * PACK_BONUS_PER_ALLY


def take_turn(
    world: World, game_map: GameMap, bus: EventBus, combat_rng: random.Random, entity: Entity
) -> None:
    player = _find_player(world)
    if player is None:
        return
    ppos = world.expect(player, Position)
    pos = world.expect(entity, Position)
    distance = max(abs(ppos.x - pos.x), abs(ppos.y - pos.y))
    if world.get(entity, Peaceful) is not None:
        return  # Dziady (M9 §3): the dead walk, they do not begin
    behavior = world.expect(entity, AI).behavior

    if behavior == "flee":
        if _walk_away(world, game_map, entity, ppos.x, ppos.y):
            return
        if distance <= 1:  # cornered — bite
            attack(world, bus, combat_rng, entity, player)
        return

    if behavior == "lift":  # M8 §2.2: the sługa serves the lids, not the fight
        target = world.get(entity, Lifting)
        if target is None:
            return
        if distance <= 1:  # a shove for whoever stands in the way
            attack(world, bus, combat_rng, entity, player)
            return
        if max(abs(pos.x - target.x), abs(pos.y - target.y)) <= 1:
            return  # adjacent to the cradle: it channels; the Wij tick counts it
        _walk_toward(world, game_map, entity, target.x, target.y)
        return

    if behavior == "ambush" and distance > AMBUSH_RADIUS:
        health = world.get(entity, Health)
        if health is None or health.hp >= health.max_hp:
            return  # lie in wait

    if distance <= 1:
        bonus = _pack_bonus(world, entity, player) if behavior == "pack" else 0
        attack(world, bus, combat_rng, entity, player, to_hit_bonus=bonus)
        return

    _walk_toward(world, game_map, entity, ppos.x, ppos.y)
