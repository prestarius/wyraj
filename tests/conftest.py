"""Shared test helpers."""

from pathlib import Path

import pytest

from wyraj.core.game import Game


@pytest.fixture(autouse=True)
def _sandbox_wyraj_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let tests touch the player's real ~/.wyraj (saves, morgue, history)."""
    monkeypatch.setenv("WYRAJ_HOME", str(tmp_path / "wyraj-home"))


@pytest.fixture(autouse=True)
def _no_packs():
    """Every test starts and ends pack-free (M12): the chain is process state."""
    from wyraj.content.packs import activate_packs

    activate_packs([])
    yield
    activate_packs([])


def goto_depth(game: Game, depth: int) -> None:
    """Jump the player straight to a level (tests only)."""
    for d in range(1, depth + 1):
        game._ensure_level(d)
    if depth > 0:
        game._change_level(depth, "down")
