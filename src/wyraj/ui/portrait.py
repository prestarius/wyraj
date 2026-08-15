# ruff: noqa: RUF001 — decorative glyphs are the point of this file
"""Layered, state-reactive character portrait.

Two prototype art directions for open decision #5 (spec §13):
- "box"  — box-drawing line art (default; won decision #5)
- "half" — halfblock "pixel" art (kept as an option)

Both react to the same layers: base figure → weapon overlay → wound decals
and an HP-band color wash. Box-drawing won decision #5 and is the default;
the halfblock prototype stays available. YAML layer files are a later cleanup.
Switch at runtime with `wyraj --portrait box|half`.
"""

from dataclasses import dataclass, field

from rich.text import Text

# (row, column, replacement char)
Patch = tuple[int, int, str]

BAND_STYLES = {"healthy": "grey74", "bloodied": "orange3", "dying": "red3"}


def hp_band(fraction: float) -> str:
    if fraction <= 0.25:
        return "dying"
    if fraction <= 0.5:
        return "bloodied"
    return "healthy"


@dataclass(frozen=True)
class PortraitArt:
    name: str
    lines: tuple[str, ...]
    weapon_marks: dict[str, tuple[Patch, ...]] = field(default_factory=dict)
    wound_marks: dict[str, tuple[Patch, ...]] = field(default_factory=dict)


HALFBLOCK = PortraitArt(
    name="half",
    lines=(
        "   ▄▄▄▄▄   ",
        "  ▟█████▙  ",
        "  █▓▒░▒▓█  ",
        "  ▀▜███▛▀  ",
        " ▄███████▄ ",
        " █ ▒███▒ █ ",
        " ▛ ▒███▒ ▜ ",
        "   ▐█▌▐█▌  ",
    ),
    weapon_marks={
        "noz": ((5, 10, "╱"),),
        "toporek": ((4, 10, "▛"), (5, 10, "┃"), (6, 10, "┃")),
        "ciupaga": ((3, 10, "†"), (4, 10, "┃"), (5, 10, "┃"), (6, 10, "┃")),
    },
    wound_marks={
        "bloodied": ((5, 3, "╳"),),
        "dying": ((5, 3, "╳"), (6, 7, "╳"), (2, 4, "░")),
    },
)

BOXDRAW = PortraitArt(
    name="box",
    lines=(
        "   ╭───╮   ",
        "   │· ·│   ",
        "   ╰─┬─╯   ",
        "  ╭──┴──╮  ",
        "  │  ¦  │  ",
        "  │  ¦  │  ",
        "  ╰─┬─┬─╯  ",
        "    │ │    ",
        "    ╨ ╨    ",
    ),
    weapon_marks={
        "noz": ((5, 9, "╱"),),
        "toporek": ((3, 9, "⊦"), (4, 9, "│"), (5, 9, "│")),
        "ciupaga": ((2, 9, "†"), (3, 9, "│"), (4, 9, "│"), (5, 9, "│")),
    },
    wound_marks={
        "bloodied": ((4, 3, "×"),),
        "dying": ((4, 3, "×"), (5, 7, "×"), (1, 5, "─")),
    },
)

STYLES = {"half": HALFBLOCK, "box": BOXDRAW}


def _apply(lines: list[list[str]], patches: tuple[Patch, ...]) -> None:
    for row, col, char in patches:
        if 0 <= row < len(lines) and 0 <= col < len(lines[row]):
            lines[row][col] = char


def render_portrait(style: str, band: str, weapon_key: str | None) -> Text:
    art = STYLES.get(style, BOXDRAW)
    width = max(len(line) for line in art.lines)
    grid = [list(line.ljust(width)) for line in art.lines]
    if weapon_key is not None:
        _apply(grid, art.weapon_marks.get(weapon_key, ()))
    _apply(grid, art.wound_marks.get(band, ()))
    text = Text()
    text.append("\n".join("".join(row) for row in grid), style=BAND_STYLES.get(band, "grey74"))
    return text
