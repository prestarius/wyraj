from wyraj.core.map import Tile
from wyraj.procgen.forest import generate_forest


def test_deterministic_for_seed() -> None:
    a = generate_forest(42)
    b = generate_forest(42)
    assert a.tiles == b.tiles


def test_different_seeds_differ() -> None:
    assert generate_forest(1).tiles != generate_forest(2).tiles


def test_borders_are_walls() -> None:
    m = generate_forest(42)
    for x in range(m.width):
        assert m.tiles[0][x] is Tile.WALL
        assert m.tiles[m.height - 1][x] is Tile.WALL
    for y in range(m.height):
        assert m.tiles[y][0] is Tile.WALL
        assert m.tiles[y][m.width - 1] is Tile.WALL


def test_floor_is_one_connected_cavern() -> None:
    m = generate_forest(42)
    floors = {(x, y) for y in range(m.height) for x in range(m.width) if m.is_walkable(x, y)}
    assert len(floors) > 100, "map should be mostly playable space"
    start = next(iter(floors))
    reached = set()
    stack = [start]
    while stack:
        x, y = stack.pop()
        if (x, y) in reached or (x, y) not in floors:
            continue
        reached.add((x, y))
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    assert reached == floors
