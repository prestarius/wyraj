"""Item loading: YAML → validated ItemDef models."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from wyraj.content.paths import data_dir

ITEM_KINDS = ("weapon", "consumable", "trinket")
EFFECTS = ("heal", "feed", "bless", "light")


class ItemDef(BaseModel):
    key: str
    name: str
    glyph: str = Field(min_length=1, max_length=1)
    ascii_glyph: str = Field(min_length=1, max_length=1)
    style: str = "white"
    kind: str
    damage: int | None = None  # weapons
    effect: str | None = None  # consumables
    power: int | None = None  # consumables
    spawn_weight: int = Field(default=1, ge=0)
    description: str = ""
    forms: dict[str, dict[str, str | bool]] = {}

    @model_validator(mode="after")
    def check_kind(self) -> "ItemDef":
        if self.kind not in ITEM_KINDS:
            raise ValueError(f"unknown item kind '{self.kind}'")
        if self.kind == "weapon" and (self.damage is None or self.damage <= 0):
            raise ValueError(f"weapon '{self.key}' needs positive damage")
        if self.kind == "consumable":
            if self.effect not in EFFECTS:
                raise ValueError(f"consumable '{self.key}' needs effect in {EFFECTS}")
            if self.power is None or self.power <= 0:
                raise ValueError(f"consumable '{self.key}' needs positive power")
        return self


def load_items(root: Path | None = None) -> dict[str, ItemDef]:
    items_dir = (root or data_dir()) / "items"
    items: dict[str, ItemDef] = {}
    for path in sorted(items_dir.glob("*.yml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for key, fields in raw.items():
            items[key] = ItemDef(key=key, **fields)
    return items
