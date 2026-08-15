"""Golden-run regression: fixed seed + scripted input → full transcript.

The transcript covers both the mechanical event log and the narration lines,
so any change to core simulation OR narration output shows up as a diff.
Intentional changes: regenerate with  GOLDEN_REGEN=1 uv run pytest tests/test_golden_run.py
"""

import os
import random
from pathlib import Path

from wyraj.content.bestiary import load_bestiary
from wyraj.content.items import load_items
from wyraj.core.actions import Action, Move, Wait
from wyraj.core.game import Game
from wyraj.narration.context import ContextEnricher
from wyraj.narration.engine import NarrationEngine
from wyraj.narration.forms import build_form_registry
from wyraj.narration.templates import TemplateNarrator, load_pack

GOLDEN = Path(__file__).parent / "golden" / "seed42_walk.log"

SEED = 42
STEPS = 150


def build_script() -> list[Action]:
    """A deterministic pseudo-random walk (its own RNG — not a game stream)."""
    rng = random.Random(1234)
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
    script: list[Action] = []
    for _ in range(STEPS):
        if rng.random() < 0.1:
            script.append(Wait())
        else:
            dx, dy = rng.choice(moves)
            script.append(Move(dx, dy))
    return script


def produce_transcript() -> str:
    game = Game(seed=SEED)
    registry = build_form_registry({**load_bestiary(), **load_items()})
    narrator = TemplateNarrator(load_pack("en"), game.rng.narration, registry)
    narration = NarrationEngine(game.bus, narrator, enricher=ContextEnricher(game).enrich)
    lines: list[str] = []
    game.bus.subscribe_all(lambda e: lines.append(repr(e)))
    narration.add_sink(lambda line: lines.append(f"NARRATE: {line.text}"))
    script = build_script()
    for action in script[:20]:
        if game.game_over:
            break
        game.step(action)
    # Leave the safe wieś: place the wanderer on the path and take it.
    # (Deterministic harness step, not a player input.)
    from wyraj.core.actions import Descend
    from wyraj.core.components import Position
    from wyraj.core.map import Tile

    stairs = game.map.find_tile(Tile.STAIRS_DOWN)
    assert stairs is not None
    game.world.add(game.player, Position(*stairs))
    game.step(Descend())
    for action in script[20:]:
        if game.game_over:
            break
        game.step(action)
    lines.append(f"END turn={game.turn} game_over={game.game_over} depth={game.depth}")
    return "\n".join(lines) + "\n"


def test_golden_run_seed_42() -> None:
    transcript = produce_transcript()
    if os.environ.get("GOLDEN_REGEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(transcript, encoding="utf-8")
    expected = GOLDEN.read_text(encoding="utf-8")
    assert transcript == expected, (
        "Golden transcript changed. If intentional, regenerate with "
        "GOLDEN_REGEN=1 uv run pytest tests/test_golden_run.py"
    )
