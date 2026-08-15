"""User config file: ~/.wyraj/config.yml (all keys optional).

Recognized keys: ascii (bool), portrait ("half"|"box"), origin (key),
lang ("en"|"pl"), narrator ("template"|"llm"),
llm ({backend: ollama|openrouter, model, url, timeout}).
CLI flags always win over the config file.
"""

from typing import Any

import yaml

from wyraj.persistence.paths import wyraj_home

VALID_KEYS = {"ascii", "portrait", "origin", "lang", "narrator", "llm"}


def load_config() -> dict[str, Any]:
    path = wyraj_home() / "config.yml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k in VALID_KEYS}
