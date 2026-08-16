"""Portrait layer art: YAML → validated per-style layer sets (M7 spec §2).

One file per art style under `data/portrait/`. Every style implements the same
layer contract — base figures (with optional per-origin and hunched variants),
weapon/armor overlays, wound decals per HP band, non-color status marks, and
blizna scar marks — so the art direction stays swappable.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from wyraj.content.paths import data_dir

Patch = tuple[int, int, str]  # row, column, replacement char

BANDS = ("healthy", "bloodied", "wounded", "dying")


class PortraitArtDef(BaseModel):
    style: str
    base: dict[str, list[str]]  # "default" required; "<origin>"/"hunched" variants optional
    weapons: dict[str, list[Patch]] = {}
    armor: list[Patch] = Field(default_factory=list)
    wounds: dict[str, list[Patch]] = {}
    status_marks: dict[str, list[Patch]] = {}
    scars: list[Patch] = Field(default_factory=list)
    belt: list[Patch] = Field(default_factory=list)  # trophy-belt marks (spec §6.2)

    @model_validator(mode="after")
    def check(self) -> "PortraitArtDef":
        if "default" not in self.base:
            raise ValueError(f"portrait style '{self.style}' needs a 'default' base figure")
        for variant, lines in self.base.items():
            if not lines:
                raise ValueError(f"portrait style '{self.style}': base '{variant}' is empty")
        for band in self.wounds:
            if band not in BANDS:
                raise ValueError(f"portrait style '{self.style}': unknown wound band '{band}'")
        return self


def load_portraits(root: Path | None = None) -> dict[str, PortraitArtDef]:
    portrait_dir = (root or data_dir()) / "portrait"
    arts: dict[str, PortraitArtDef] = {}
    for path in sorted(portrait_dir.glob("*.yml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        art = PortraitArtDef(**raw)
        arts[art.style] = art
    return arts
