"""User config file: ~/.wyraj/config.yml (all keys optional).

Recognized keys: ascii (bool), portrait ("half"|"box"), origin (key),
lang ("en"|"pl"), narrator ("template"|"llm"),
llm ({backend: ollama|openrouter, model, url, timeout}).
CLI flags always win over the config file.
"""

from typing import Any

import yaml

from wyraj.persistence.paths import wyraj_home

VALID_KEYS = {
    "ascii",
    "portrait",
    "origin",
    "lang",
    "narrator",
    "llm",
    "hints",
    "text_speed",
    "quickslots",  # M7: {auto_refill: bool}
    "audio",  # M11: {enabled: bool, master: float, ambient: float, sfx: float}
    "packs",  # M12: ordered list of pack directory paths (later wins)
}


def load_config() -> dict[str, Any]:
    path = wyraj_home() / "config.yml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k in VALID_KEYS}


def save_config(updates: dict[str, Any]) -> None:
    """Merge updates into config.yml, preserving unknown keys."""
    path = wyraj_home() / "config.yml"
    current: dict[str, Any] = {}
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            current = raw
    current.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(current, sort_keys=True, allow_unicode=True), encoding="utf-8")
