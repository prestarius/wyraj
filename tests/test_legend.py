"""The glyph legend: full terrain/item coverage, codex-gated creatures."""

from collections.abc import Iterator

import pytest

from wyraj.content.bestiary import load_bestiary
from wyraj.content.items import load_items
from wyraj.ui import i18n
from wyraj.ui.legend_view import build_legend_text


@pytest.fixture(autouse=True)
def _restore_language() -> Iterator[None]:
    yield
    i18n.set_language("en")


def test_unknown_creatures_stay_hidden() -> None:
    text = build_legend_text(load_items(), load_bestiary(), tier_of=lambda _key: "unknown")
    plain = text.plain
    assert "None yet." in plain
    for definition in load_bestiary().values():
        # Item names may embed a monster's name ("wolf pelt") — check the row.
        assert f" {definition.glyph}  {definition.name}" not in plain


def test_known_creatures_appear_with_pl_names() -> None:
    i18n.set_language("pl")
    bestiary = load_bestiary()
    text = build_legend_text(load_items(), bestiary, tier_of=lambda _key: "full")
    plain = text.plain
    assert "— Legenda —" in plain
    for definition in bestiary.values():
        mian = definition.forms["pl"]["mian"]
        assert isinstance(mian, str)
        assert mian in plain


def test_every_item_glyph_listed() -> None:
    items = load_items()
    plain = build_legend_text(items, load_bestiary(), tier_of=lambda _key: "unknown").plain
    for definition in items.values():
        assert f" {definition.glyph}  " in plain or f", {definition.name}" in plain
        assert definition.name in plain


def test_ascii_mode_merges_colliding_wall_glyphs() -> None:
    plain = build_legend_text(
        load_items(), load_bestiary(), tier_of=lambda _key: "unknown", use_ascii=True
    ).plain
    # puszcza/kurhany/wieś walls all render '#' in ascii — one merged row, not three.
    assert plain.count(" #  ") == 1
    assert "♣" not in plain
