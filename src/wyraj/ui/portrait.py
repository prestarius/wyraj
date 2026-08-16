"""Layered, state-reactive character portrait (M7 US 10.1, spec §2).

Pure compositor: `PortraitState` (a projection of ECS components — never widget
state) + a `PortraitArtDef` (YAML art under `data/portrait/`) → rich `Text`.
Layer order: base figure → equipment overlays → wound decals → status decals →
blizna scars. Status tints are style washes here in code; every status also
carries a non-color mark from the art file (color-blind rule, spec §6.1), and
fear shifts the whole figure a column aside — a recoil readable without color.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from rich.text import Text

from wyraj.content.portrait import Patch, PortraitArtDef, load_portraits

if TYPE_CHECKING:
    from wyraj.core.game import Game

BAND_STYLES = {
    "healthy": "grey74",
    "bloodied": "orange3",
    "wounded": "dark_orange3",
    "dying": "red3",
}
POISON_EDGE_STYLE = "chartreuse4"
WET_STYLE = "deep_sky_blue4"
HALO_BACKGROUND = " on #1d1f12"  # lit gromnica warms the portrait's dark


def hp_band(fraction: float) -> str:
    """Four bands per spec §2.3: healthy / bloodied <2/3 / wounded <1/3 / dying <10%."""
    if fraction < 0.10:
        return "dying"
    if fraction < 1 / 3:
        return "wounded"
    if fraction < 2 / 3:
        return "bloodied"
    return "healthy"


@dataclass(frozen=True)
class PortraitState:
    band: str = "healthy"
    origin: str = "default"
    weapon_key: str | None = None
    armored: bool = False
    halo: bool = False  # lit gromnica
    statuses: tuple[str, ...] = ()
    scars: int = 0  # blizny — near-deaths survived this run
    trophies: int = 0  # trophy-belt marks (most recent 1-2, spec §6.2)
    mini: bool = False  # short-terminal 4-row variant (spec §1)


@lru_cache(maxsize=1)
def _arts() -> dict[str, PortraitArtDef]:
    return load_portraits()


def get_art(style: str, use_ascii: bool = False) -> PortraitArtDef:
    arts = _arts()
    if use_ascii and "ascii" in arts:
        return arts["ascii"]
    return arts.get(style) or arts["box"]


def _base_lines(state: PortraitState, art: PortraitArtDef) -> list[str]:
    candidates = []
    if state.mini:
        candidates.append("mini")
    if state.band in ("wounded", "dying"):
        candidates += [f"{state.origin}_hunched", "hunched"]
    candidates += [state.origin, "default"]
    for name in candidates:
        if name in art.base:
            return art.base[name]
    return art.base["default"]


def _apply(grid: list[list[str]], patches: list[Patch] | tuple[Patch, ...]) -> None:
    for row, col, char in patches:
        if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
            grid[row][col] = char


def compose_portrait(state: PortraitState, art: PortraitArtDef) -> Text:
    lines = _base_lines(state, art)
    width = max(len(line) for line in lines)
    grid = [list(line.ljust(width)) for line in lines]
    if state.armored:
        _apply(grid, art.armor)
    if state.weapon_key is not None:
        _apply(grid, art.weapons.get(state.weapon_key, ()))
    _apply(grid, art.wounds.get(state.band, ()))
    for status in state.statuses:
        _apply(grid, art.status_marks.get(status, ()))
    _apply(grid, art.scars[: state.scars])
    _apply(grid, art.belt[: state.trophies])

    rows = ["".join(row) for row in grid]
    if "fear" in state.statuses and width > 1:  # recoil: the figure flinches aside
        rows = [" " + row[:-1] for row in rows]

    wash = BAND_STYLES.get(state.band, "grey74")
    if "blessing" in state.statuses:  # faint bright outline
        wash = f"bold {wash}"
    suffix = HALO_BACKGROUND if state.halo else ""
    text = Text()
    total = len(rows)
    for index, row in enumerate(rows):
        row_style = wash
        if "wet" in state.statuses and index >= total - total // 3:  # dark lower third
            row_style = WET_STYLE
        if "poison" in state.statuses and len(row) > 4:  # green-tinted edges
            text.append(row[:2], style=POISON_EDGE_STYLE + suffix)
            text.append(row[2:-2], style=row_style + suffix)
            text.append(row[-2:], style=POISON_EDGE_STYLE + suffix)
        else:
            text.append(row, style=row_style + suffix)
        if index < total - 1:
            text.append("\n")
    return text


def portrait_state_for(game: "Game", mini: bool = False) -> PortraitState:
    """Project ECS state into a PortraitState — shared by the pane and the morgue."""
    from wyraj.core.components import (
        Health,
        Inventory,
        Item,
        LightSource,
        StatusEffects,
        Wearing,
        Wielding,
    )

    world, player = game.world, game.player
    health = world.expect(player, Health)
    wielding = world.get(player, Wielding)
    weapon_key = None
    if wielding is not None and wielding.item is not None:
        weapon = world.get(wielding.item, Item)
        weapon_key = weapon.key if weapon is not None else None
    wearing = world.get(player, Wearing)
    statuses = world.get(player, StatusEffects)
    light = world.get(player, LightSource)
    inventory = world.get(player, Inventory) or Inventory()
    trophies = sum(
        1
        for entity in inventory.items
        if (item := world.get(entity, Item)) is not None and item.kind == "trophy"
    )
    return PortraitState(
        band=hp_band(health.fraction),
        origin=game.origin.key,
        weapon_key=weapon_key,
        armored=wearing is not None and wearing.item is not None,
        halo=light is not None and light.turns > 0,
        statuses=tuple(e.kind for e in statuses.effects) if statuses is not None else (),
        scars=game.blizny,
        trophies=min(trophies, 2),
        mini=mini,
    )
