from wyraj.core.actions import Wait
from wyraj.core.components import AI, Health, Lore, OnLevel, Position
from wyraj.core.game import Game
from wyraj.persistence.meta import MetaState


def die_to(game: Game, monster_key: str | None = None) -> None:
    """Drag a monster (optionally of a given kind) next to the player and wait."""
    game._ensure_level(1)
    candidates = [
        e
        for e in game.world.entities_with(AI)
        if monster_key is None or game.world.expect(e, Lore).key == monster_key
    ]
    if not candidates:
        bies = game.spawn_monster(game.bestiary[monster_key or "bies"], 1, 1, 0)
        candidates = [bies]
    monster = candidates[0]
    ppos = game.world.expect(game.player, Position)
    game.world.add(monster, OnLevel(0))
    game.world.add(monster, Position(ppos.x + 1, ppos.y))
    game.world.add(game.player, Health(1, 24))
    for _ in range(80):
        if game.game_over:
            return
        game.step(Wait())
    raise AssertionError("player refused to die")


def test_death_updates_counters_and_deepest() -> None:
    meta = MetaState()
    game = Game(seed=42, meta=meta, meta_autosave=False)
    game.max_depth_reached = 3
    die_to(game, "strzyga")
    unlocked = game.apply_death_to_meta()
    assert meta.achievements["runs"] == 1
    assert meta.achievements["strzyga_deaths"] == 1
    assert meta.achievements["deepest_level"] == 3
    assert unlocked == []


def test_strzygobojca_unlocks_on_third_strzyga_death() -> None:
    meta = MetaState()
    meta.achievements["strzyga_deaths"] = 2
    game = Game(seed=42, meta=meta, meta_autosave=False)
    die_to(game, "strzyga")
    unlocked = game.apply_death_to_meta()
    assert unlocked == ["strzygobojca"]
    assert "strzygobojca" in meta.unlocks.origins
    # Already unlocked — never announced twice.
    game2 = Game(seed=7, meta=meta, meta_autosave=False)
    die_to(game2, "strzyga")
    assert game2.apply_death_to_meta() == []


def test_dziadowy_uczen_unlocks_via_reputation() -> None:
    meta = MetaState()
    meta.dziad.reputation = 5
    game = Game(seed=42, meta=meta, meta_autosave=False)
    die_to(game)
    assert "dziadowy_uczen" in game.apply_death_to_meta()


def test_unlocked_origin_is_playable() -> None:
    meta = MetaState()
    meta.unlocks.origins.append("strzygobojca")
    game = Game(seed=42, origin="strzygobojca", meta=meta, meta_autosave=False)
    assert game.origin.name == "Strzygobójca"


def test_morgue_mentions_meta(tmp_path) -> None:
    from datetime import datetime

    from wyraj.persistence.morgue import write_morgue

    meta = MetaState()
    meta.currency.denary = 77
    game = Game(seed=42, meta=meta, meta_autosave=False)
    text = write_morgue(game, when=datetime(2026, 8, 15, 13, 0, 0), directory=tmp_path).read_text()
    assert "Banked in the wieś: 77 denary" in text
