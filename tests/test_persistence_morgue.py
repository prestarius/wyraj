from datetime import datetime
from pathlib import Path

from tests.conftest import goto_depth
from wyraj.core.game import Game
from wyraj.persistence.history import recent_runs, record_run
from wyraj.persistence.morgue import write_morgue

WHEN = datetime(2026, 8, 15, 12, 0, 0)


def test_morgue_file_contents(tmp_path: Path) -> None:
    game = Game(seed=42, origin="zielarka")
    goto_depth(game, 3)
    game.death_cause = "slain by strzyga"
    game.codex_seen.add("strzyga")
    path = write_morgue(game, when=WHEN, directory=tmp_path)
    text = path.read_text()
    assert "Zielarka" in text
    assert "Seed: 42" in text
    assert "kurhan level 1" in text
    assert "slain by strzyga" in text
    assert "strzyga" in text
    assert path.name == "20260815-120000-seed42.txt"


def test_morgue_without_cause(tmp_path: Path) -> None:
    game = Game(seed=1)
    path = write_morgue(game, when=WHEN, directory=tmp_path)
    assert "lost to the forest" in path.read_text()


def test_history_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    record_run(
        seed=42,
        origin="najemnik",
        turns=120,
        max_depth=3,
        cause="slain by bies",
        when=WHEN,
        db_path=db,
    )
    record_run(
        seed=7,
        origin="zielarka",
        turns=15,
        max_depth=0,
        cause="starved, far from any table",
        when=WHEN,
        db_path=db,
    )
    runs = recent_runs(db_path=db)
    assert len(runs) == 2
    assert runs[0].seed == 7  # newest first
    assert runs[1].cause == "slain by bies"
    assert recent_runs(db_path=tmp_path / "missing.db") == []


def test_death_cause_tracked_in_combat() -> None:
    from wyraj.core.actions import Wait
    from wyraj.core.components import AI, Health, Lore, OnLevel, Position

    game = Game(seed=42)
    game._ensure_level(1)
    game.world.add(game.player, Health(1, 24))
    ppos = game.world.expect(game.player, Position)
    monster = game.world.entities_with(AI)[0]
    game.world.add(monster, OnLevel(0))
    game.world.add(monster, Position(ppos.x + 1, ppos.y))
    monster_name = game.world.expect(monster, Lore).name
    for _ in range(60):
        if game.game_over:
            break
        game.step(Wait())
    assert game.game_over
    assert game.death_cause == f"slain by {monster_name}"
