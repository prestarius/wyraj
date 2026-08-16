"""Data packs (M12 "Gusła"): folders shaped like data/, declared by manifest.

Data only, forever: a pack is YAML and asset files. Nothing here — or
anywhere — imports, execs, or evals anything from a pack directory.
A missing or invalid pack never blocks the game: it is skipped with a note.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from wyraj.content.paths import set_pack_roots


class PackError(Exception):
    pass


class PackManifest(BaseModel):
    name: str
    key: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    version: str = "1.0"
    author: str = ""
    license: str = ""
    description: str = ""

    @field_validator("license")
    @classmethod
    def open_license_only(cls, value: str) -> str:
        if "NC" in value or "ND" in value:
            raise ValueError("packs are content: no NC/ND licenses")
        return value


@dataclass(frozen=True)
class Pack:
    path: Path
    manifest: PackManifest


_active: list[Pack] = []


def load_manifest(path: Path) -> PackManifest:
    manifest_path = path / "pack.yml"
    if not path.is_dir():
        raise PackError(f"{path} is not a directory")
    if not manifest_path.exists():
        raise PackError(f"{path} has no pack.yml")
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        return PackManifest(**raw)
    except PackError:
        raise
    except Exception as exc:
        raise PackError(f"{manifest_path}: {exc}") from exc


def discover_packs(paths: list[str]) -> tuple[list[Pack], list[str]]:
    """Resolve configured pack paths in order. Returns (loaded, skip notes)."""
    loaded: list[Pack] = []
    notes: list[str] = []
    seen: set[str] = set()
    for entry in paths:
        path = Path(str(entry)).expanduser().resolve()
        try:
            manifest = load_manifest(path)
        except PackError as exc:
            notes.append(str(exc))
            continue
        if manifest.key in seen:
            notes.append(f"{path}: duplicate pack key '{manifest.key}' — skipped")
            continue
        seen.add(manifest.key)
        loaded.append(Pack(path=path, manifest=manifest))
    return loaded, notes


def activate_packs(packs: list[Pack]) -> None:
    """Set the content root chain. Called once at startup; tests reset."""
    global _active
    _active = list(packs)
    set_pack_roots([pack.path for pack in packs])


def active_packs() -> list[Pack]:
    return list(_active)


def active_fingerprint() -> list[list[str]]:
    """What a save records: the world's content identity (spec §2)."""
    return [[pack.manifest.key, pack.manifest.version] for pack in _active]
