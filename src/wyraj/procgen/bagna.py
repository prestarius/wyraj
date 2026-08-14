"""Bagna (marsh) map generation: moisture blobs of open water in reed flats.

Pure function of (seed, params). Water is transparent but unwalkable for
anything that cannot swim; the walkable floor is guaranteed connected.
"""

import random

from wyraj.core.map import GameMap, Tile


def generate_bagna(
    seed: int,
    width: int = 54,
    height: int = 32,
    pool_count: int = 10,
    pool_size: int = 40,
    reed_prob: float = 0.10,
) -> GameMap:
    rng = random.Random(seed)
    tiles = [[Tile.FLOOR for _x in range(width)] for _y in range(height)]

    def border(x: int, y: int) -> bool:
        return x in (0, width - 1) or y in (0, height - 1)

    # Reed thickets: sparse scattered walls.
    for y in range(height):
        for x in range(width):
            if border(x, y) or rng.random() < reed_prob:
                tiles[y][x] = Tile.WALL

    # Moisture: random-walk pools of open water.
    for _ in range(pool_count):
        px = rng.randint(2, width - 3)
        py = rng.randint(2, height - 3)
        for _ in range(pool_size):
            if not border(px, py):
                tiles[py][px] = Tile.WATER
            px = min(max(px + rng.choice((-1, 0, 1)), 1), width - 2)
            py = min(max(py + rng.choice((-1, 0, 1)), 1), height - 2)

    _keep_largest_floor_region(tiles, width, height)

    floors = [(x, y) for y in range(height) for x in range(width) if tiles[y][x] is Tile.FLOOR]
    ux, uy = rng.choice(floors)
    tiles[uy][ux] = Tile.STAIRS_UP
    dx_, dy_ = max(
        (t for t in floors if t != (ux, uy)),
        key=lambda t: abs(t[0] - ux) + abs(t[1] - uy),
    )
    tiles[dy_][dx_] = Tile.STAIRS_DOWN

    return GameMap(tiles, biome="bagna")


def _keep_largest_floor_region(tiles: list[list[Tile]], width: int, height: int) -> None:
    """Reeds swallow every walkable pocket except the largest one."""
    seen: set[tuple[int, int]] = set()
    largest: set[tuple[int, int]] = set()
    for y in range(height):
        for x in range(width):
            if tiles[y][x] is not Tile.FLOOR or (x, y) in seen:
                continue
            region: set[tuple[int, int]] = set()
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (
                    (cx, cy) in region
                    or not (0 <= cx < width and 0 <= cy < height)
                    or tiles[cy][cx] is not Tile.FLOOR
                ):
                    continue
                region.add((cx, cy))
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
            seen |= region
            if len(region) > len(largest):
                largest = region
    for y in range(height):
        for x in range(width):
            if tiles[y][x] is Tile.FLOOR and (x, y) not in largest:
                tiles[y][x] = Tile.WALL
