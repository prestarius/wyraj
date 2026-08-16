"""Examine (`x`) must describe features and terrain, not just beasts and food."""

from collections.abc import Iterator

import pytest

from wyraj.core.components import Lore, Position, Shrine, StashChest, Villager
from wyraj.core.game import FOV_RADIUS, Game
from wyraj.core.map import Tile
from wyraj.ui import i18n
from wyraj.ui.screens import build_examine_text


@pytest.fixture(autouse=True)
def _restore_language() -> Iterator[None]:
    yield
    i18n.set_language("en")


def _look_from(game: Game, x: int, y: int) -> str:
    game.world.add(game.player, Position(x, y))
    game.map.update_fov((x, y), FOV_RADIUS)
    return build_examine_text(game).plain


def test_shrines_and_skrzynia_show_with_descriptions() -> None:
    game = Game(seed=42)
    for component in (Shrine, StashChest):
        entity, (_c, pos) = next(iter(game.world.query(component, Position)))
        lore = game.world.expect(entity, Lore)
        assert lore.description, f"{lore.name} has no description to show"
        plain = _look_from(game, pos.x, pos.y)
        assert lore.name in plain
        assert lore.description[:30] in plain


def test_villagers_show_with_descriptions() -> None:
    game = Game(seed=42)
    entity, (_villager, pos) = next(iter(game.world.query(Villager, Position)))
    lore = game.world.expect(entity, Lore)
    plain = _look_from(game, pos.x, pos.y)
    assert lore.name in plain
    assert lore.description[:30] in plain


def test_visible_stairs_are_described() -> None:
    game = Game(seed=42)
    for y, row in enumerate(game.map.tiles):
        for x, tile in enumerate(row):
            if tile is Tile.STAIRS_DOWN:
                plain = _look_from(game, x, y)
                assert i18n.t("examine_stairs_down") in plain
                return
    raise AssertionError("village map has no down stairs?")
