from wyraj.core.actions import BuyItem, Move
from wyraj.core.components import Inventory, Item, OnLevel, Position, Purse, Villager
from wyraj.core.events import DziadRecognized, TalkedTo
from wyraj.core.game import Game
from wyraj.core.systems.movement import level_of
from wyraj.persistence.meta import MetaState


def find_dziad(game: Game) -> int | None:
    for entity, (villager,) in game.world.query(Villager):
        if villager.role == "dziad_wedrowny":
            return entity
    return None


def ensure_dziad(game: Game) -> int:
    for depth in range(3, 6):
        game._ensure_level(depth)
        if game.dziad_seen_this_run:
            break
    dziad = find_dziad(game)
    assert dziad is not None, "pity guarantee must have fired by the deepest crypt"
    return dziad


def test_pity_guarantee_by_deepest_level() -> None:
    for seed in range(5):
        game = Game(seed=seed, meta=MetaState(), meta_autosave=False)
        ensure_dziad(game)


def test_never_spawns_above_first_eligible() -> None:
    game = Game(seed=42, meta=MetaState(), meta_autosave=False)
    game._ensure_level(1)
    game._ensure_level(2)
    assert find_dziad(game) is None


def test_stock_tiers_gate_on_reputation() -> None:
    low = Game(seed=42, meta=MetaState(), meta_autosave=False)
    tier1_only = set(low.dziad_shop.stock_pool(0))
    assert "ciupaga" not in tier1_only and "zurawie_pioro" not in tier1_only

    rich_meta = MetaState()
    rich_meta.dziad.reputation = 6
    high = Game(seed=42, meta=rich_meta, meta_autosave=False)
    full_pool = set(high.dziad_shop.stock_pool(6))
    assert {"ciupaga", "zurawie_pioro"} <= full_pool


def test_dziad_prices_are_cruel_but_soften_with_rep() -> None:
    meta = MetaState()
    game = Game(seed=42, meta=meta, meta_autosave=False)
    dziad = ensure_dziad(game)
    base = game.prices.buy["odwar"]
    cruel = game.price_for("odwar", dziad)
    assert cruel == round(base * game.prices.dziad_multiplier)
    meta.dziad.reputation = 5
    assert game.price_for("odwar", dziad) < cruel


def test_meeting_and_recognition() -> None:
    meta = MetaState()
    meta.dziad.reputation = 3
    game = Game(seed=42, meta=meta, meta_autosave=False)
    dziad = ensure_dziad(game)
    ddepth = level_of(game.world, dziad)
    game.depth = ddepth
    game.world.add(game.player, OnLevel(ddepth))
    dpos = game.world.expect(dziad, Position)
    game.world.add(game.player, Position(dpos.x - 1, dpos.y))

    talks: list[TalkedTo] = []
    known: list[DziadRecognized] = []
    game.bus.subscribe(TalkedTo, talks.append)
    game.bus.subscribe(DziadRecognized, known.append)
    game.step(Move(1, 0))
    assert talks and talks[0].role == "dziad_wedrowny"
    assert known and known[0].reputation == 3
    assert meta.dziad.met_count == 1

    game.step(Move(1, 0))  # second bump: no second recognition, no double count
    assert len(known) == 1
    assert meta.dziad.met_count == 1


def test_depth_purchase_spends_purse_and_earns_rep_once() -> None:
    meta = MetaState()
    game = Game(seed=42, meta=meta, meta_autosave=False)
    dziad = ensure_dziad(game)
    ddepth = level_of(game.world, dziad)
    game.depth = ddepth
    game.world.add(game.player, OnLevel(ddepth))
    dpos = game.world.expect(dziad, Position)
    game.world.add(game.player, Position(dpos.x - 1, dpos.y))
    stock = game.world.expect(dziad, Inventory).items
    assert stock
    key = game.world.expect(stock[0], Item).key
    price = game.price_for(key, dziad)
    game.world.add(game.player, Purse(denary=price + 10))
    game.step(BuyItem(trader=dziad, item=stock[0]))
    assert game.world.expect(game.player, Purse).denary == 10
    assert stock[0] in game.world.expect(game.player, Inventory).items
    assert meta.dziad.reputation == 1
    if len(stock) > 1:
        game.world.add(game.player, Purse(denary=1000))
        game.step(BuyItem(trader=dziad, item=stock[1]))
        assert meta.dziad.reputation == 1  # capped +1 per run
