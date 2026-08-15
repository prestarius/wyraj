import random

from wyraj.core.components import Health, Melee, Position
from wyraj.core.events import EntityRef, LoreDiscovered
from wyraj.core.game import Game
from wyraj.core.systems.combat import attack
from wyraj.persistence.meta import MetaState


def slay(game: Game, key: str) -> None:
    monster = game.spawn_monster(game.bestiary[key], 2, 2, 0)
    game.world.add(monster, Health(1, 1))
    game.world.add(game.player, Position(1, 2))
    game.world.add(game.player, Melee(damage=99, to_hit=100))
    attack(game.world, game.bus, random.Random(1), game.player, monster)


def test_kills_raise_codex_tier() -> None:
    meta = MetaState()
    game = Game(seed=42, meta=meta, meta_autosave=False)
    assert game.codex_tier("wilk") == "unknown"
    slay(game, "wilk")
    assert game.codex_tier("wilk") == "partial"
    slay(game, "wilk")
    assert game.codex_tier("wilk") == "partial"
    slay(game, "wilk")
    assert game.codex_tier("wilk") == "full"
    assert meta.achievements["kills_wilk"] == 3


def test_glimpse_never_downgrades_knowledge() -> None:
    meta = MetaState()
    meta.codex.known["strzyga"] = "full"
    game = Game(seed=42, meta=meta, meta_autosave=False)
    game.bus.publish(LoreDiscovered(entity=EntityRef(entity=99, key="strzyga", name="strzyga")))
    assert game.codex_tier("strzyga") == "full"


def test_knowledge_persists_into_next_run() -> None:
    meta = MetaState()
    first = Game(seed=1, meta=meta, meta_autosave=False)
    slay(first, "utopiec")
    assert meta.codex.known["utopiec"] == "partial"

    second = Game(seed=2, meta=meta, meta_autosave=False)
    assert "utopiec" in second.codex_seen  # no re-discovery event next run
    assert second.codex_tier("utopiec") == "partial"


def test_hooks_do_not_enter_bestiary_codex() -> None:
    meta = MetaState()
    game = Game(seed=42, meta=meta, meta_autosave=False)
    game.bus.publish(LoreDiscovered(entity=EntityRef(entity=99, key="kapliczka", name="chapel")))
    assert "kapliczka" not in meta.codex.known
