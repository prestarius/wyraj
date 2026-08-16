from tests.conftest import goto_depth
from wyraj.core.actions import Ascend, Descend, Wait
from wyraj.core.components import AI, Lore, Position
from wyraj.core.events import LevelChanged
from wyraj.core.game import MAX_DEPTH, Game
from wyraj.core.map import Tile
from wyraj.core.systems.movement import level_of


def stand_on(game: Game, tile: Tile) -> None:
    spot = game.map.find_tile(tile)
    assert spot is not None
    game.world.add(game.player, Position(*spot))


def test_world_chain_biomes() -> None:
    game = Game(seed=42)
    assert game.map.biome == "wies"
    for depth, biome in [(1, "puszcza"), (2, "bagna"), (3, "kurhany"), (5, "kurhany")]:
        game._ensure_level(depth)
        assert game.levels[depth].biome == biome


def test_descend_and_ascend_roundtrip() -> None:
    game = Game(seed=42)
    changes: list[LevelChanged] = []
    game.bus.subscribe(LevelChanged, changes.append)

    stand_on(game, Tile.STAIRS_DOWN)
    game.step(Descend())
    assert game.depth == 1
    assert game.map.biome == "puszcza"
    assert level_of(game.world, game.player) == 1
    ppos = game.world.expect(game.player, Position)
    assert game.map.tiles[ppos.y][ppos.x] is Tile.STAIRS_UP
    assert changes[0] == LevelChanged(depth=1, direction="down")

    game.step(Ascend())
    assert game.depth == 0
    assert game.map.biome == "wies"
    ppos = game.world.expect(game.player, Position)
    assert game.map.tiles[ppos.y][ppos.x] is Tile.STAIRS_DOWN


def test_levels_persist_within_run() -> None:
    game = Game(seed=42)
    stand_on(game, Tile.STAIRS_DOWN)
    game.step(Descend())
    first_map = game.map
    forest_monsters = {e for e in game.world.entities_with(AI) if level_of(game.world, e) == 1}
    assert forest_monsters, "puszcza should be populated"
    game.step(Ascend())
    stand_on(game, Tile.STAIRS_DOWN)
    game.step(Descend())
    assert game.map is first_map  # same object, not regenerated


def test_descent_is_deterministic_across_runs() -> None:
    def forest_layout() -> list[list[Tile]]:
        game = Game(seed=42)
        stand_on(game, Tile.STAIRS_DOWN)
        game.step(Descend())
        return game.map.tiles

    assert forest_layout() == forest_layout()


def test_off_level_monsters_frozen() -> None:
    game = Game(seed=42)
    game._ensure_level(1)
    forest = [
        (e, game.world.expect(e, Position))
        for e in game.world.entities_with(AI)
        if level_of(game.world, e) == 1
    ]
    assert forest
    for _ in range(5):
        game.step(Wait())  # player is still in the village
    for entity, pos in forest:
        assert game.world.expect(entity, Position) == pos


def test_deepest_level_has_no_down_stairs() -> None:
    game = Game(seed=42)
    for depth in range(1, MAX_DEPTH + 1):
        game._ensure_level(depth)
    assert game.levels[MAX_DEPTH].find_tile(Tile.STAIRS_DOWN) is None
    assert game.levels[MAX_DEPTH - 1].find_tile(Tile.STAIRS_DOWN) is not None


def test_monsters_respect_biomes() -> None:
    game = Game(seed=42)
    game._ensure_level(3)
    crypt_keys = {
        game.world.expect(e, Lore).key
        for e in game.world.entities_with(AI)
        if level_of(game.world, e) == 3
    }
    assert crypt_keys, "crypt must have monsters"
    allowed = {k for k, d in game.bestiary.items() if "kurhany" in d.biomes}
    assert crypt_keys <= allowed


def test_village_is_safe_and_staffed() -> None:
    from wyraj.core.components import Villager

    game = Game(seed=42)
    assert not [e for e in game.world.entities_with(AI) if level_of(game.world, e) == 0]
    roles = {game.world.expect(e, Villager).role for e, _ in game.world.query(Villager)}
    assert roles == {"innkeeper", "trader", "gossip", "kowal", "mlynarz"}


def test_goto_depth_helper_darkness() -> None:
    game = Game(seed=42)
    goto_depth(game, 3)
    assert game.depth == 3
    assert game.in_darkness
