from tests.conftest import goto_depth
from wyraj.core.actions import Move, UseItem, Wait
from wyraj.core.components import (
    AI,
    Channeling,
    Health,
    Inventory,
    OnLevel,
    Perch,
    Position,
    Purse,
    Znamie,
)
from wyraj.core.events import (
    CoinsBanked,
    CraneRefused,
    CraneReturn,
    CraneSummonCompleted,
    CraneSummonInterrupted,
    CraneSummonStarted,
)
from wyraj.core.game import Game
from wyraj.core.map import Tile
from wyraj.persistence.meta import MetaState


def new_game() -> Game:
    return Game(seed=42, meta=MetaState(), meta_autosave=False)


def give_feather(game: Game) -> int:
    feather = game.spawn_stock_item("zurawie_pioro")
    inv = game.world.get(game.player, Inventory) or Inventory()
    game.world.add(game.player, Inventory(items=(*inv.items, feather)))
    return feather


def clear_watchers(game: Game) -> None:
    for entity in game.world.entities_with(AI):
        pos = game.world.expect(entity, Position)
        if (pos.x, pos.y) in game.map.visible:
            game.world.destroy(entity)


def test_refused_in_village_keeps_feather() -> None:
    game = new_game()
    feather = give_feather(game)
    refusals: list[CraneRefused] = []
    game.bus.subscribe(CraneRefused, refusals.append)
    game.step(UseItem(item=feather))
    assert refusals and refusals[0].reason == "in_village"
    assert game.world.is_alive(feather)


def test_refused_without_sky_in_crypt() -> None:
    game = new_game()
    goto_depth(game, 3)
    clear_watchers(game)
    feather = give_feather(game)
    ppos = game.world.expect(game.player, Position)
    assert game.map.tiles[ppos.y][ppos.x] is not Tile.SHAFT  # arrive on stairs
    refusals: list[CraneRefused] = []
    game.bus.subscribe(CraneRefused, refusals.append)
    game.step(UseItem(item=feather))
    assert refusals and refusals[0].reason == "no_sky"
    assert game.world.is_alive(feather)


def test_refused_while_watched() -> None:
    game = new_game()
    goto_depth(game, 1)
    feather = give_feather(game)
    ppos = game.world.expect(game.player, Position)
    bies = game.spawn_monster(game.bestiary["bies"], ppos.x + 1, ppos.y, 1)
    game._update_player_fov()
    assert bies in game.world.entities_with(AI)
    refusals: list[CraneRefused] = []
    game.bus.subscribe(CraneRefused, refusals.append)
    game.step(UseItem(item=feather))
    assert refusals and refusals[0].reason == "watched"
    assert game.world.is_alive(feather)


def full_flight(game: Game) -> list:
    events: list = []
    for kind in (CraneSummonStarted, CraneSummonCompleted, CoinsBanked):
        game.bus.subscribe(kind, events.append)
    feather = give_feather(game)
    game.step(UseItem(item=feather))
    assert not game.world.is_alive(feather)  # consumed on the call
    for _ in range(6):
        game.step(Wait())
    return events


def test_full_flight_home_banks_and_marks() -> None:
    game = new_game()
    goto_depth(game, 1)
    clear_watchers(game)
    game.world.add(game.player, Purse(denary=30))
    origin_pos = game.world.expect(game.player, Position)
    events = full_flight(game)
    kinds = [type(e).__name__ for e in events]
    assert "CraneSummonStarted" in kinds
    assert "CraneSummonCompleted" in kinds
    assert "CoinsBanked" in kinds  # arrival banks the purse
    assert game.depth == 0
    perch = game.world.entities_with(Perch)[0]
    assert game.world.expect(game.player, Position) == game.world.expect(perch, Position)
    marks = game.world.entities_with(Znamie)
    assert len(marks) == 1
    assert game.world.expect(marks[0], Position) == origin_pos
    assert game.meta.currency.denary == 30


def test_perch_return_consumes_znamie() -> None:
    game = new_game()
    goto_depth(game, 1)
    clear_watchers(game)
    origin_pos = game.world.expect(game.player, Position)
    full_flight(game)
    returns: list[CraneReturn] = []
    game.bus.subscribe(CraneReturn, returns.append)
    # Step off the perch and back on: the return fires on arrival.
    game.step(Move(1, 0))
    game.step(Move(-1, 0))
    assert returns and returns[0].depth == 1
    assert game.depth == 1
    assert game.world.expect(game.player, Position) == origin_pos
    assert game.world.entities_with(Znamie) == []


def test_moving_breaks_channel_and_feather_stays_lost() -> None:
    game = new_game()
    goto_depth(game, 1)
    clear_watchers(game)
    feather = give_feather(game)
    interruptions: list[CraneSummonInterrupted] = []
    game.bus.subscribe(CraneSummonInterrupted, interruptions.append)
    game.step(UseItem(item=feather))
    game.step(Wait())
    game.step(Move(1, 0))
    assert interruptions and interruptions[0].reason == "moved"
    assert game.world.get(game.player, Channeling) is None
    assert not game.world.is_alive(feather)
    assert game.depth == 1


def test_damage_breaks_channel() -> None:
    game = new_game()
    goto_depth(game, 1)
    clear_watchers(game)
    feather = give_feather(game)
    game.step(UseItem(item=feather))
    assert game.world.get(game.player, Channeling) is not None
    # A monster arrives mid-channel and draws blood.
    ppos = game.world.expect(game.player, Position)
    game.spawn_monster(game.bestiary["bies"], ppos.x + 1, ppos.y, 1)
    interruptions: list[CraneSummonInterrupted] = []
    game.bus.subscribe(CraneSummonInterrupted, interruptions.append)
    for _ in range(20):
        if interruptions or game.game_over:
            break
        game.step(Wait())
    assert interruptions and interruptions[0].reason == "damage"


def test_crypt_shafts_exist_and_allow_flight() -> None:
    game = new_game()
    for depth in (3, 4, 5):
        game._ensure_level(depth)
        shafts = [
            (x, y)
            for y in range(game.levels[depth].height)
            for x in range(game.levels[depth].width)
            if game.levels[depth].tiles[y][x] is Tile.SHAFT
        ]
        assert 1 <= len(shafts) <= 2

    goto_depth(game, 3)
    clear_watchers(game)
    shaft = next(
        (x, y)
        for y in range(game.map.height)
        for x in range(game.map.width)
        if game.map.tiles[y][x] is Tile.SHAFT
    )
    game.world.add(game.player, Position(*shaft))
    game._update_player_fov()
    clear_watchers(game)
    feather = give_feather(game)
    started: list[CraneSummonStarted] = []
    game.bus.subscribe(CraneSummonStarted, started.append)
    game.step(UseItem(item=feather))
    assert started, "shaft tile must open the sky"


def test_player_survives_flight_bookkeeping() -> None:
    game = new_game()
    goto_depth(game, 2)
    clear_watchers(game)
    full_flight(game)
    assert game.world.expect(game.player, OnLevel).depth == 0
    assert game.world.expect(game.player, Health).hp > 0
