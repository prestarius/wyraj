import random

from wyraj.core.fov import compute_fov
from wyraj.core.map import GameMap, Tile


def map_from_ascii(art: str) -> GameMap:
    rows = [line for line in art.strip().splitlines()]
    tiles = [[Tile.WALL if ch == "#" else Tile.FLOOR for ch in row] for row in rows]
    return GameMap(tiles)


def visible_from(m: GameMap, origin: tuple[int, int], radius: int = 12) -> set[tuple[int, int]]:
    return compute_fov(origin, radius, is_blocking=lambda x, y: not m.is_transparent(x, y))


def test_open_room_fully_visible() -> None:
    m = map_from_ascii(
        """
#####
#...#
#...#
#...#
#####
"""
    )
    vis = visible_from(m, (2, 2), radius=10)
    for x, y in m.floor_tiles():
        assert (x, y) in vis


def test_wall_blocks_sight() -> None:
    m = map_from_ascii(
        """
#######
#..#..#
#######
"""
    )
    vis = visible_from(m, (1, 1), radius=10)
    assert (2, 1) in vis
    assert (3, 1) in vis  # the blocking wall itself is revealed
    assert (4, 1) not in vis
    assert (5, 1) not in vis


def test_symmetry_between_floor_tiles() -> None:
    rng = random.Random(7)
    for _ in range(5):
        tiles = [
            [Tile.WALL if rng.random() < 0.3 else Tile.FLOOR for _ in range(12)] for _ in range(12)
        ]
        m = GameMap(tiles)
        floors = m.floor_tiles()
        fov = {origin: visible_from(m, origin, radius=20) for origin in floors}
        for a in floors:
            for b in floors:
                assert (b in fov[a]) == (a in fov[b]), f"asymmetric: {a} vs {b}"


def test_radius_limits_view() -> None:
    m = GameMap([[Tile.FLOOR] * 30 for _ in range(3)])
    vis = visible_from(m, (0, 1), radius=5)
    assert (5, 1) in vis
    assert (6, 1) not in vis


def test_update_fov_tracks_explored() -> None:
    m = map_from_ascii(
        """
#######
#.....#
#######
"""
    )
    m.update_fov((1, 1), radius=2)
    first = set(m.visible)
    m.update_fov((5, 1), radius=2)
    assert m.explored >= first | m.visible
