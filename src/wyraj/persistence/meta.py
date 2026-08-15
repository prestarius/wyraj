"""Meta-state: what survives death (M6 "Powroty", spec §2).

Human-readable YAML at `~/.wyraj/meta.yml` — editing it is a feature, not a
crime. An HMAC checksum (fixed app key, honesty not security) flags edited
profiles: on mismatch the game loads normally and sets `edited: true`;
morgue files mention it. Unknown fields survive a rewrite (forward compat),
`schema_version` migrations live in `meta_migrations.py`, and every write is
an atomic tmp-file replace.
"""

import hashlib
import hmac
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from wyraj.persistence.meta_migrations import CURRENT_SCHEMA_VERSION, migrate
from wyraj.persistence.paths import wyraj_home

_HMAC_KEY = b"wyraj-meta-honesty-v1"  # fixed app constant by design (spec §2.2)

BASE_ORIGINS = ["wygnaniec", "zielarka", "najemnik"]
STASH_BASE_SLOTS = 4


class Currency(BaseModel):
    model_config = ConfigDict(extra="allow")
    denary: int = 0


class StashedItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    item_id: str
    count: int = 1
    instance: dict[str, Any] = {}


class Stash(BaseModel):
    model_config = ConfigDict(extra="allow")
    slots_total: int = STASH_BASE_SLOTS
    items: list[StashedItem] = []


class DziadMemory(BaseModel):
    model_config = ConfigDict(extra="allow")
    reputation: int = 0
    met_count: int = 0
    unlocked_stock_tiers: list[int] = [1]


class Codex(BaseModel):
    model_config = ConfigDict(extra="allow")
    known: dict[str, str] = {}  # monster key → unknown|glimpsed|partial|full


class Unlocks(BaseModel):
    model_config = ConfigDict(extra="allow")
    origins: list[str] = Field(default_factory=lambda: list(BASE_ORIGINS))


class MetaState(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: int = CURRENT_SCHEMA_VERSION
    edited: bool = False
    currency: Currency = Field(default_factory=Currency)
    stash: Stash = Field(default_factory=Stash)
    dziad: DziadMemory = Field(default_factory=DziadMemory)
    codex: Codex = Field(default_factory=Codex)
    unlocks: Unlocks = Field(default_factory=Unlocks)
    achievements: dict[str, int] = {}
    prologue_seen: bool = False
    szept_seen: list[str] = []


def meta_path() -> Path:
    return wyraj_home() / "meta.yml"


def _canonical(payload: dict[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if k != "checksum"}
    return yaml.safe_dump(clean, sort_keys=True, allow_unicode=True)


def _checksum(payload: dict[str, Any]) -> str:
    return hmac.new(_HMAC_KEY, _canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()


def load_meta(path: Path | None = None) -> MetaState:
    target = path or meta_path()
    if not target.exists():
        return MetaState()
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("meta.yml is not a mapping")
    except Exception:
        # Corrupt file: keep the evidence, start honest and fresh.
        target.rename(target.with_suffix(".yml.broken"))
        return MetaState()

    stored_checksum = raw.get("checksum")
    tampered = stored_checksum != _checksum(raw)
    raw = migrate(raw)
    raw.pop("checksum", None)
    try:
        meta = MetaState(**raw)
    except Exception:
        target.rename(target.with_suffix(".yml.broken"))
        return MetaState()
    if tampered:
        meta.edited = True  # flagged, never punished (spec §2.2)
    return meta


def save_meta(meta: MetaState, path: Path | None = None) -> Path:
    target = path or meta_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = meta.model_dump(mode="json")
    payload["schema_version"] = CURRENT_SCHEMA_VERSION
    payload["checksum"] = _checksum(payload)
    tmp = target.with_suffix(".yml.tmp")
    tmp.write_text(yaml.safe_dump(payload, sort_keys=True, allow_unicode=True), encoding="utf-8")
    tmp.replace(target)  # atomic on POSIX
    return target
