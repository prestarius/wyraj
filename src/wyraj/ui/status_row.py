"""Status row (M7 US 10.3): a pure projection of `StatusEffects`.

Horizontal strip of glyph + localized name + remaining turns, color-coded by
family (harmful red / beneficial gold / neutral blue) with a redundant glyph
per status (color-blind rule, spec §6.1). Overflow past four shows three
entries plus "+N".
"""

from rich.text import Text

from wyraj.core.components import StatusEffect
from wyraj.ui.i18n import t

MAX_SHOWN = 4

# kind → ((unicode, ascii) glyph, family)
_GLYPHS: dict[str, tuple[tuple[str, str], str]] = {
    "bleeding": (("✖", "x"), "harmful"),
    "poison": (("☠", "%"), "harmful"),
    "fear": (("!", "!"), "harmful"),
    "blessing": (("✚", "+"), "beneficial"),
    "perun_favor": (("Λ", "^"), "beneficial"),
    "weles_favor": (("Ω", "O"), "beneficial"),
}
_FAMILY_STYLES = {"harmful": "red3", "beneficial": "gold3", "neutral": "sky_blue3"}


def build_status_row(effects: tuple[StatusEffect, ...], use_ascii: bool = False) -> Text | None:
    """One-line strip, or None when there is nothing to show."""
    if not effects:
        return None
    shown = effects if len(effects) <= MAX_SHOWN else effects[: MAX_SHOWN - 1]
    text = Text()
    for effect in shown:
        glyphs, family = _GLYPHS.get(effect.kind, (("•", "*"), "neutral"))
        glyph = glyphs[1] if use_ascii else glyphs[0]
        style = _FAMILY_STYLES[family]
        text.append(f" {glyph} ", style=f"bold {style}")
        text.append(f"{t('status_' + effect.kind)}({effect.duration})", style=style)
    if len(effects) > MAX_SHOWN:
        text.append(" " + t("status_more", n=len(effects) - (MAX_SHOWN - 1)), style="grey58")
    return text
