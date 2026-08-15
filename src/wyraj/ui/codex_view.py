"""Codex rendering, shared by the in-game screen and the title menu."""

from collections.abc import Callable

from rich.text import Text

from wyraj.content.bestiary import MonsterDef
from wyraj.content.economy import DropSpec
from wyraj.content.items import ItemDef
from wyraj.ui.i18n import t


def build_codex_text(
    bestiary: dict[str, MonsterDef],
    items_catalog: dict[str, ItemDef],
    drops: dict[str, DropSpec],
    sell_price_for: Callable[[str], int],
    tier_of: Callable[[str], str],
) -> Text:
    def trophy_line(key: str) -> str:
        spec = drops.get(key)
        if spec is None:
            return ""
        parts = []
        if spec.denary is not None:
            parts.append(t("codex_carries_silver"))
        for trophy in spec.trophies:
            definition = items_catalog.get(trophy.item)
            if definition is not None:
                parts.append(f"{definition.name} ({sell_price_for(trophy.item)})")
        return ", ".join(parts)

    text = Text()
    text.append(t("codex_title") + "\n\n", style="bold")
    for key in sorted(bestiary):
        definition = bestiary[key]
        tier = tier_of(key)
        if tier == "unknown":
            text.append(" " + t("codex_unseen") + "\n\n", style="grey30")
            continue
        text.append(f" {definition.name}", style="bold")
        text.append(f"  [{t('codex_tier_' + tier)}]", style="grey42")
        if definition.epithets:
            text.append(f" — {', '.join(definition.epithets)}", style="italic grey58")
        text.append("\n")
        if tier in ("partial", "full"):
            trophies = trophy_line(key)
            if trophies:
                text.append(f"   {t('codex_trophies')}: {trophies}\n", style="gold3")
        if tier == "full":
            if definition.weakness:
                text.append(
                    f"   {t('codex_weakness')}: {definition.weakness}\n",
                    style="medium_purple3",
                )
            text.append(f"   {definition.description.strip()}\n", style="grey66")
        text.append("\n")
    text.append(t("esc_close"), style="grey42")
    return text
