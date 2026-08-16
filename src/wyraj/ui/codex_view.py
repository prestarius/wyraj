"""Codex rendering, shared by the in-game screen and the title menu."""

from collections.abc import Callable

from rich.text import Text

from wyraj.content.bestiary import MonsterDef
from wyraj.content.economy import DropSpec
from wyraj.content.errands import ErrandDef
from wyraj.content.items import ItemDef
from wyraj.persistence.meta import MetaState
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
    text.append(t("zlecenia_tab_hint") + "  ·  " + t("esc_close"), style="grey42")
    return text


def build_errands_text(
    catalog: dict[str, ErrandDef],
    run_errands: dict[str, str] | None,
    meta: MetaState,
    bestiary: dict[str, MonsterDef],
    items_catalog: dict[str, ItemDef],
) -> Text:
    """The Zlecenia tab (M10 §5): a ledger, not a journal. `run_errands` is
    None from the title menu — that view reads from meta alone."""

    def target_name(errand: ErrandDef) -> str:
        if errand.kind == "hunt":
            definition = bestiary.get(errand.target)
            return definition.name if definition is not None else errand.target
        item = items_catalog.get(errand.target)
        return item.name if item is not None else errand.target

    text = Text()
    text.append(t("zlecenia_title") + "\n\n", style="bold")

    if run_errands is not None:
        text.append(" " + t("zlecenia_run_header") + "\n", style="grey58")
        taken = {key: state for key, state in sorted(run_errands.items()) if state != "offered"}
        if not taken:
            text.append("  " + t("zlecenia_none") + "\n", style="grey42")
        for key, state in taken.items():
            errand = catalog[key]
            mark = "✓" if state == "done" else "·"
            style = "grey42" if state == "done" else "grey85"
            text.append(
                f"  {mark} {t('villager_' + errand.giver)}: {target_name(errand)}"
                f" — {t('zlecenia_status_' + state)}\n",
                style=style,
            )
        text.append("\n")

    text.append(" " + t("zlecenia_meta_header") + "\n", style="grey58")
    if not meta.villagers:
        text.append("  " + t("zlecenia_no_memory") + "\n", style="grey42")
    for role in sorted(meta.villagers):
        memory = meta.villagers[role]
        text.append(
            "  "
            + t(
                "zlecenia_memory_line",
                villager=t("villager_" + role),
                reputation=memory.reputation,
                done=memory.errands_done,
                failed=memory.errands_failed,
            )
            + "\n",
            style="grey85",
        )
    if meta.village.resolved:
        text.append("\n " + t("zlecenia_fates_header") + "\n", style="grey58")
        for fate in meta.village.resolved:
            text.append(f"  {t('zlecenia_fate_' + fate)}\n", style="dark_red")
    text.append("\n" + t("zlecenia_tab_hint") + "  ·  " + t("esc_close"), style="grey42")
    return text
