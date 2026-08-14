"""Bestiary loading: YAML → validated MonsterDef models."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_dir


class MonsterDef(BaseModel):
    key: str
    name: str
    glyph: str = Field(min_length=1, max_length=1)
    ascii_glyph: str = Field(min_length=1, max_length=1)
    style: str = "white"
    hp: int = Field(gt=0)
    speed: int = Field(gt=0)
    damage: int = Field(ge=0)
    to_hit: int = Field(ge=0, le=100)
    behavior: str = "approach"
    spawn_weight: int = Field(default=1, ge=0)
    biomes: list[str] = ["puszcza", "kurhany"]
    epithets: list[str] = []
    description: str = ""
    # String-form tables per language (spec §7), e.g. {"en": {"plural": "biesy"}}
    forms: dict[str, dict[str, str | bool]] = {}


def load_bestiary(root: Path | None = None) -> dict[str, MonsterDef]:
    bestiary_dir = (root or data_dir()) / "bestiary"
    monsters: dict[str, MonsterDef] = {}
    for path in sorted(bestiary_dir.glob("*.yml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for key, fields in raw.items():
            monsters[key] = MonsterDef(key=key, **fields)
    return monsters
