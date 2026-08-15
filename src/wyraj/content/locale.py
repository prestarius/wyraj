"""UI string catalogs: data/locale/<lang>.yml (flat key → string)."""

from pathlib import Path

import yaml

from wyraj.content.paths import data_dir


def load_locale(lang: str, root: Path | None = None) -> dict[str, str]:
    path = (root or data_dir()) / "locale" / f"{lang}.yml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in raw.items()}
