import random
from pathlib import Path

from wyraj.core.actions import Action, Move, Wait
from wyraj.core.components import (
    Health,
    Hunger,
    Inventory,
    Position,
    StatusEffect,
    StatusEffects,
)
from wyraj.core.events import GameEvent, TurnEnded
from wyraj.core.game import Game
from wyraj.core.systems.status import apply_status
from wyraj.persistence.save import has_save, load_game, save_game


def scripted(rng: random.Random, n: int) -> list[Action]:
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    return [Move(*rng.choice(moves)) if rng.random() > 0.2 else Wait() for _ in range(n)]


def test_roundtrip_preserves_state(tmp_path: Path) -> None:
    save_file = tmp_path / "save.json.gz"
    game = Game(seed=42)
    for action in scripted(random.Random(5), 30):
        game.step(action)
    ppos = game.world.expect(game.player, Position)
    item = game.spawn_item(game.items_catalog["odwar"], ppos.x, ppos.y, 0)
    inventory = game.world.get(game.player, Inventory) or Inventory()
    game.world.add(game.player, Inventory(items=(*inventory.items, item)))
    game.world.remove(item, Position)
    apply_status(
        game.world, game.bus, game.player, StatusEffect(kind="bleeding", duration=9, power=1)
    )

    save_game(game, save_file)
    assert save_file.exists()
    loaded = load_game(save_file)
    assert loaded is not None
    assert not save_file.exists(), "save must be consumed on load (permadeath)"

    assert loaded.seed == game.seed
    assert loaded.turn == game.turn
    assert loaded.depth == game.depth
    assert loaded.codex_seen == game.codex_seen
    assert loaded.world.expect(loaded.player, Position) == game.world.expect(game.player, Position)
    assert loaded.world.expect(loaded.player, Health) == game.world.expect(game.player, Health)
    assert loaded.world.expect(loaded.player, Hunger) == game.world.expect(game.player, Hunger)
    assert item in loaded.world.expect(loaded.player, Inventory).items
    loaded_statuses = loaded.world.expect(loaded.player, StatusEffects).effects
    assert any(e.kind == "bleeding" for e in loaded_statuses)
    assert loaded.map.explored == game.map.explored


def test_roundtrip_preserves_gameplay_determinism(tmp_path: Path) -> None:
    save_file = tmp_path / "save.json.gz"
    prefix = scripted(random.Random(11), 25)
    suffix = scripted(random.Random(12), 25)

    game = Game(seed=42)
    for action in prefix:
        game.step(action)
    save_game(game, save_file)
    loaded = load_game(save_file)
    assert loaded is not None

    def run(g: Game) -> list[GameEvent]:
        log: list[GameEvent] = []
        g.bus.subscribe_all(log.append)
        for action in suffix:
            if g.game_over:
                break
            g.step(action)
        return [e for e in log if not isinstance(e, TurnEnded)]

    original_events = run(game)
    loaded_events = run(loaded)
    assert original_events == loaded_events


def test_missing_save_returns_none(tmp_path: Path) -> None:
    assert load_game(tmp_path / "nope.json.gz") is None
    assert not has_save(tmp_path / "nope.json.gz")
