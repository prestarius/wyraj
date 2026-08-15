"""Map and character-panel widgets. Read game state; never mutate it."""

from rich.text import Text
from textual.widgets import Static

from wyraj.core.components import (
    Health,
    Hunger,
    Item,
    LightSource,
    Lore,
    Position,
    Purse,
    Renderable,
    StatusEffects,
    Wearing,
    Wielding,
)
from wyraj.core.game import Game
from wyraj.core.map import Tile
from wyraj.core.systems.movement import level_of
from wyraj.ui.i18n import current_language, t
from wyraj.ui.portrait import hp_band, render_portrait

# (unicode, ascii) glyphs per terrain, keyed by biome
WALL_GLYPHS = {
    "puszcza": ("♣", "#"),
    "kurhany": ("▒", "#"),
    "bagna": ('"', '"'),
    "wies": ("#", "#"),
}
WALL_STYLES = {
    "puszcza": "dark_green",
    "kurhany": "grey39",
    "bagna": "dark_olive_green3",
    "wies": "tan",
}
FLOOR_GLYPHS = ("·", ".")
WATER_GLYPHS = ("≈", "~")
SHAFT_GLYPHS = ("◌", "o")
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
        if tile is Tile.WATER:
            return WATER_GLYPHS[glyph_index]
        if tile is Tile.SHAFT:
            return SHAFT_GLYPHS[glyph_index]
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
                    elif tile is Tile.WATER:
                        text.append(self._terrain_glyph(tile), style="deep_sky_blue4")
                    elif tile is Tile.SHAFT:
                        text.append(self._terrain_glyph(tile), style="light_sky_blue3")
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
    def __init__(self, game: Game, portrait_style: str = "box") -> None:
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
        text.append(
            f" {game.origin.name}, {game.origin.title_for(current_language())}\n", style="bold"
        )
        places = {0: t("place_wies"), 1: t("place_puszcza"), 2: t("place_bagna")}
        place = places.get(game.depth, t("place_kurhan", n=game.depth - 2))
        text.append(f" {place}\n", style="grey58")
        text.append(f" {t('turn', n=game.turn)}\n\n", style="grey58")
        text.append(" HP ")
        bar_width = 14
        filled = round(health.fraction * bar_width)
        frac = health.fraction
        hp_style = "green" if frac > 0.5 else "yellow" if frac > 0.25 else "red"
        text.append("█" * filled, style=hp_style)
        text.append("░" * (bar_width - filled), style="grey23")
        text.append(f" {health.hp}/{health.max_hp}\n")

        purse = game.world.get(game.player, Purse)
        if purse is not None:
            text.append(f"\n {t('purse', n=purse.denary)}\n", style="gold3")
            text.append(f" {t('banked', n=game.meta.currency.denary)}\n", style="grey58")

        hunger = game.world.get(game.player, Hunger)
        if hunger is not None:
            band_styles = {"sated": "grey58", "hungry": "yellow", "starving": "bold red"}
            text.append(f"\n {t('hunger_' + hunger.band)}\n", style=band_styles[hunger.band])

        wielding = game.world.get(game.player, Wielding)
        if wielding is not None and wielding.item is not None:
            lore = game.world.get(wielding.item, Lore)
            if lore is not None:
                text.append(f" {t('wields', name=lore.name)}\n", style="grey66")

        wearing = game.world.get(game.player, Wearing)
        if wearing is not None and wearing.item is not None:
            armor_lore = game.world.get(wearing.item, Lore)
            if armor_lore is not None:
                text.append(f" {t('wears', name=armor_lore.name)}\n", style="grey66")

        statuses = game.world.get(game.player, StatusEffects)
        if statuses is not None and statuses.effects:
            status_styles = {
                "bleeding": "red3",
                "poison": "chartreuse4",
                "fear": "medium_purple3",
                "blessing": "light_goldenrod2",
            }
            text.append("\n")
            for effect in statuses.effects:
                style = status_styles.get(effect.kind, "grey66")
                label = t("status_" + effect.kind)
                text.append(f" {label} ({effect.duration})\n", style=style)

        light = game.world.get(game.player, LightSource)
        if light is not None:
            text.append(f"\n {t('gromnica_meter', n=light.turns)}\n", style="light_goldenrod2")
        return text
