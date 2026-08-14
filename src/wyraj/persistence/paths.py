"""Where Wyraj keeps its user data (override with WYRAJ_HOME)."""

import os
from pathlib import Path


def wyraj_home() -> Path:
    home = os.environ.get("WYRAJ_HOME")
    return Path(home) if home else Path.home() / ".wyraj"
