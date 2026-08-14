"""Morgue files: a readable record of each fallen run."""

from datetime import datetime
from pathlib import Path

from wyraj.core.components import Inventory, Item
from wyraj.core.game import Game
from wyraj.persistence.paths import wyraj_home


def morgue_dir() -> Path:
    return wyraj_home() / "morgue"


def write_morgue(game: Game, when: datetime, directory: Path | None = None) -> Path:
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

    lines = [
        "════════ WYRAJ — morgue ════════",
        f"{game.origin.name}, {game.origin.title}",
        f"Seed: {game.seed}",
        f"Turns survived: {game.turn}",
        f"Deepest point: {deepest}",
        f"Fate: {game.death_cause or 'lost to the forest'}",
        "",
        "Creatures witnessed: " + (", ".join(known) if known else "none"),
        "Carried at the end: " + (", ".join(carried) if carried else "nothing"),
        "",
        "Somewhere above the canopy, a bird takes wing toward Wyraj.",
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
