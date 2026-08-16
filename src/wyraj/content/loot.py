"""Per-biome loot tables: how many items a level gets and their weights."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_roots


class LootTable(BaseModel):
    count: int = Field(ge=0)
    count_per_depth: int = Field(default=0, ge=0)
    weights: dict[str, int]

    def items_for_depth(self, depth: int) -> int:
        return self.count + self.count_per_depth * depth


def load_loot_tables(root: Path | None = None) -> dict[str, LootTable]:
    tables: dict[str, LootTable] = {}
    for base in [root] if root is not None else data_roots():
        loot_dir = base / "loot"
        if not loot_dir.is_dir():
            continue
        for path in sorted(loot_dir.glob("*.yml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            tables[path.stem] = LootTable(**raw)
    return tables
