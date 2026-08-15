"""Tile map state: terrain grid plus FOV/exploration memory."""

from enum import Enum

from wyraj.core.fov import compute_fov


class Tile(Enum):
    WALL = "wall"  # dense trees / barrow stone / reed thicket, per biome
    FLOOR = "floor"
    WATER = "water"  # open marsh pools: see over, don't walk in (swimmers may)
    SHAFT = "shaft"  # collapsed crypt ceiling: floor with open sky above
    STAIRS_DOWN = "stairs_down"
    STAIRS_UP = "stairs_up"


WALKABLE = {Tile.FLOOR, Tile.SHAFT, Tile.STAIRS_DOWN, Tile.STAIRS_UP}


class GameMap:
    def __init__(self, tiles: list[list[Tile]], biome: str = "puszcza") -> None:
        self.tiles = tiles
        self.biome = biome
        self.height = len(tiles)
        self.width = len(tiles[0]) if tiles else 0
        self.visible: set[tuple[int, int]] = set()
        self.explored: set[tuple[int, int]] = set()

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.tiles[y][x] in WALKABLE

    def find_tile(self, tile: Tile) -> tuple[int, int] | None:
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] is tile:
                    return (x, y)
        return None

    def is_transparent(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.tiles[y][x] is not Tile.WALL

    def update_fov(self, origin: tuple[int, int], radius: int) -> None:
        self.visible = compute_fov(
            origin, radius, is_blocking=lambda x, y: not self.is_transparent(x, y)
        )
        self.visible = {(x, y) for x, y in self.visible if self.in_bounds(x, y)}
        self.explored |= self.visible

    def floor_tiles(self) -> list[tuple[int, int]]:
        """All plain floor tiles in row-major order (deterministic for spawning)."""
        return [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.tiles[y][x] is Tile.FLOOR
        ]
