"""Map and character-panel widgets. Read game state; never mutate it."""

from rich.text import Text
from textual.widgets import Static

from wyraj.core.components import Health, Hunger, Item, Lore, Position, Renderable, Wielding
from wyraj.core.game import Game
from wyraj.core.map import Tile
from wyraj.ui.portrait import hp_band, render_portrait

# (unicode, ascii) glyphs per terrain
TREE_GLYPHS = ("♣", "#")
FLOOR_GLYPHS = ("·", ".")


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

        # Items first, creatures second — creatures draw on top.
        entities: dict[tuple[int, int], Renderable] = {}
        for entity, (pos, renderable) in game.world.query(Position, Renderable):
            if not game.world.has(entity, Health):
                entities[(pos.x, pos.y)] = renderable
        for entity, (pos, renderable) in game.world.query(Position, Renderable):
            if game.world.has(entity, Health):
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
    def __init__(self, game: Game, portrait_style: str = "half") -> None:
        super().__init__()
        self.game = game
        self.portrait_style = portrait_style

    def _weapon_key(self) -> str | None:
        wielding = self.game.world.get(self.game.player, Wielding)
        if wielding is None or wielding.item is None:
            return None
        item = self.game.world.get(wielding.item, Item)
        return item.key if item else None

    def render(self) -> Text:
        game = self.game
        health = game.world.expect(game.player, Health)
        text = Text()
        text.append(
            render_portrait(self.portrait_style, hp_band(health.fraction), self._weapon_key())
        )
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

        hunger = game.world.get(game.player, Hunger)
        if hunger is not None:
            band_styles = {"sated": "grey58", "hungry": "yellow", "starving": "bold red"}
            text.append(f"\n {hunger.band.capitalize()}\n", style=band_styles[hunger.band])

        wielding = game.world.get(game.player, Wielding)
        if wielding is not None and wielding.item is not None:
            lore = game.world.get(wielding.item, Lore)
            if lore is not None:
                text.append(f" Wields: {lore.name}\n", style="grey66")
        return text
