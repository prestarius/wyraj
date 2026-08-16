"""Localized stat suffixes so the player can compare items at a glance."""

from __future__ import annotations

from wyraj.content.items import ItemDef
from wyraj.ui.i18n import t

# "crane" is deliberately absent: its power is channel time, not a quality stat.
_EFFECT_KEYS = {
    "heal": "stat_heal",
    "feed": "stat_feed",
    "bless": "stat_bless",
    "light": "stat_light",
}


def stat_suffix(definition: ItemDef | None) -> str:
    """A "(damage 5)"-style suffix for an item, or "" when it has no stats."""
    if definition is None:
        return ""
    if definition.kind == "weapon" and definition.damage is not None:
        return t("stat_damage", n=definition.damage)
    if definition.kind == "armor" and definition.protection is not None:
        return t("stat_protection", n=definition.protection)
    if definition.kind == "consumable" and definition.effect in _EFFECT_KEYS and definition.power:
        return t(_EFFECT_KEYS[definition.effect], n=definition.power)
    return ""
