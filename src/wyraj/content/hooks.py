"""Story hook loading: YAML → validated HookDef models (spec §8).

Hooks are narrative seeds placed by the generators — a ransacked chapel, a
dead traveler — entities with Lore and a one-shot narration trigger on
discovery. The narrator weaves them in when the player first sees them.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_roots


class HookDef(BaseModel):
    key: str
    name: str
    glyph: str = Field(min_length=1, max_length=1)
    ascii_glyph: str = Field(min_length=1, max_length=1)
    style: str = "grey66"
    biomes: list[str]
    description: str = ""
    forms: dict[str, dict[str, str | bool]] = {}


def load_hooks(root: Path | None = None) -> dict[str, HookDef]:
    hooks: dict[str, HookDef] = {}
    for base in [root] if root is not None else data_roots():
        hooks_dir = base / "hooks"
        if not hooks_dir.is_dir():
            continue
        for path in sorted(hooks_dir.glob("*.yml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for key, fields in raw.items():
                hooks[key] = HookDef(key=key, **fields)
    return hooks
