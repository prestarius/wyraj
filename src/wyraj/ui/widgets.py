"""Map and character-panel widgets. Read game state; never mutate it."""

from rich.text import Text
from textual.widgets import Static

from wyraj.core.components import Health, Position, Renderable
from wyraj.core.game import Game
from wyraj.core.map import Tile

# (unicode, ascii) glyphs per terrain
TREE_GLYPHS = ("♣", "#")
FLOOR_GLYPHS = ("·", ".")

PORTRAIT = """\
   ▄▄▄▄▄
  ▟█████▙
  █▓▒░▒▓█
  ▀▜███▛▀
 ▄███████▄
 █ ▒███▒ █
 ▛ ▒███▒ ▜
   ▐█▌▐█▌"""


class MapView(Static):
    def __init__(self, game: Game, use_ascii: bool = False) -> None:
        super().__init__()
        self.game = game
        self.use_ascii = use_ascii

    def render(self) -> Text:
        game = self.game
        glyph_index = 1 if self.use_ascii else 0
        tree = TREE_GLYPHS[glyph_index]
        floor = FLOOR_GLYPHS[glyph_index]

        entities: dict[tuple[int, int], Renderable] = {}
        for _entity, (pos, renderable) in game.world.query(Position, Renderable):
            entities[(pos.x, pos.y)] = renderable

        text = Text()
        for y in range(game.map.height):
            for x in range(game.map.width):
                cell = (x, y)
                if cell in game.map.visible:
                    renderable = entities.get(cell)
                    if renderable is not None:
                        glyph = (
                            renderable.ascii_glyph
                            if self.use_ascii and renderable.ascii_glyph
                            else renderable.glyph
                        )
                        text.append(glyph, style=renderable.style)
                    elif game.map.tiles[y][x] is Tile.WALL:
                        text.append(tree, style="dark_green")
                    else:
                        text.append(floor, style="grey58")
                elif cell in game.map.explored:
                    terrain = tree if game.map.tiles[y][x] is Tile.WALL else floor
                    text.append(terrain, style="grey23")
                else:
                    text.append(" ")
            if y < game.map.height - 1:
                text.append("\n")
        return text


class CharacterPanel(Static):
    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game

    def render(self) -> Text:
        game = self.game
        health = game.world.expect(game.player, Health)
        text = Text()
        text.append(PORTRAIT, style="grey74")
        text.append("\n\n")
        text.append(" Wędrowiec\n", style="bold")
        text.append(f" Turn {game.turn}\n\n", style="grey58")
        text.append(" HP ")
        bar_width = 14
        filled = round(health.fraction * bar_width)
        frac = health.fraction
        hp_style = "green" if frac > 0.5 else "yellow" if frac > 0.25 else "red"
        text.append("█" * filled, style=hp_style)
        text.append("░" * (bar_width - filled), style="grey23")
        text.append(f" {health.hp}/{health.max_hp}\n")
        return text
