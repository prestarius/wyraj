from wyraj.content.hooks import load_hooks
from wyraj.core.actions import Wait
from wyraj.core.components import Lore, Position, StoryHook
from wyraj.core.events import LoreDiscovered
from wyraj.core.game import Game
from wyraj.core.systems.movement import level_of
from wyraj.narration.templates import load_pack


def test_hooks_load_three_per_biome() -> None:
    hooks = load_hooks()
    for biome in ("puszcza", "kurhany", "bagna"):
        assert len([h for h in hooks.values() if biome in h.biomes]) == 3


def test_every_hook_has_discovery_narration() -> None:
    pack = load_pack("en")
    for key in load_hooks():
        assert ("lore_discovered", key) in pack.rules, f"hook {key} lacks a first-sight line"


def test_levels_are_seeded_with_hooks() -> None:
    game = Game(seed=42)
    game._ensure_level(1)
    forest_hooks = [
        game.world.expect(e, Lore).key
        for e, _ in game.world.query(StoryHook)
        if level_of(game.world, e) == 1
    ]
    assert len(forest_hooks) == 3
    game._ensure_level(3)
    crypt_hooks = [
        game.world.expect(e, Lore).key
        for e, _ in game.world.query(StoryHook)
        if level_of(game.world, e) == 3
    ]
    assert len(crypt_hooks) == 3
    allowed = {k for k, h in game.hooks_catalog.items() if "kurhany" in h.biomes}
    assert set(crypt_hooks) <= allowed


def test_hook_discovery_emits_once() -> None:
    game = Game(seed=42)
    discovered: list[LoreDiscovered] = []
    game.bus.subscribe(LoreDiscovered, discovered.append)
    game._ensure_level(1)
    hook = next(e for e, _ in game.world.query(StoryHook) if level_of(game.world, e) == 1)
    from wyraj.core.components import OnLevel

    game.world.add(hook, OnLevel(0))
    ppos = game.world.expect(game.player, Position)
    game.world.add(hook, Position(ppos.x + 1, ppos.y))
    game.step(Wait())
    keys = [e.entity.key for e in discovered]
    hook_key = game.world.expect(hook, Lore).key
    assert hook_key in keys
    game.step(Wait())
    assert [k for k in (e.entity.key for e in discovered) if k == hook_key] == [hook_key]
