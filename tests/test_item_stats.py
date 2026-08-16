"""The inventory/trade/stash stat suffixes: every stat-bearing item shows one."""

from collections.abc import Iterator

import pytest

from wyraj.content.items import ItemDef, load_items
from wyraj.ui import i18n
from wyraj.ui.item_info import stat_suffix


@pytest.fixture(autouse=True)
def _restore_language() -> Iterator[None]:
    yield
    i18n.set_language("en")


def _weapon(damage: int = 5) -> ItemDef:
    return ItemDef(
        key="w", name="test axe", glyph=")", ascii_glyph=")", kind="weapon", damage=damage
    )


def test_suffix_en() -> None:
    i18n.set_language("en")
    assert stat_suffix(_weapon()) == "(damage 5)"
    armor = ItemDef(
        key="a", name="test coat", glyph="[", ascii_glyph="[", kind="armor", protection=2
    )
    assert stat_suffix(armor) == "(protection 2)"
    potion = ItemDef(
        key="p",
        name="test odwar",
        glyph="!",
        ascii_glyph="!",
        kind="consumable",
        effect="heal",
        power=8,
    )
    assert stat_suffix(potion) == "(heals 8)"


def test_suffix_pl() -> None:
    i18n.set_language("pl")
    assert stat_suffix(_weapon()) == "(obrażenia 5)"


def test_suffix_empty_for_statless() -> None:
    trophy = ItemDef(key="t", name="test claw", glyph="*", ascii_glyph="*", kind="trophy")
    assert stat_suffix(trophy) == ""
    assert stat_suffix(None) == ""


def test_every_stat_bearing_item_in_data_gets_a_suffix() -> None:
    # Crane feathers are the one sanctioned exception: power is channel time.
    for key, definition in load_items().items():
        if definition.kind in ("trophy", "trinket") or definition.effect == "crane":
            continue
        assert stat_suffix(definition), f"{key} ({definition.kind}) renders no stat suffix"
