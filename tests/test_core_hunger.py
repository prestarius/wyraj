from wyraj.core.actions import Wait
from wyraj.core.components import Health, Hunger
from wyraj.core.events import HungerChanged, StarvationHit
from wyraj.core.game import Game


def test_satiation_drains_per_turn() -> None:
    game = Game(seed=42)
    start = game.world.expect(game.player, Hunger).satiation
    game.step(Wait())
    game.step(Wait())
    assert game.world.expect(game.player, Hunger).satiation == start - 2


def test_band_transition_emits_event() -> None:
    game = Game(seed=42)
    game.world.add(game.player, Hunger(201, 600))
    changed: list[HungerChanged] = []
    game.bus.subscribe(HungerChanged, changed.append)
    game.step(Wait())
    assert changed and changed[0].band == "hungry"


def test_starvation_damages_and_can_kill() -> None:
    game = Game(seed=42)
    game.world.add(game.player, Hunger(0, 600))
    game.world.add(game.player, Health(2, 20))
    hits: list[StarvationHit] = []
    game.bus.subscribe(StarvationHit, hits.append)
    for _ in range(30):
        if game.game_over:
            break
        game.step(Wait())
    assert hits, "starvation should tick damage"
    assert game.game_over
    assert game.world.expect(game.player, Health).hp == 0
