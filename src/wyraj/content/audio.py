"""Audio catalog loading: data/audio/sounds.yml + CREDITS.yml (M11 "Głosy" §3).

`sounds.yml` maps names to files, never the reverse: `beds` for the ambient
layer, `events` keyed by narration rule keys (flat "event/subkey" strings —
the same vocabulary the grammar packs speak), `voices` by monster key.
Explicit filenames only; nothing in data/audio/ is globbed.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_dir


class SoundSpec(BaseModel):
    file: str  # relative to data/audio/
    volume: float = Field(default=1.0, ge=0.0, le=1.0)


class AudioCatalog(BaseModel):
    beds: dict[str, SoundSpec] = {}
    events: dict[str, SoundSpec] = {}  # "attack_resolved/player_kill" or bare "light_extinguished"
    voices: dict[str, SoundSpec] = {}

    def event_sound(self, event_key: str, subkey: str | None) -> SoundSpec | None:
        """Exact "event/subkey" first, then the bare event — the narration
        lookup's fallback chain, minus "default"."""
        if subkey is not None:
            spec = self.events.get(f"{event_key}/{subkey}")
            if spec is not None:
                return spec
        return self.events.get(event_key)


class CreditEntry(BaseModel):
    file: str
    author: str
    source_url: str
    license: str  # CC0/CC-BY only — no NC, no ND (spec §3)


def audio_dir(root: Path | None = None) -> Path:
    return (root or data_dir()) / "audio"


def load_audio_catalog(root: Path | None = None) -> AudioCatalog:
    path = audio_dir(root) / "sounds.yml"
    if not path.exists():
        return AudioCatalog()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AudioCatalog(**raw)


def load_audio_credits(root: Path | None = None) -> list[CreditEntry]:
    path = audio_dir(root) / "CREDITS.yml"
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [CreditEntry(**entry) for entry in raw]
