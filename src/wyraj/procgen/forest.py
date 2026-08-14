"""Puszcza (primeval forest) map generation: cellular automata.

Pure function of (seed, params) — never touches shared RNG state.
"""

import random

from wyraj.core.map import GameMap, Tile


def generate_forest(
    seed: int,
    width: int = 60,
    height: int = 36,
    tree_prob: float = 0.42,
    steps: int = 4,
) -> GameMap:
    rng = random.Random(seed)
    walls = [
        [
            True if _is_border(x, y, width, height) else rng.random() < tree_prob
            for x in range(width)
        ]
        for y in range(height)
    ]

    for _ in range(steps):
        walls = _smooth(walls, width, height)

    walls = _keep_largest_cavern(walls, width, height)

    tiles = [
        [Tile.WALL if walls[y][x] else Tile.FLOOR for x in range(width)] for y in range(height)
    ]
    return GameMap(tiles)


def _is_border(x: int, y: int, width: int, height: int) -> bool:
    return x in (0, width - 1) or y in (0, height - 1)


def _neighbor_walls(walls: list[list[bool]], x: int, y: int, width: int, height: int) -> int:
    count = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height) or walls[ny][nx]:
                count += 1
    return count


def _smooth(walls: list[list[bool]], width: int, height: int) -> list[list[bool]]:
    return [
        [
            True
            if _is_border(x, y, width, height)
            else _neighbor_walls(walls, x, y, width, height) >= 5
            for x in range(width)
        ]
        for y in range(height)
    ]


def _keep_largest_cavern(walls: list[list[bool]], width: int, height: int) -> list[list[bool]]:
    """Flood-fill open regions; wall off everything but the largest."""
    seen: set[tuple[int, int]] = set()
    largest: set[tuple[int, int]] = set()
    for y in range(height):
        for x in range(width):
            if walls[y][x] or (x, y) in seen:
                continue
            region = _flood(walls, x, y, width, height)
            seen |= region
            if len(region) > len(largest):
                largest = region
    return [[walls[y][x] or (x, y) not in largest for x in range(width)] for y in range(height)]


def _flood(
    walls: list[list[bool]], x: int, y: int, width: int, height: int
) -> set[tuple[int, int]]:
    region: set[tuple[int, int]] = set()
    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in region or not (0 <= cx < width and 0 <= cy < height) or walls[cy][cx]:
            continue
        region.add((cx, cy))
        stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
    return region
