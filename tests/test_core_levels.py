from wyraj.core.actions import Ascend, Descend, Wait
from wyraj.core.components import AI, Position
from wyraj.core.events import LevelChanged
from wyraj.core.game import MAX_DEPTH, Game
from wyraj.core.map import Tile
from wyraj.core.systems.movement import level_of


def stand_on(game: Game, tile: Tile) -> None:
    spot = game.map.find_tile(tile)
    assert spot is not None
    game.world.add(game.player, Position(*spot))


def test_descend_and_ascend_roundtrip() -> None:
    game = Game(seed=42)
    changes: list[LevelChanged] = []
    game.bus.subscribe(LevelChanged, changes.append)

    stand_on(game, Tile.STAIRS_DOWN)
    game.step(Descend())
    assert game.depth == 1
    assert game.map.biome == "kurhany"
    assert level_of(game.world, game.player) == 1
    ppos = game.world.expect(game.player, Position)
    assert game.map.tiles[ppos.y][ppos.x] is Tile.STAIRS_UP
    assert changes[0] == LevelChanged(depth=1, direction="down")

    game.step(Ascend())
    assert game.depth == 0
    assert game.map.biome == "puszcza"
    ppos = game.world.expect(game.player, Position)
    assert game.map.tiles[ppos.y][ppos.x] is Tile.STAIRS_DOWN


def test_levels_persist_within_run() -> None:
    game = Game(seed=42)
    stand_on(game, Tile.STAIRS_DOWN)
    game.step(Descend())
    first_map = game.map
    crypt_monsters = {e for e in game.world.entities_with(AI) if level_of(game.world, e) == 1}
    assert crypt_monsters, "crypt should be populated"
    game.step(Ascend())
    stand_on(game, Tile.STAIRS_DOWN)
    game.step(Descend())
    assert game.map is first_map  # same object, not regenerated


def test_descent_is_deterministic_across_runs() -> None:
    def crypt_layout() -> list[list[Tile]]:
        game = Game(seed=42)
        stand_on(game, Tile.STAIRS_DOWN)
        game.step(Descend())
        return game.map.tiles

    assert crypt_layout() == crypt_layout()


def test_surface_monsters_frozen_while_below() -> None:
    game = Game(seed=42)
    stand_on(game, Tile.STAIRS_DOWN)
    game.step(Descend())
    surface = [
        (e, game.world.expect(e, Position))
        for e in game.world.entities_with(AI)
        if level_of(game.world, e) == 0
    ]
    for _ in range(5):
        game.step(Wait())
    for entity, pos in surface:
        assert game.world.expect(entity, Position) == pos


def test_deepest_level_has_no_down_stairs() -> None:
    game = Game(seed=42)
    for depth in range(1, MAX_DEPTH + 1):
        game._ensure_level(depth)
    assert game.levels[MAX_DEPTH].find_tile(Tile.STAIRS_DOWN) is None
    assert game.levels[MAX_DEPTH - 1].find_tile(Tile.STAIRS_DOWN) is not None


def test_monsters_respect_biomes() -> None:
    from wyraj.core.components import Lore

    game = Game(seed=42)
    game._ensure_level(1)
    crypt_keys = {
        game.world.expect(e, Lore).key
        for e in game.world.entities_with(AI)
        if level_of(game.world, e) == 1
    }
    assert crypt_keys, "crypt must have monsters"
    allowed = {k for k, d in game.bestiary.items() if "kurhany" in d.biomes}
    assert crypt_keys <= allowed
