import asyncio

from wyraj.content.origins import load_origins
from wyraj.core.components import Health, Hunger, Inventory, Item, Melee
from wyraj.core.game import Game


def test_origins_load() -> None:
    origins = load_origins()
    assert set(origins) == {
        "wygnaniec",
        "zielarka",
        "najemnik",
        "strzygobojca",
        "dziadowy_uczen",
    }
    for origin in origins.values():
        assert origin.intro and origin.description
    base = [o for o in origins.values() if o.unlock is None]
    assert {o.key for o in base} == {"wygnaniec", "zielarka", "najemnik"}


def test_origin_stats_and_kit_apply() -> None:
    game = Game(seed=42, origin="zielarka")
    assert game.world.expect(game.player, Health).max_hp == 18
    assert game.world.expect(game.player, Melee).to_hit == 70
    inventory = game.world.expect(game.player, Inventory)
    keys = sorted(game.world.expect(e, Item).key for e in inventory.items)
    assert keys == ["gromnica", "odwar", "odwar", "sol_swiecona"]

    najemnik = Game(seed=42, origin="najemnik")
    assert najemnik.world.expect(najemnik.player, Melee).to_hit == 80
    kit = {
        najemnik.world.expect(e, Item).key
        for e in najemnik.world.expect(najemnik.player, Inventory).items
    }
    assert kit == {"toporek", "wilcza_skora"}


def test_default_origin_is_wygnaniec() -> None:
    game = Game(seed=42)
    assert game.origin.key == "wygnaniec"
    assert game.world.expect(game.player, Health).max_hp == 24
    assert game.world.expect(game.player, Hunger).max_satiation == 500


def test_same_seed_same_origin_same_world() -> None:
    a = Game(seed=7, origin="najemnik")
    b = Game(seed=7, origin="najemnik")
    assert a.map.tiles == b.map.tiles


def test_origin_select_app() -> None:
    from wyraj.ui.origin_select import OriginApp

    async def run() -> None:
        app = OriginApp(load_origins())
        async with app.run_test(size=(90, 30)) as pilot:
            await pilot.press("down")
            await pilot.press("enter")
        assert app.return_value == sorted(load_origins())[1]

    asyncio.run(run())
