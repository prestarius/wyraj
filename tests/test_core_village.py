from tests.conftest import goto_depth
from wyraj.core.actions import BuyItem, Move, Rest, SellItem, Wait
from wyraj.core.components import (
    Health,
    Hunger,
    Inventory,
    Position,
    Swimmer,
    Villager,
)
from wyraj.core.events import ItemBought, ItemSold, Rested, TalkedTo
from wyraj.core.game import Game
from wyraj.core.map import Tile


def find_villager(game: Game, role: str) -> int:
    for entity, (villager,) in game.world.query(Villager):
        if villager.role == role:
            return entity
    raise AssertionError(f"no {role} in the village")


def test_bump_villager_talks_instead_of_attacking() -> None:
    game = Game(seed=42)
    dziad = find_villager(game, "gossip")
    ppos = game.world.expect(game.player, Position)
    game.world.add(dziad, Position(ppos.x + 1, ppos.y))
    talks: list[TalkedTo] = []
    game.bus.subscribe(TalkedTo, talks.append)
    game.step(Move(1, 0))
    assert talks and talks[0].role == "gossip"
    assert game.world.expect(dziad, Health).hp == 10  # unharmed


def test_rest_heals_in_village_only() -> None:
    game = Game(seed=42)
    game.world.add(game.player, Health(5, 20))
    rested: list[Rested] = []
    game.bus.subscribe(Rested, rested.append)
    game.step(Rest())
    assert game.world.expect(game.player, Health).hp == 20
    assert rested
    hunger = game.world.expect(game.player, Hunger)
    assert hunger.satiation < hunger.max_satiation - 50

    goto_depth(game, 1)
    game.world.add(game.player, Health(5, 20))
    game.step(Rest())
    assert game.world.expect(game.player, Health).hp == 5  # no rest in the wild


def test_buy_from_village_trader_spends_banked_wallet() -> None:
    game = Game(seed=42, meta_autosave=False)
    game.meta.currency.denary = 500
    trader = find_villager(game, "trader")
    stock = game.world.expect(trader, Inventory).items
    want = stock[0]
    from wyraj.core.components import Item

    price = game.price_for(game.world.expect(want, Item).key, trader)
    bought: list[ItemBought] = []
    game.bus.subscribe(ItemBought, bought.append)
    game.step(BuyItem(trader=trader, item=want))
    assert want in game.world.expect(game.player, Inventory).items
    assert game.meta.currency.denary == 500 - price
    assert bought and bought[0].price == price


def test_buy_refused_when_broke() -> None:
    game = Game(seed=42, meta_autosave=False)
    game.meta.currency.denary = 0
    trader = find_villager(game, "trader")
    stock = game.world.expect(trader, Inventory).items
    game.step(BuyItem(trader=trader, item=stock[0]))
    assert stock[0] not in game.world.expect(game.player, Inventory).items
    assert game.meta.currency.denary == 0


def test_sell_trophy_earns_denary() -> None:
    game = Game(seed=42, meta_autosave=False)
    trader = find_villager(game, "trader")
    trophy = game.spawn_stock_item("zab_strzygi")
    inv = game.world.get(game.player, Inventory) or Inventory()
    game.world.add(game.player, Inventory(items=(*inv.items, trophy)))
    sold: list[ItemSold] = []
    game.bus.subscribe(ItemSold, sold.append)
    game.step(SellItem(trader=trader, item=trophy))
    assert trophy not in game.world.expect(game.player, Inventory).items
    assert game.meta.currency.denary == game.sell_price_for("zab_strzygi")
    assert sold and sold[0].item.key == "zab_strzygi"


def test_bagna_has_water_and_swimming_utopce() -> None:
    game = Game(seed=42)
    game._ensure_level(2)
    bagna = game.levels[2]
    water = [
        (x, y)
        for y in range(bagna.height)
        for x in range(bagna.width)
        if bagna.tiles[y][x] is Tile.WATER
    ]
    assert water, "the marsh must have pools"
    assert not bagna.is_walkable(*water[0])
    assert bagna.is_transparent(*water[0])

    # A spawned utopiec swims: it can step into open water, the player cannot.
    wx, wy = water[0]
    utopiec = game.spawn_monster(game.bestiary["utopiec"], wx - 1, wy, 2)
    assert game.world.has(utopiec, Swimmer)
    from wyraj.core.systems.ai import _step

    game.world.add(utopiec, Position(wx - 1, wy))
    assert _step(game.world, bagna, utopiec, 1, 0)  # into the pool
    assert game.world.expect(utopiec, Position) == Position(wx, wy)


def test_village_turns_still_advance() -> None:
    game = Game(seed=42)
    game.step(Wait())
    assert game.turn == 1
