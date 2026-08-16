"""UI string catalogs: data/locale/<lang>.yml (flat key → string).

M12: catalogs merge across the pack chain per key, and a pack shipping a
new locale (plus narration/<lang>/) makes that language real — EN is
always merged underneath by the i18n layer.
"""

from pathlib import Path

import yaml

from wyraj.content.paths import data_roots


def load_locale(lang: str, root: Path | None = None) -> dict[str, str]:
    strings: dict[str, str] = {}
    for base in [root] if root is not None else data_roots():
        path = base / "locale" / f"{lang}.yml"
        if not path.exists():
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        strings.update({str(k): str(v) for k, v in raw.items()})
    return strings


def available_languages() -> list[str]:
    """Languages any root ships a locale or narration pack for."""
    langs: set[str] = set()
    for base in data_roots():
        locale_dir = base / "locale"
        if locale_dir.is_dir():
            langs |= {p.stem for p in locale_dir.glob("*.yml")}
        narration_dir = base / "narration"
        if narration_dir.is_dir():
            langs |= {p.name for p in narration_dir.iterdir() if p.is_dir()}
    return sorted(langs)
