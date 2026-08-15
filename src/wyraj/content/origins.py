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
    title_pl: str = ""
    intro_pl: str = ""
    description_pl: str = ""

    def title_for(self, lang: str) -> str:
        return self.title_pl if lang == "pl" and self.title_pl else self.title

    def intro_for(self, lang: str) -> str:
        return self.intro_pl if lang == "pl" and self.intro_pl else self.intro

    def description_for(self, lang: str) -> str:
        return self.description_pl if lang == "pl" and self.description_pl else self.description


def load_origins(root: Path | None = None) -> dict[str, OriginDef]:
    path = (root or data_dir()) / "origins.yml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {key: OriginDef(key=key, **fields) for key, fields in raw.items()}
