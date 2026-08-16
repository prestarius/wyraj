"""The Dno vault (M8 §2.1): the authored hall at the bottom where the Wij lies.

Stamped like the village template — a fixed layout, deterministic regardless
of seed. Legend: '#' wall, '.' floor, '<' stairs up (the only way out),
'C' the stone cradle, 'N' a wall niche the sługi crawl out of. The pillar
pairs exist to break line of sight from the cradle — remember them.
"""

from dataclasses import dataclass

from wyraj.core.map import GameMap, Tile

_TEMPLATE = """
##############################################
#<...........................................#
#..........##......##......##................#
#............................................#
#N..........................................N#
#............................................#
#..........##......##......##......C.........#
#............................................#
#N..........................................N#
#............................................#
#..........##......##......##................#
#............................................#
##############################################
"""


@dataclass(frozen=True)
class VaultLayout:
    map: GameMap
    cradle: tuple[int, int]
    niches: tuple[tuple[int, int], ...]


def generate_vault(seed: int = 0) -> VaultLayout:
    """Authored, so `seed` is accepted only for signature symmetry."""
    rows = _TEMPLATE.strip("\n").split("\n")
    width = max(len(row) for row in rows)
    tiles: list[list[Tile]] = []
    cradle = (0, 0)
    niches: list[tuple[int, int]] = []
    for y, row in enumerate(rows):
        line: list[Tile] = []
        for x in range(width):
            char = row[x] if x < len(row) else "#"
            if char == "#":
                line.append(Tile.WALL)
                continue
            line.append(Tile.STAIRS_UP if char == "<" else Tile.FLOOR)
            if char == "C":
                cradle = (x, y)
            elif char == "N":
                niches.append((x, y))
        tiles.append(line)
    return VaultLayout(map=GameMap(tiles, biome="kurhany"), cradle=cradle, niches=tuple(niches))
