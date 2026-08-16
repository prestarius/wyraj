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
from wyraj.ui.item_info import display_name, stat_suffix
from wyraj.ui.portrait import PortraitState, compose_portrait, get_art, hp_band

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
FLOOR_STYLES = {
    "wies": "#93856b",
    "puszcza": "#7d8a6e",
    "bagna": "#7e8154",
    "kurhany": "#6f7a85",
}
FLOOR_GLYPHS = ("·", ".")
WATER_GLYPHS = ("≈", "~")
SHAFT_GLYPHS = ("◌", "o")
STAIRS_DOWN_GLYPHS = (">", ">")
STAIRS_UP_GLYPHS = ("<", "<")


def place_label(game: Game) -> str:
    places = {0: t("place_wies"), 1: t("place_puszcza"), 2: t("place_bagna")}
    return places.get(game.depth, t("place_kurhan", n=game.depth - 2))


class MapView(Static):
    def __init__(self, game: Game, use_ascii: bool = False) -> None:
        super().__init__()
        self.game = game
        self.use_ascii = use_ascii
        self._damage_flash = False

    def flash_damage(self) -> None:
        """Briefly mark the player glyph after taking a hit (cosmetic only)."""
        self._damage_flash = True
        self.refresh()
        self.set_timer(0.2, self._clear_flash)

    def _clear_flash(self) -> None:
        self._damage_flash = False
        self.refresh()

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
        self.border_title = place_label(game)
        wall_style = WALL_STYLES.get(game.map.biome, "dark_green")
        floor_style = FLOOR_STYLES.get(game.map.biome, "grey58")
        player_pos = game.world.expect(game.player, Position)
        flash_cell = (player_pos.x, player_pos.y) if self._damage_flash else None

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
                        style = "bold white on red3" if cell == flash_cell else renderable.style
                        text.append(glyph, style=style)
                    elif tile is Tile.WALL:
                        text.append(self._terrain_glyph(tile), style=wall_style)
                    elif tile in (Tile.STAIRS_DOWN, Tile.STAIRS_UP):
                        text.append(self._terrain_glyph(tile), style="bold gold3")
                    elif tile is Tile.WATER:
                        text.append(self._terrain_glyph(tile), style="deep_sky_blue4")
                    elif tile is Tile.SHAFT:
                        text.append(self._terrain_glyph(tile), style="light_sky_blue3")
                    else:
                        text.append(self._terrain_glyph(tile), style=floor_style)
                elif cell in game.map.explored:
                    text.append(self._terrain_glyph(tile), style="grey23")
                else:
                    text.append(" ")
            if y < game.map.height - 1:
                text.append("\n")
        return text


class CharacterPanel(Static):
    def __init__(self, game: Game, portrait_style: str = "box", use_ascii: bool = False) -> None:
        super().__init__()
        self.game = game
        self.portrait_style = portrait_style
        self.use_ascii = use_ascii
        self.border_title = game.origin.name

    def _weapon_key(self) -> str | None:
        wielding = self.game.world.get(self.game.player, Wielding)
        if wielding is None or wielding.item is None:
            return None
        item = self.game.world.get(wielding.item, Item)
        return item.key if item else None

    def _portrait_state(self) -> PortraitState:
        game = self.game
        health = game.world.expect(game.player, Health)
        wearing = game.world.get(game.player, Wearing)
        statuses = game.world.get(game.player, StatusEffects)
        light = game.world.get(game.player, LightSource)
        return PortraitState(
            band=hp_band(health.fraction),
            origin=game.origin.key,
            weapon_key=self._weapon_key(),
            armored=wearing is not None and wearing.item is not None,
            halo=light is not None and light.turns > 0,
            statuses=tuple(e.kind for e in statuses.effects) if statuses else (),
            scars=0,  # blizna tracking lands in US 10.5
        )

    def render(self) -> Text:
        game = self.game
        health = game.world.expect(game.player, Health)
        text = Text()
        text.append(
            compose_portrait(self._portrait_state(), get_art(self.portrait_style, self.use_ascii))
        )
        text.append("\n\n")
        text.append(
            f" {game.origin.name}, {game.origin.title_for(current_language())}\n", style="bold"
        )
        text.append(f" {place_label(game)}\n", style="grey58")
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
                definition = game.items_catalog.get(lore.key)
                name = display_name(definition, fallback=lore.name)
                text.append(f" {t('wields', name=name)}", style="grey66")
                suffix = stat_suffix(definition)
                if suffix:
                    text.append(f" {suffix}", style="grey58")
                text.append("\n")

        wearing = game.world.get(game.player, Wearing)
        if wearing is not None and wearing.item is not None:
            armor_lore = game.world.get(wearing.item, Lore)
            if armor_lore is not None:
                definition = game.items_catalog.get(armor_lore.key)
                name = display_name(definition, fallback=armor_lore.name)
                text.append(f" {t('wears', name=name)}", style="grey66")
                suffix = stat_suffix(definition)
                if suffix:
                    text.append(f" {suffix}", style="grey58")
                text.append("\n")

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
