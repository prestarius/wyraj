"""Origin loading: YAML → validated OriginDef models (character creation)."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_dir


class OriginDef(BaseModel):
    key: str
    name: str
    title: str
    hp: int = Field(gt=0)
    to_hit: int = Field(ge=0, le=100)
    damage: int = Field(gt=0)
    satiation: int = Field(gt=0)
    starting_items: list[str] = []
    intro: str = ""
    description: str = ""


def load_origins(root: Path | None = None) -> dict[str, OriginDef]:
    path = (root or data_dir()) / "origins.yml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {key: OriginDef(key=key, **fields) for key, fields in raw.items()}
