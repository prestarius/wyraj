from wyraj.core.actions import Move, Wait
from wyraj.core.components import AI, Health, OnLevel, Position
from wyraj.core.events import GameEvent
from wyraj.core.game import Game


def test_game_boots_deterministically() -> None:
    a = Game(seed=42)
    b = Game(seed=42)
    assert a.map.tiles == b.map.tiles
    assert a.world.expect(a.player, Position) == b.world.expect(b.player, Position)
    a._ensure_level(1)
    b._ensure_level(1)
    monsters_a = [a.world.expect(e, Position) for e in a.world.entities_with(AI)]
    monsters_b = [b.world.expect(e, Position) for e in b.world.entities_with(AI)]
    assert monsters_a == monsters_b
    assert len(monsters_a) == 6


def test_scripted_run_same_event_log() -> None:
    script = [Move(1, 0), Move(0, 1), Wait(), Move(-1, 0)] * 5

    def run() -> list[GameEvent]:
        game = Game(seed=42)
        log: list[GameEvent] = []
        game.bus.subscribe_all(log.append)
        for action in script:
            game.step(action)
        return log

    first, second = run(), run()
    assert first == second
    assert len(first) >= len(script)  # at least TurnEnded per action


def test_surrounded_player_eventually_dies() -> None:
    game = Game(seed=42)
    # Pull a forest monster into the village, right next to the player.
    game._ensure_level(1)
    ppos = game.world.expect(game.player, Position)
    bies = game.world.entities_with(AI)[0]
    game.world.add(bies, OnLevel(0))
    game.world.add(bies, Position(ppos.x + 1, ppos.y))
    for _ in range(200):
        if game.game_over:
            break
        game.step(Wait())
    assert game.game_over
    assert game.world.expect(game.player, Health).hp == 0
    assert game.world.is_alive(game.player)  # kept for the death screen
