"""Shared test helpers."""

from wyraj.core.game import Game


def goto_depth(game: Game, depth: int) -> None:
    """Jump the player straight to a level (tests only)."""
    for d in range(1, depth + 1):
        game._ensure_level(d)
    if depth > 0:
        game._change_level(depth, "down")
