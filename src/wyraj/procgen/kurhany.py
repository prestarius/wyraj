"""Kurhany (barrow-crypt) map generation: BSP rooms under the mounds.

Pure function of (seed, params). Every crypt has an up-stair; all but the
deepest also get a down-stair, placed in rooms far apart from each other.
"""

import itertools
import random
from dataclasses import dataclass

from wyraj.core.map import GameMap, Tile

MIN_LEAF = 7  # smallest BSP leaf that still fits a room


@dataclass(frozen=True)
class _Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


def generate_kurhan(
    seed: int,
    width: int = 48,
    height: int = 30,
    with_down_stairs: bool = True,
) -> GameMap:
    rng = random.Random(seed)
    tiles = [[Tile.WALL for _x in range(width)] for _y in range(height)]
    rooms: list[_Room] = []

    def carve_room(room: _Room) -> None:
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                tiles[y][x] = Tile.FLOOR

    def carve_corridor(a: tuple[int, int], b: tuple[int, int]) -> None:
        (ax, ay), (bx, by) = a, b
        if rng.random() < 0.5:
            _h_line(ax, bx, ay)
            _v_line(ay, by, bx)
        else:
            _v_line(ay, by, ax)
            _h_line(ax, bx, by)

    def _h_line(x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            tiles[y][x] = Tile.FLOOR

    def _v_line(y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            tiles[y][x] = Tile.FLOOR

    def split(x: int, y: int, w: int, h: int) -> None:
        can_h = h >= MIN_LEAF * 2
        can_v = w >= MIN_LEAF * 2
        if not can_h and not can_v:
            room_w = rng.randint(3, max(3, w - 3))
            room_h = rng.randint(3, max(3, h - 3))
            room_x = x + rng.randint(1, max(1, w - room_w - 1))
            room_y = y + rng.randint(1, max(1, h - room_h - 1))
            room = _Room(room_x, room_y, room_w, room_h)
            carve_room(room)
            rooms.append(room)
            return
        if can_h and (not can_v or rng.random() < 0.5):
            cut = rng.randint(MIN_LEAF, h - MIN_LEAF)
            split(x, y, w, cut)
            split(x, y + cut, w, h - cut)
        else:
            cut = rng.randint(MIN_LEAF, w - MIN_LEAF)
            split(x, y, cut, h)
            split(x + cut, y, w - cut, h)

    # Keep a 1-tile border of solid stone.
    split(1, 1, width - 2, height - 2)

    for a, b in itertools.pairwise(rooms):
        carve_corridor(a.center, b.center)

    up_room = rooms[0]
    down_room = max(
        rooms[1:] or rooms,
        key=lambda r: abs(r.center[0] - up_room.center[0]) + abs(r.center[1] - up_room.center[1]),
    )
    ux, uy = up_room.center
    tiles[uy][ux] = Tile.STAIRS_UP
    if with_down_stairs:
        dx, dy = down_room.center
        tiles[dy][dx] = Tile.STAIRS_DOWN

    # 1-2 collapsed-ceiling shafts: light wells and the only open sky down
    # here (crane flight, spec M6 §6.2).
    floors = [(x, y) for y in range(height) for x in range(width) if tiles[y][x] is Tile.FLOOR]
    for sx, sy in rng.sample(floors, min(rng.randint(1, 2), len(floors))):
        tiles[sy][sx] = Tile.SHAFT

    return GameMap(tiles, biome="kurhany")
