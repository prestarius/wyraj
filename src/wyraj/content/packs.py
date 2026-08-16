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


# ---- --validate-pack (spec §3) --------------------------------------------

# The v1 modding surface (open decision #41); anything else in a pack is
# ignored by the loaders and flagged here so authors aren't left guessing.
SURFACE_DIRS = (
    "bestiary",
    "items",
    "hooks",
    "loot",
    "errands",
    "epithets",
    "narration",
    "locale",
    "audio",
)


@dataclass
class PackReport:
    name: str = ""
    errors: list[str] | None = None
    warnings: list[str] | None = None
    adds: list[str] | None = None
    overrides: list[str] | None = None

    def __post_init__(self) -> None:
        self.errors = self.errors or []
        self.warnings = self.warnings or []
        self.adds = self.adds or []
        self.overrides = self.overrides or []

    @property
    def ok(self) -> bool:
        return not self.errors

    def lines(self) -> list[str]:
        out = [f"{self.name}: {'VALID' if self.ok else 'INVALID'}"]
        for error in self.errors or []:
            out.append(f"  error: {error}")
        for warning in self.warnings or []:
            out.append(f"  warning: {warning}")
        if self.adds:
            out.append(f"  adds ({len(self.adds)}): " + ", ".join(self.adds))
        if self.overrides:
            out.append(f"  overrides ({len(self.overrides)}): " + ", ".join(self.overrides))
        if not self.overrides:
            out.append("  overrides: none")
        return out


def _friendly(file: Path, key: str, exc: Exception) -> str:
    try:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            parts = [
                f"{'.'.join(str(loc) for loc in err['loc'])} — {err['msg']}" for err in exc.errors()
            ]
            return f"{file.name}: {key}: " + "; ".join(parts)
    except Exception:
        pass
    return f"{file.name}: {key}: {exc}"


def _check_keyed(
    report: PackReport,
    pack_dir: Path,
    subdir: str,
    model: type,
    base_keys: set[str],
    key_kwarg: bool = True,
) -> None:
    directory = pack_dir / subdir
    if not directory.is_dir():
        return
    assert report.errors is not None and report.adds is not None
    assert report.overrides is not None
    for path in sorted(directory.glob("*.yml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            report.errors.append(f"{path.name}: not valid YAML — {exc}")
            continue
        if not isinstance(raw, dict):
            report.errors.append(f"{path.name}: expected a mapping of keys to entries")
            continue
        for key, fields in raw.items():
            try:
                model(key=key, **fields) if key_kwarg else model(**fields)
            except Exception as exc:
                report.errors.append(_friendly(path, str(key), exc))
                continue
            label = f"{subdir}/{key}"
            (report.overrides if key in base_keys else report.adds).append(label)


def validate_pack(path: Path) -> PackReport:
    """Friendly errors, then the honest adds/overrides summary (spec §3)."""
    from wyraj.content.audio import AudioCatalog, CreditEntry
    from wyraj.content.bestiary import MonsterDef, load_bestiary
    from wyraj.content.errands import ErrandDef, load_errands
    from wyraj.content.hooks import HookDef, load_hooks
    from wyraj.content.items import ItemDef, load_items
    from wyraj.content.loot import LootTable, load_loot_tables
    from wyraj.content.paths import data_dir
    from wyraj.narration.templates import GrammarPack

    pack_dir = Path(path).expanduser().resolve()
    report = PackReport(name=str(pack_dir))
    assert report.errors is not None and report.warnings is not None
    assert report.adds is not None and report.overrides is not None
    try:
        manifest = load_manifest(pack_dir)
        report.name = f"{manifest.name} ({manifest.key} {manifest.version})"
    except PackError as exc:
        report.errors.append(str(exc))
        return report

    base = data_dir()
    _check_keyed(report, pack_dir, "bestiary", MonsterDef, set(load_bestiary(base)))
    _check_keyed(report, pack_dir, "items", ItemDef, set(load_items(base)))
    _check_keyed(report, pack_dir, "hooks", HookDef, set(load_hooks(base)))
    _check_keyed(report, pack_dir, "errands", ErrandDef, set(load_errands(base)))

    loot_dir = pack_dir / "loot"
    if loot_dir.is_dir():
        base_loot = set(load_loot_tables(base))
        for path_ in sorted(loot_dir.glob("*.yml")):
            try:
                LootTable(**(yaml.safe_load(path_.read_text(encoding="utf-8")) or {}))
            except Exception as exc:
                report.errors.append(_friendly(path_, path_.stem, exc))
                continue
            label = f"loot/{path_.stem}"
            (report.overrides if path_.stem in base_loot else report.adds).append(label)

    narration_dir = pack_dir / "narration"
    if narration_dir.is_dir():
        for lang_dir in sorted(p for p in narration_dir.iterdir() if p.is_dir()):
            base_lang = base / "narration" / lang_dir.name
            base_rules = set(GrammarPack.load_dir(base_lang).rules) if base_lang.is_dir() else set()
            try:
                rules = GrammarPack.load_dir(lang_dir).rules
            except Exception as exc:
                report.errors.append(f"narration/{lang_dir.name}: {exc}")
                continue
            for event_key, subkey in sorted(rules, key=str):
                label = f"narration/{lang_dir.name}/{event_key}" + (f"/{subkey}" if subkey else "")
                target = report.overrides if (event_key, subkey) in base_rules else report.adds
                target.append(label)

    locale_dir = pack_dir / "locale"
    if locale_dir.is_dir():
        from wyraj.content.locale import load_locale

        for path_ in sorted(locale_dir.glob("*.yml")):
            lang = path_.stem
            base_keys = set(load_locale(lang, base))
            try:
                raw = yaml.safe_load(path_.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                report.errors.append(f"{path_.name}: not valid YAML — {exc}")
                continue
            for key in raw:
                label = f"locale/{lang}/{key}"
                (report.overrides if key in base_keys else report.adds).append(label)

    sounds_path = pack_dir / "audio" / "sounds.yml"
    if sounds_path.exists():
        from wyraj.content.audio import load_audio_catalog

        base_audio = load_audio_catalog(base)
        try:
            catalog = AudioCatalog(
                **(yaml.safe_load(sounds_path.read_text(encoding="utf-8")) or {})
            )
        except Exception as exc:
            report.errors.append(_friendly(sounds_path, "sounds", exc))
        else:
            credits_path = pack_dir / "audio" / "CREDITS.yml"
            credited: set[str] = set()
            if credits_path.exists():
                try:
                    raw_credits = yaml.safe_load(credits_path.read_text(encoding="utf-8")) or []
                    credited = {CreditEntry(**e).file for e in raw_credits}
                except Exception as exc:
                    report.errors.append(_friendly(credits_path, "credits", exc))
            for section in ("beds", "events", "voices"):
                base_keys = set(getattr(base_audio, section))
                for key, spec in getattr(catalog, section).items():
                    if not (pack_dir / "audio" / spec.file).exists():
                        report.errors.append(
                            f"sounds.yml: {section}/{key}: missing file {spec.file}"
                        )
                    elif spec.file not in credited:
                        report.errors.append(
                            f"sounds.yml: {section}/{key}: {spec.file} not in CREDITS.yml"
                        )
                    label = f"audio/{section}/{key}"
                    (report.overrides if key in base_keys else report.adds).append(label)

    for child in sorted(p.name for p in pack_dir.iterdir() if p.is_dir()):
        if child not in SURFACE_DIRS:
            report.warnings.append(
                f"'{child}/' is outside the v1 modding surface and will be ignored"
            )
    return report
