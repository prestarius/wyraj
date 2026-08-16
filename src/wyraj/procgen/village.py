"""Wieś (village hub): semi-authored safe haven at the top of the world.

The layout is a fixed template — the village is home, and home does not
reshuffle. Returns the map plus NPC posts and the player start.
"""

from dataclasses import dataclass

from wyraj.core.map import GameMap, Tile

# '#' hut wall, '.' ground, '>' path into the puszcza,
# 'K' karczmarka (innkeeper), 'T' handlarz (trader), 'G' dziad (gossip),
# 'F' kowal (smith, at his open-air forge), 'M' młynarz (miller, in from his
# mill outside the palisade), 'S' skrzynia (stash chest), 'P' żerdź (crane
# perch), 'R' Perun shrine, 'W' Weles shrine, '@' player start.
_TEMPLATE = """
##############################
#.M..........................#
#..#####...#####....#####....#
#..#...#...#...#....#...#....#
#..#.K.#...#.T.#....#...#....#
#..#...#...#...#....#.G.#....#
#..##.##...##.##....##.##....#
#..........................R#
#..........................W#
#.............@..............#
#........................P...#
#...######...................#
#...#.S..#...................#
#...#....#..................>#
#...##.###...................#
#.F..........................#
##############################
"""


@dataclass(frozen=True)
class VillageLayout:
    map: GameMap
    player_start: tuple[int, int]
    npc_posts: tuple[tuple[str, int, int], ...]  # (role, x, y)
    special_posts: tuple[tuple[str, int, int], ...] = ()  # (kind, x, y)


_ROLES = {"K": "innkeeper", "T": "trader", "G": "gossip", "F": "kowal", "M": "mlynarz"}
_SPECIALS = {"S": "skrzynia", "P": "perch", "R": "shrine_perun", "W": "shrine_weles"}


def generate_village() -> VillageLayout:
    rows = [line for line in _TEMPLATE.strip("\n").splitlines()]
    width = max(len(r) for r in rows)
    tiles: list[list[Tile]] = []
    player_start = (1, 1)
    posts: list[tuple[str, int, int]] = []
    specials: list[tuple[str, int, int]] = []
    for y, row in enumerate(rows):
        tile_row: list[Tile] = []
        for x in range(width):
            ch = row[x] if x < len(row) else "#"
            if ch == "#":
                tile_row.append(Tile.WALL)
            elif ch == ">":
                tile_row.append(Tile.STAIRS_DOWN)
            else:
                tile_row.append(Tile.FLOOR)
                if ch == "@":
                    player_start = (x, y)
                elif ch in _ROLES:
                    posts.append((_ROLES[ch], x, y))
                elif ch in _SPECIALS:
                    specials.append((_SPECIALS[ch], x, y))
        tiles.append(tile_row)
    return VillageLayout(
        map=GameMap(tiles, biome="wies"),
        player_start=player_start,
        npc_posts=tuple(posts),
        special_posts=tuple(specials),
    )
