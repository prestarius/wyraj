"""Legend rendering: what every glyph on the map means.

Pure text builder (like codex_view) so it stays unit-testable without Pilot.
Creatures appear only once the codex knows them — the legend must not spoil
"a shape not yet seen".
"""

from collections.abc import Callable

from rich.text import Text

from wyraj.content.bestiary import MonsterDef
from wyraj.content.items import ItemDef
from wyraj.ui.i18n import t
from wyraj.ui.item_info import display_name
from wyraj.ui.widgets import (
    FLOOR_GLYPHS,
    SHAFT_GLYPHS,
    STAIRS_DOWN_GLYPHS,
    STAIRS_UP_GLYPHS,
    WALL_GLYPHS,
    WALL_STYLES,
    WATER_GLYPHS,
)

Row = tuple[str, str, str]  # glyph, style, label


def _merge_duplicates(rows: list[Row]) -> list[Row]:
    """In ascii mode several glyphs collapse (e.g. every wall is '#')."""
    out: list[Row] = []
    index: dict[str, int] = {}
    for glyph, style, label in rows:
        if glyph in index:
            kept_glyph, kept_style, kept_label = out[index[glyph]]
            out[index[glyph]] = (kept_glyph, kept_style, f"{kept_label}, {label}")
        else:
            index[glyph] = len(out)
            out.append((glyph, style, label))
    return out


def build_legend_text(
    items_catalog: dict[str, ItemDef],
    bestiary: dict[str, MonsterDef],
    tier_of: Callable[[str], str],
    use_ascii: bool = False,
) -> Text:
    g = 1 if use_ascii else 0
    terrain: list[Row] = [
        (FLOOR_GLYPHS[g], "grey58", t("legend_ground")),
        (WALL_GLYPHS["puszcza"][g], WALL_STYLES["puszcza"], t("legend_trees")),
        (WALL_GLYPHS["bagna"][g], WALL_STYLES["bagna"], t("legend_reeds")),
        (WALL_GLYPHS["kurhany"][g], WALL_STYLES["kurhany"], t("legend_barrow")),
        (WALL_GLYPHS["wies"][g], WALL_STYLES["wies"], t("legend_walls")),
        (WATER_GLYPHS[g], "deep_sky_blue4", t("legend_water")),
        (SHAFT_GLYPHS[g], "light_sky_blue3", t("legend_shaft")),
        (STAIRS_DOWN_GLYPHS[g], "bold gold3", t("legend_down")),
        (STAIRS_UP_GLYPHS[g], "bold gold3", t("legend_up")),
    ]
    # These mirror the Renderables hardcoded in core/game.py spawns.
    places: list[Row] = [
        (("☺", "P")[g], "light_goldenrod2", t("legend_villager")),
        (("▣", "8")[g], "gold3", t("legend_skrzynia")),
        (("⊥", "T")[g], "grey66", t("legend_perch")),
        (("Λ", "^")[g], "light_goldenrod2", t("legend_shrine_perun")),
        (("Ω", "O")[g], "light_goldenrod2", t("legend_shrine_weles")),
        ("$", "gold3", t("legend_coins")),
        (("⌖", "+")[g], "grey93", t("legend_znamie")),
    ]
    grouped: dict[str, tuple[str, list[str]]] = {}
    for definition in items_catalog.values():
        glyph = definition.ascii_glyph if use_ascii else definition.glyph
        if glyph not in grouped:
            grouped[glyph] = (definition.style, [])
        grouped[glyph][1].append(display_name(definition))
    items: list[Row] = [
        (glyph, style, ", ".join(names)) for glyph, (style, names) in sorted(grouped.items())
    ]
    creatures: list[Row] = []
    for key in sorted(bestiary):
        monster = bestiary[key]
        if tier_of(key) == "unknown":
            continue
        glyph = monster.ascii_glyph if use_ascii else monster.glyph
        creatures.append((glyph, monster.style, display_name(monster)))

    text = Text()
    text.append(t("legend_title") + "\n\n", style="bold")
    text.append(" @", style="bold white")
    text.append(f"  {t('legend_you')}\n\n")
    for header, rows in (
        ("legend_terrain", terrain),
        ("legend_places", places),
        ("legend_items", items),
        ("legend_creatures", creatures),
    ):
        text.append(t(header) + "\n", style="grey58")
        if not rows:
            text.append(" " + t("legend_creatures_none") + "\n", style="grey42")
        for glyph, style, label in _merge_duplicates(rows):
            text.append(f" {glyph}", style=style)
            text.append(f"  {label}\n")
        text.append("\n")
    text.append(t("legend_examine_hint") + "\n", style="grey42")
    text.append("\n" + t("esc_close"), style="grey42")
    return text
