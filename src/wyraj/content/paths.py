"""Locate the data/ directory (repo root; overridable via WYRAJ_DATA).

M12 "Gusła": content may come from a chain of roots — base data/ first,
then each enabled pack in config order (later packs win on key collisions).
The chain is set once at startup from config; tests reset it (conftest).
"""

import os
from pathlib import Path

_pack_roots: list[Path] = []


def data_dir() -> Path:
    override = os.environ.get("WYRAJ_DATA")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "data"


def set_pack_roots(roots: list[Path]) -> None:
    global _pack_roots
    _pack_roots = list(roots)


def data_roots() -> list[Path]:
    """Base data/ plus enabled packs, in override order."""
    return [data_dir(), *_pack_roots]
