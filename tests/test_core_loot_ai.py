import random

from wyraj.content.loot import load_loot_tables
from wyraj.core.actions import Get, WearItem
from wyraj.core.components import (
    AI,
    ArmorStats,
    Health,
    Lore,
    Melee,
    OnLevel,
    Player,
    Position,
    Wearing,
)
from wyraj.core.ecs import World
from wyraj.core.events import AttackResolved, EventBus, ItemWorn, Outcome
from wyraj.core.game import Game
from wyraj.core.map import GameMap, Tile
from wyraj.core.systems import ai
from wyraj.core.systems.combat import attack


def open_map(width: int = 12, height: int = 12) -> GameMap:
    tiles = [[Tile.FLOOR] * width for _ in range(height)]
    for x in range(width):
        tiles[0][x] = Tile.WALL
        tiles[height - 1][x] = Tile.WALL
    for y in range(height):
        tiles[y][0] = Tile.WALL
        tiles[y][width - 1] = Tile.WALL
    return GameMap(tiles)


def test_loot_tables_load_and_reference_real_items() -> None:
    game = Game(seed=42)
    tables = load_loot_tables()
    assert {"puszcza", "kurhany"} <= set(tables)
    for table in tables.values():
        for key in table.weights:
            assert key in game.items_catalog, f"loot table references unknown item {key}"
    assert tables["kurhany"].items_for_depth(3) > tables["kurhany"].items_for_depth(1)


def test_armor_fully_absorbs_weak_hit_as_graze() -> None:
    world = World()
    bus = EventBus()
    events: list[AttackResolved] = []
    bus.subscribe(AttackResolved, events.append)
    armor = world.create(ArmorStats(protection=5))
    defender = world.create(Player(), Health(10, 10), Wearing(item=armor))
    attacker = world.create(Melee(damage=3, to_hit=100), Health(5, 5))
    attack(world, bus, random.Random(1), attacker, defender)
    assert events[0].outcome is Outcome.GRAZE
    assert events[0].damage == 0
    assert world.expect(defender, Health).hp == 10


def test_armor_reduces_damage() -> None:
    world = World()
    bus = EventBus()
    armor = world.create(ArmorStats(protection=2))
    defender = world.create(Player(), Health(10, 10), Wearing(item=armor))
    attacker = world.create(Melee(damage=5, to_hit=100), Health(5, 5))
    attack(world, bus, random.Random(1), attacker, defender)
    assert world.expect(defender, Health).hp == 7  # 5 - 2


def test_wear_flow_in_game() -> None:
    game = Game(seed=42)
    ppos = game.world.expect(game.player, Position)
    armor = game.spawn_item(game.items_catalog["kaftan"], ppos.x, ppos.y, 0)
    worn_events: list[ItemWorn] = []
    game.bus.subscribe(ItemWorn, worn_events.append)
    game.step(Get())
    game.step(WearItem(armor))
    assert game.world.expect(game.player, Wearing).item == armor
    assert worn_events[0].item.key == "kaftan"


def build_duel_world() -> tuple[World, EventBus, int]:
    world = World()
    bus = EventBus()
    player = world.create(Player(), Position(5, 5), Health(50, 50), OnLevel(0))
    return world, bus, player


def test_ambusher_waits_then_charges() -> None:
    world, bus, _player = build_duel_world()
    monster = world.create(
        AI(behavior="ambush"),
        Position(1, 1),  # distance 4 from (5,5)
        Health(10, 10),
        Melee(damage=1, to_hit=100),
        OnLevel(0),
        Lore(key="strzyga", name="strzyga"),
    )
    game_map = open_map()
    rng = random.Random(1)
    # Distance 4 == AMBUSH_RADIUS → it moves.
    ai.take_turn(world, game_map, bus, rng, monster)
    assert world.expect(monster, Position) != Position(1, 1)

    # Reset far away: distance > radius → it holds still.
    world.add(monster, Position(10, 10))
    world.add(_player, Position(1, 1))
    ai.take_turn(world, game_map, bus, rng, monster)
    assert world.expect(monster, Position) == Position(10, 10)

    # Wounded ambusher abandons the ambush.
    world.add(monster, Health(5, 10))
    ai.take_turn(world, game_map, bus, rng, monster)
    assert world.expect(monster, Position) != Position(10, 10)


def test_fleeing_licho_keeps_distance() -> None:
    world, bus, player = build_duel_world()
    monster = world.create(
        AI(behavior="flee"),
        Position(6, 5),
        Health(4, 4),
        Melee(damage=1, to_hit=100),
        OnLevel(0),
        Lore(key="licho", name="licho"),
    )
    game_map = open_map()
    before = world.expect(monster, Position)
    ai.take_turn(world, game_map, bus, random.Random(1), monster)
    after = world.expect(monster, Position)
    ppos = world.expect(player, Position)
    dist_before = max(abs(before.x - ppos.x), abs(before.y - ppos.y))
    dist_after = max(abs(after.x - ppos.x), abs(after.y - ppos.y))
    assert dist_after > dist_before


def test_pack_bonus_counts_flanking_allies() -> None:
    world, _bus, player = build_duel_world()
    wilk_a = world.create(
        AI(behavior="pack"),
        Position(4, 5),
        Health(6, 6),
        Melee(damage=1, to_hit=50),
        OnLevel(0),
        Lore(key="wilk", name="wilk"),
    )
    world.create(
        AI(behavior="pack"),
        Position(6, 5),
        Health(6, 6),
        Melee(damage=1, to_hit=50),
        OnLevel(0),
        Lore(key="wilk", name="wilk"),
    )
    assert ai._pack_bonus(world, wilk_a, player) == ai.PACK_BONUS_PER_ALLY
