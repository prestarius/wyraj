"""Per-biome loot tables: how many items a level gets and their weights."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_dir


class LootTable(BaseModel):
    count: int = Field(ge=0)
    count_per_depth: int = Field(default=0, ge=0)
    weights: dict[str, int]

    def items_for_depth(self, depth: int) -> int:
        return self.count + self.count_per_depth * depth


def load_loot_tables(root: Path | None = None) -> dict[str, LootTable]:
    loot_dir = (root or data_dir()) / "loot"
    tables: dict[str, LootTable] = {}
    for path in sorted(loot_dir.glob("*.yml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        tables[path.stem] = LootTable(**raw)
    return tables
