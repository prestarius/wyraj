"""Golden-run regression: fixed seed + scripted input → full transcript.

The transcript covers both the mechanical event log and the narration lines,
so any change to core simulation OR narration output shows up as a diff.
Intentional changes: regenerate with  GOLDEN_REGEN=1 uv run pytest tests/test_golden_run.py
"""

import os
import random
from pathlib import Path

from wyraj.content.bestiary import load_bestiary
from wyraj.core.actions import Action, Move, Wait
from wyraj.core.game import Game
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
    registry = build_form_registry(load_bestiary())
    narrator = TemplateNarrator(load_pack("en"), game.rng.narration, registry)
    narration = NarrationEngine(game.bus, narrator)
    lines: list[str] = []
    game.bus.subscribe_all(lambda e: lines.append(repr(e)))
    narration.add_sink(lambda line: lines.append(f"NARRATE: {line.text}"))
    for action in build_script():
        if game.game_over:
            break
        game.step(action)
    lines.append(f"END turn={game.turn} game_over={game.game_over}")
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
