from wyraj.core.map import Tile
from wyraj.procgen.kurhany import generate_kurhan


def test_deterministic() -> None:
    assert generate_kurhan(7).tiles == generate_kurhan(7).tiles
    assert generate_kurhan(7).tiles != generate_kurhan(8).tiles


def test_stairs_placement() -> None:
    m = generate_kurhan(7)
    assert m.find_tile(Tile.STAIRS_UP) is not None
    assert m.find_tile(Tile.STAIRS_DOWN) is not None
    bottom = generate_kurhan(7, with_down_stairs=False)
    assert bottom.find_tile(Tile.STAIRS_UP) is not None
    assert bottom.find_tile(Tile.STAIRS_DOWN) is None


def test_biome_and_borders() -> None:
    m = generate_kurhan(7)
    assert m.biome == "kurhany"
    for x in range(m.width):
        assert m.tiles[0][x] is Tile.WALL
        assert m.tiles[m.height - 1][x] is Tile.WALL


def test_walkable_area_is_connected() -> None:
    m = generate_kurhan(7)
    walkable = {(x, y) for y in range(m.height) for x in range(m.width) if m.is_walkable(x, y)}
    assert len(walkable) > 50
    start = next(iter(walkable))
    reached: set[tuple[int, int]] = set()
    stack = [start]
    while stack:
        x, y = stack.pop()
        if (x, y) in reached or (x, y) not in walkable:
            continue
        reached.add((x, y))
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    assert reached == walkable
