"""AI behaviors. M0: 'approach' — walk toward the player, bite when adjacent."""

import random

from wyraj.core.components import Player, Position
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EventBus
from wyraj.core.map import GameMap
from wyraj.core.systems.combat import attack
from wyraj.core.systems.movement import blocking_entity_at, level_of


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)


def take_turn(
    world: World, game_map: GameMap, bus: EventBus, combat_rng: random.Random, entity: Entity
) -> None:
    players = world.entities_with(Player, Position)
    if not players:
        return
    player = players[0]
    ppos = world.expect(player, Position)
    pos = world.expect(entity, Position)
    dx, dy = ppos.x - pos.x, ppos.y - pos.y

    if max(abs(dx), abs(dy)) <= 1:
        attack(world, bus, combat_rng, entity, player)
        return

    # Greedy approach: try the full step, then each axis, most-distant first.
    sx, sy = _sign(dx), _sign(dy)
    candidates = [(sx, sy)]
    axis_steps = [(sx, 0), (0, sy)] if abs(dx) >= abs(dy) else [(0, sy), (sx, 0)]
    candidates += axis_steps
    depth = level_of(world, entity)
    for mx, my in candidates:
        if (mx, my) == (0, 0):
            continue
        nx, ny = pos.x + mx, pos.y + my
        if game_map.is_walkable(nx, ny) and blocking_entity_at(world, nx, ny, depth) is None:
            world.add(entity, Position(nx, ny))
            return
    # Boxed in: skip the turn silently (no event — nothing observable happened).
