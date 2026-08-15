"""Intro/onboarding content: title lines, prologue pages, szept hints, help.

Lives under data/intro/<lang>/ — NOT under data/narration/, which is
reserved for grammar packs (their loader consumes every *.yml it finds).
Falls back to English per file when a language lacks one.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from wyraj.content.paths import data_dir


def _load(lang: str, name: str, root: Path | None = None) -> Any:
    base = (root or data_dir()) / "intro"
    path = base / lang / name
    if not path.exists():
        path = base / "en" / name
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_title_lines(lang: str = "en") -> list[str]:
    raw = _load(lang, "title_lines.yml")
    return [str(line) for line in raw] if isinstance(raw, list) else []


class Prologue(BaseModel):
    common: list[str]  # shared pages, in order
    origins: dict[str, str]  # origin key → final page
    fallback: str  # final page when the origin has no variant


def load_prologue(lang: str = "en") -> Prologue:
    raw = _load(lang, "prologue.yml") or {}
    return Prologue(**raw)


def load_szept(lang: str = "en") -> dict[str, str]:
    raw = _load(lang, "szept.yml") or {}
    return {str(k): str(v) for k, v in raw.items()}


class HelpText(BaseModel):
    title: str
    keys: list[str]  # pre-formatted key reference lines
    world: list[str]  # "How Wyraj works" paragraphs, in-voice


def load_help(lang: str = "en") -> HelpText:
    raw = _load(lang, "help.yml") or {}
    return HelpText(**raw)
