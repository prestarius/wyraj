"""Morgue files: a readable record of each fallen run."""

from datetime import datetime
from pathlib import Path

from wyraj.core.components import Inventory, Item
from wyraj.core.game import Game
from wyraj.persistence.paths import wyraj_home


def morgue_dir() -> Path:
    return wyraj_home() / "morgue"


def write_morgue(
    game: Game, when: datetime, directory: Path | None = None, victory: bool = False
) -> Path:
    target_dir = directory or morgue_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = when.strftime("%Y%m%d-%H%M%S")
    target = target_dir / f"{stamp}-seed{game.seed}.txt"

    inventory = game.world.get(game.player, Inventory)
    carried = []
    if inventory is not None:
        for entity in inventory.items:
            item = game.world.get(entity, Item)
            if item is not None:
                carried.append(game.items_catalog[item.key].name)

    known = sorted(k for k in game.codex_seen if k in game.bestiary)
    places = {0: "the wieś", 1: "the puszcza", 2: "the bagna"}
    deepest = places.get(game.max_depth_reached, f"kurhan level {game.max_depth_reached - 2}")

    stash_count = sum(item.count for item in game.meta.stash.items)
    meta_lines = [
        f"Banked in the wieś: {game.meta.currency.denary} denary",
        f"Heirlooms waiting in the skrzynia: {stash_count}",
    ]
    if game.meta.edited:
        meta_lines.append("(profile hand-edited — no judgment, just honesty)")

    # M7 §6.2: every death leaves a picture of who you were at the end.
    # compose_portrait is a pure text builder — no Textual app involved.
    from wyraj.ui.portrait import compose_portrait, get_art, portrait_state_for

    portrait = compose_portrait(portrait_state_for(game), get_art("box")).plain

    lines = [
        "════════ WYRAJ — morgue ════════",
        f"{game.origin.name}, {game.origin.title}",
        f"Seed: {game.seed}",
        f"Turns survived: {game.turn}",
        f"Deepest point: {deepest}",
        f"Fate: {'the lids stayed shut' if victory else game.death_cause or 'lost to the forest'}",
        "",
        *portrait.splitlines(),
        "",
        "Creatures witnessed: " + (", ".join(known) if known else "none"),
        "Carried at the end: " + (", ".join(carried) if carried else "nothing"),
        *meta_lines,
        "",
        (
            "The birds returned. Once."
            if victory
            else "Somewhere above the canopy, a bird takes wing toward Wyraj."
        ),
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
