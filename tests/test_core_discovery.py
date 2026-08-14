from wyraj.core.actions import Wait
from wyraj.core.components import AI, Position
from wyraj.core.events import LoreDiscovered
from wyraj.core.game import Game


def test_first_sighting_emits_lore_discovered_once() -> None:
    game = Game(seed=42)
    discovered: list[LoreDiscovered] = []
    game.bus.subscribe(LoreDiscovered, discovered.append)

    ppos = game.world.expect(game.player, Position)
    monster = game.world.entities_with(AI)[0]
    game.world.add(monster, Position(ppos.x + 1, ppos.y))

    game.step(Wait())
    keys = [e.entity.key for e in discovered]
    assert len(keys) >= 1
    assert keys[0] in game.codex_seen

    count_before = len(discovered)
    game.step(Wait())
    same_kind = [e for e in discovered[count_before:] if e.entity.key == keys[0]]
    assert not same_kind, "a kind is discovered only once per run"


def test_codex_starts_empty() -> None:
    game = Game(seed=42)
    # Spawns are at least FOV-radius away, so nothing is discovered at boot.
    assert game.codex_seen == set()
