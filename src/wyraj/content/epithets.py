"""Named-weapon epithets (M7 §6.2): species → per-language name.

Both languages live in one file because an epithet is one identity — the
narration packs carry the announcement prose per language; this catalog only
supplies the display name for the pane and log.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from wyraj.content.paths import data_roots


class EpithetDef(BaseModel):
    en: str
    pl: str

    def for_lang(self, lang: str) -> str:
        return self.pl if lang == "pl" else self.en


def load_epithets(root: Path | None = None) -> dict[str, EpithetDef]:
    epithets: dict[str, EpithetDef] = {}
    for base in [root] if root is not None else data_roots():
        path = base / "epithets" / "epithets.yml"
        if not path.exists():
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for species, fields in raw.items():
            epithets[species] = EpithetDef(**fields)
    return epithets
