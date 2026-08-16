"""US 11.7 — the competent-bot descent sim (M8 §5).

A provisioned, rule-following bot (standard kit; omniscient pathing — it
measures the dungeon and the encounter, not village economics or map memory)
descends to the Dno and attempts the rite. The full win-rate measurement runs
only with WYRAJ_SIM=1; CI keeps a cheap smoke that the bot neither crashes
nor wins implausibly often.
"""

import os
from collections import deque

import pytest

from wyraj.core.actions import Action, Descend, Get, Move, UseItem, Wait
from wyraj.core.components import (
    AI,
    Health,
    Hunger,
    Inventory,
    Item,
    LightSource,
    Position,
    Rite,
)
from wyraj.core.game import MAX_DEPTH, Game
from wyraj.core.map import Tile
from wyraj.core.systems.movement import level_of

KIT = (
    "toporek",
    "kaftan",
    "gromnica",
    "gromnica",
    "gromnica",
    "sol_swiecona",
    "odwar",
    "odwar",
    "odwar",
    "mocny_odwar",
    "chleb",
    "suszone_mieso",
)
TURN_BUDGET = 1500


def provision(game: Game) -> None:
    from wyraj.core.actions import WearItem, WieldItem

    inventory = game.world.get(game.player, Inventory) or Inventory()
    extra = tuple(game.spawn_stock_item(key) for key in KIT)
    game.world.add(game.player, Inventory(items=(*inventory.items, *extra)))
    axe, coat = held(game, "toporek"), held(game, "kaftan")
    if axe is not None:
        game.step(WieldItem(axe))
    if coat is not None:
        game.step(WearItem(coat))


def held(game: Game, key: str) -> int | None:
    inventory = game.world.get(game.player, Inventory) or Inventory()
    for entity in inventory.items:
        item = game.world.get(entity, Item)
        if item is not None and item.key == key:
            return entity
    return None


def path_step(game: Game, targets: set[tuple[int, int]]) -> Action | None:
    """BFS over walkable tiles toward the nearest target; first step out."""
    game_map = game.map
    start = game.world.expect(game.player, Position)
    if (start.x, start.y) in targets:
        return None
    frontier = deque([(start.x, start.y)])
    came: dict[tuple[int, int], tuple[int, int]] = {(start.x, start.y): (start.x, start.y)}
    goal = None
    while frontier:
        x, y = frontier.popleft()
        if (x, y) in targets:
            goal = (x, y)
            break
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if (nx, ny) in came or not game_map.in_bounds(nx, ny):
                    continue
                if not game_map.is_walkable(nx, ny):
                    continue
                came[(nx, ny)] = (x, y)
                frontier.append((nx, ny))
    if goal is None:
        return None
    node = goal
    while came[node] != (start.x, start.y):
        node = came[node]
    return Move(node[0] - start.x, node[1] - start.y)


def adjacent_hostile(game: Game) -> Action | None:
    pos = game.world.expect(game.player, Position)
    for entity, (_ai, epos) in game.world.query(AI, Position):
        if level_of(game.world, entity) != game.depth:
            continue
        if max(abs(epos.x - pos.x), abs(epos.y - pos.y)) <= 1:
            return Move(epos.x - pos.x, epos.y - pos.y)
    return None


def choose_action(game: Game) -> Action:
    world, player = game.world, game.player
    pos = world.expect(player, Position)
    health = world.expect(player, Health)

    if world.get(player, Rite) is not None:
        return Wait()  # hands on the lids: hold
    if game.depth == MAX_DEPTH and game.vault is not None:
        lit = world.get(player, LightSource) is not None
        candle = held(game, "gromnica")
        if game.wij_phase == "gaze" and lit and candle is not None:
            return UseItem(candle)  # douse: the dark is survival now
        fight = adjacent_hostile(game)
        if fight is not None and health.fraction > 0.3:
            return fight
        if held(game, "sol_swiecona") is not None:
            cx, cy = game.vault.cradle
            if max(abs(pos.x - cx), abs(pos.y - cy)) <= 1:
                return Move(cx - pos.x, cy - pos.y)  # begin the rite
            step = path_step(game, {(cx + dx, cy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)})
            return step or Wait()
        return fight or Wait()

    odwar = held(game, "odwar") or held(game, "mocny_odwar")
    if health.fraction < 0.55 and odwar is not None:
        return UseItem(odwar)
    hunger = world.get(player, Hunger)
    bread = held(game, "chleb")
    if hunger is not None and hunger.band != "sated" and bread is not None:
        return UseItem(bread)
    fight = adjacent_hostile(game)
    if fight is not None:
        return fight
    candle = held(game, "gromnica")
    if game.depth >= 3 and world.get(player, LightSource) is None and candle is not None:
        return UseItem(candle)
    from wyraj.core.systems.items import item_at

    if item_at(world, pos.x, pos.y, game.depth) is not None:
        return Get()
    if game.map.tiles[pos.y][pos.x] is Tile.STAIRS_DOWN:
        return Descend()
    stairs = {
        (x, y)
        for y, row in enumerate(game.map.tiles)
        for x, tile in enumerate(row)
        if tile is Tile.STAIRS_DOWN
    }
    return path_step(game, stairs) or Wait()


def run_bot(seed: int) -> Game:
    game = Game(seed=seed, meta_autosave=False)
    provision(game)
    for _ in range(TURN_BUDGET):
        if game.game_over:
            break
        game.step(choose_action(game))
    return game


def test_bot_smoke_three_seeds() -> None:
    """CI floor: the bot plays whole runs without crashing and reaches crypts."""
    deepest = 0
    for seed in (7, 42, 1234):
        game = run_bot(seed)
        deepest = max(deepest, game.max_depth_reached)
        assert game.turn > 0
    assert deepest >= 3  # a competent bot at least reaches the barrows


@pytest.mark.skipif(not os.environ.get("WYRAJ_SIM"), reason="WYRAJ_SIM=1 runs the measurement")
def test_bot_win_rate_measurement() -> None:
    seeds = range(1, 31)
    wins, depths = 0, []
    for seed in seeds:
        game = run_bot(seed)
        wins += int(game.victory)
        depths.append(game.max_depth_reached)
    rate = wins / len(depths)
    print(f"\nDno sim: {wins}/{len(depths)} wins ({rate:.0%}), depths={sorted(depths)}")
    assert wins >= 1, "the sanity floor: a provisioned competent bot can win at all"
    assert rate <= 0.5, "if half the runs win, the bottom is too soft"
