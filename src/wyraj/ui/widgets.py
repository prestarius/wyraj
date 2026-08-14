"""Map and character-panel widgets. Read game state; never mutate it."""

from rich.text import Text
from textual.widgets import Static

from wyraj.core.components import Health, Hunger, Item, Lore, Position, Renderable, Wielding
from wyraj.core.game import Game
from wyraj.core.map import Tile
from wyraj.core.systems.movement import level_of
from wyraj.ui.portrait import hp_band, render_portrait

# (unicode, ascii) glyphs per terrain, keyed by biome
WALL_GLYPHS = {"puszcza": ("♣", "#"), "kurhany": ("▒", "#")}
WALL_STYLES = {"puszcza": "dark_green", "kurhany": "grey39"}
FLOOR_GLYPHS = ("·", ".")
STAIRS_DOWN_GLYPHS = (">", ">")
STAIRS_UP_GLYPHS = ("<", "<")


class MapView(Static):
    def __init__(self, game: Game, use_ascii: bool = False) -> None:
        super().__init__()
        self.game = game
        self.use_ascii = use_ascii

    def _terrain_glyph(self, tile: Tile) -> str:
        glyph_index = 1 if self.use_ascii else 0
        biome = self.game.map.biome
        if tile is Tile.WALL:
            return WALL_GLYPHS.get(biome, WALL_GLYPHS["puszcza"])[glyph_index]
        if tile is Tile.STAIRS_DOWN:
            return STAIRS_DOWN_GLYPHS[glyph_index]
        if tile is Tile.STAIRS_UP:
            return STAIRS_UP_GLYPHS[glyph_index]
        return FLOOR_GLYPHS[glyph_index]

    def render(self) -> Text:
        game = self.game
        wall_style = WALL_STYLES.get(game.map.biome, "dark_green")

        # Items first, creatures second — creatures draw on top.
        entities: dict[tuple[int, int], Renderable] = {}
        for entity, (pos, renderable) in game.world.query(Position, Renderable):
            if level_of(game.world, entity) == game.depth and not game.world.has(entity, Health):
                entities[(pos.x, pos.y)] = renderable
        for entity, (pos, renderable) in game.world.query(Position, Renderable):
            if level_of(game.world, entity) == game.depth and game.world.has(entity, Health):
                entities[(pos.x, pos.y)] = renderable

        text = Text()
        for y in range(game.map.height):
            for x in range(game.map.width):
                cell = (x, y)
                tile = game.map.tiles[y][x]
                if cell in game.map.visible:
                    renderable = entities.get(cell)
                    if renderable is not None:
                        glyph = (
                            renderable.ascii_glyph
                            if self.use_ascii and renderable.ascii_glyph
                            else renderable.glyph
                        )
                        text.append(glyph, style=renderable.style)
                    elif tile is Tile.WALL:
                        text.append(self._terrain_glyph(tile), style=wall_style)
                    elif tile in (Tile.STAIRS_DOWN, Tile.STAIRS_UP):
                        text.append(self._terrain_glyph(tile), style="bold gold3")
                    else:
                        text.append(self._terrain_glyph(tile), style="grey58")
                elif cell in game.map.explored:
                    text.append(self._terrain_glyph(tile), style="grey23")
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
        place = "Puszcza" if game.depth == 0 else f"Kurhan, poziom {game.depth}"
        text.append(f" {place}\n", style="grey58")
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
