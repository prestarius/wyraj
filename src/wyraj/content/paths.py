"""Locate the data/ directory (repo root; overridable via WYRAJ_DATA)."""

import os
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("WYRAJ_DATA")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "data"
