"""Schema migrations for meta.yml. Each migration lifts N → N+1."""

from collections.abc import Callable
from typing import Any

CURRENT_SCHEMA_VERSION = 1

# version being migrated FROM → function producing the next version's shape
_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    version = int(raw.get("schema_version", 1))
    while version < CURRENT_SCHEMA_VERSION:
        step = _MIGRATIONS.get(version)
        if step is None:
            break  # unknown gap: let pydantic defaults absorb what they can
        raw = step(raw)
        version = int(raw.get("schema_version", version + 1))
    raw["schema_version"] = max(version, CURRENT_SCHEMA_VERSION)
    return raw
