# ruff: noqa: RUF001 — glyphs are deliberate
"""Equipment paper-doll (M7 US 10.2): a pure projection of the six slots.

Rows are built from `DollSlot` values the caller assembles out of ECS state —
the widget owns nothing. Heirlooms carry the ⟲ rune (spec §2.6); a lit
gromnica in the offhand shows its remaining burn turns (spec §3).
"""

from dataclasses import dataclass

from rich.text import Text

from wyraj.core.components import (
    Epithet,
    Item,
    ItemMemory,
    LightSource,
    Lore,
    Quickslots,
    Wearing,
    Wielding,
    WornExtras,
)
from wyraj.core.ecs import Entity
from wyraj.core.game import Game
from wyraj.core.systems.quickslots import count_of
from wyraj.ui.i18n import current_language, t
from wyraj.ui.item_info import display_name, stat_suffix

SLOTS = ("head", "torso", "weapon", "off", "amulet", "feet")

# slot → (unicode, ascii) glyph
_SLOT_GLYPHS = {
    "head": ("∩", "n"),
    "torso": ("▦", "#"),
    "weapon": ("†", "/"),
    "off": ("◐", "o"),
    "amulet": ("◆", "*"),
    "feet": ("⊔", "u"),
}
HEIRLOOM_RUNE = ("⟲", "&")


@dataclass(frozen=True)
class DollSlot:
    slot: str
    name: str | None = None  # None renders as an empty slot
    detail: str = ""  # stat suffix or burn counter, already localized
    heirloom: bool = False
    epithet: str | None = None  # named weapon (US 10.5)


def build_paper_doll(
    slots: tuple[DollSlot, ...], use_ascii: bool = False, max_name: int = 24
) -> Text:
    text = Text()
    text.append(t("doll_title") + "\n", style="grey58")
    glyph_index = 1 if use_ascii else 0
    for entry in slots:
        glyph = _SLOT_GLYPHS.get(entry.slot, ("?", "?"))[glyph_index]
        text.append(f" {glyph} ", style="grey66")
        text.append(f"{t('doll_' + entry.slot):<7}", style="grey58")
        if entry.name is None:
            text.append("-" if use_ascii else "—", style="grey42")
        else:
            name = entry.name
            if len(name) > max_name:
                name = name[: max_name - 1] + "…"
            text.append(name)
            if entry.epithet:
                text.append(f" „{entry.epithet}”", style="italic gold3")
            if entry.heirloom:
                text.append(f" {HEIRLOOM_RUNE[glyph_index]}", style="medium_purple3")
            if entry.detail:
                text.append(f" {entry.detail}", style="grey58")
        text.append("\n")
    return text


def _slot_entry(game: Game, slot: str, entity: Entity | None) -> DollSlot:
    if entity is None:
        return DollSlot(slot=slot)
    item = game.world.get(entity, Item)
    lore = game.world.get(entity, Lore)
    definition = game.items_catalog.get(item.key) if item is not None else None
    name = display_name(definition, fallback=lore.name if lore is not None else "something")
    epithet = None
    marker = game.world.get(entity, Epithet)
    if marker is not None:
        edef = game.epithets_catalog.get(marker.species)
        if edef is not None:
            epithet = edef.for_lang(current_language())
    return DollSlot(
        slot=slot,
        name=name,
        detail=stat_suffix(definition),
        heirloom=game.world.get(entity, ItemMemory) is not None,
        epithet=epithet,
    )


def doll_slots_for(game: Game) -> tuple[DollSlot, ...]:
    """The six paper-doll slots, read straight from ECS state."""
    world, player = game.world, game.player
    wielding = world.get(player, Wielding)
    wearing = world.get(player, Wearing)
    extras = world.get(player, WornExtras) or WornExtras()
    light = world.get(player, LightSource)
    if light is not None:
        off = DollSlot(
            slot="off",
            name=display_name(game.items_catalog.get("gromnica"), fallback="gromnica"),
            detail=t("doll_lit", n=light.turns),
        )
    else:
        off = DollSlot(slot="off")
    return (
        _slot_entry(game, "head", extras.head),
        _slot_entry(game, "torso", wearing.item if wearing is not None else None),
        _slot_entry(game, "weapon", wielding.item if wielding is not None else None),
        off,
        _slot_entry(game, "amulet", extras.amulet),
        _slot_entry(game, "feet", extras.feet),
    )


def build_quickslot_bar(game: Game, use_ascii: bool = False) -> Text:
    """The four "Podręczne" rows: keycap, name, stack count (dim when empty)."""
    slots = game.world.get(game.player, Quickslots) or Quickslots()
    text = Text()
    text.append(t("quickslot_title") + "\n", style="grey58")
    for index in range(4):
        key = slots.key_at(index)
        text.append(f" [{index + 1}]", style="bold gold3" if key else "grey42")
        if key is None:
            text.append(" -" if use_ascii else " —", style="grey42")
        else:
            count = count_of(game.world, game.player, key)
            name = display_name(game.items_catalog.get(key), fallback=key)
            text.append(f" {name} ", style="" if count else "grey42")
            times = "x" if use_ascii else "×"
            text.append(f"{times}{count}", style="gold3" if count else "grey42")
        text.append("\n")
    return text
