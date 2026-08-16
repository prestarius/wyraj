"""Textual Pilot smoke tests (async driven via asyncio.run — no plugin needed)."""

import asyncio

from textual.widgets import RichLog

from wyraj.core.components import AI, Health, OnLevel, Position
from wyraj.ui.app import WyrajApp
from wyraj.ui.screens import (
    CodexScreen,
    ConfirmQuitScreen,
    DeathScreen,
    ExamineScreen,
    InventoryScreen,
    LegendScreen,
    ShrineScreen,
    StashScreen,
    TradeScreen,
)
from wyraj.ui.widgets import CharacterPanel, MapView


def test_app_boots_and_waits_advance_turns() -> None:
    async def run() -> None:
        app = WyrajApp(seed=42)
        async with app.run_test(size=(100, 40)) as pilot:
            assert app.query_one(MapView) is not None
            assert app.query_one(CharacterPanel) is not None
            assert app.query_one(RichLog) is not None
            start_turn = app.game.turn
            await pilot.press("full_stop")
            await pilot.press("h")
            await pilot.press("l")
            assert app.game.turn == start_turn + 3

            await pilot.press("x")
            assert isinstance(app.screen, ExamineScreen)
            await pilot.press("escape")
            await pilot.press("c")
            assert isinstance(app.screen, CodexScreen)
            await pilot.press("escape")
            await pilot.press("i")
            assert isinstance(app.screen, InventoryScreen)
            await pilot.press("escape")
            await pilot.press("L")
            assert isinstance(app.screen, LegendScreen)
            await pilot.press("escape")
            assert len(app.screen_stack) == 1  # escape must actually close the modal
            assert app.game.turn == start_turn + 3  # modals cost no turns

    asyncio.run(run())


def test_escape_closes_every_modal() -> None:
    """Regression: modals with on_key used to swallow escape via event.stop()."""

    async def run() -> None:
        app = WyrajApp(seed=42)
        async with app.run_test(size=(100, 40)) as pilot:
            modals = [
                InventoryScreen(app.game),
                StashScreen(app.game),
                ShrineScreen(app.game, "weles"),
                TradeScreen(app.game, app.game.player),
                LegendScreen(app.game),
            ]
            for modal in modals:
                app.push_screen(modal)
                await pilot.pause()
                assert len(app.screen_stack) == 2
                await pilot.press("escape")
                await pilot.pause()
                assert len(app.screen_stack) == 1, f"{type(modal).__name__} did not close"

    asyncio.run(run())


def test_quit_asks_for_confirmation() -> None:
    async def run() -> None:
        app = WyrajApp(seed=42)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.press("q")
            assert isinstance(app.screen, ConfirmQuitScreen)
            await pilot.press("n")
            await pilot.pause()
            assert len(app.screen_stack) == 1  # declined: back in the game
            await pilot.press("q")
            assert isinstance(app.screen, ConfirmQuitScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1
            await pilot.press("q")
            await pilot.press("y")
            await pilot.pause()
            assert not app.is_running  # confirmed: the app exited

    asyncio.run(run())


def test_death_screen_appears_on_game_over() -> None:
    async def run() -> None:
        app = WyrajApp(seed=42)
        async with app.run_test(size=(100, 40)) as pilot:
            # Pull a forest monster next to the player, then wait until it kills us.
            app.game._ensure_level(1)
            ppos = app.game.world.expect(app.game.player, Position)
            bies = app.game.world.entities_with(AI)[0]
            app.game.world.add(bies, OnLevel(0))
            app.game.world.add(bies, Position(ppos.x + 1, ppos.y))
            for _ in range(60):
                if app.game.game_over:
                    break
                await pilot.press("full_stop")
            await pilot.pause()
            assert app.game.game_over
            assert app.game.world.expect(app.game.player, Health).hp == 0
            assert isinstance(app.screen, DeathScreen)
            await pilot.press("n")
            await pilot.pause()
            assert app.return_value == "restart"  # "set out again"

    asyncio.run(run())


def test_death_screen_main_screen_and_quit_outcomes() -> None:
    async def run() -> None:
        for key, expected in (("m", "title"), ("q", "quit")):
            app = WyrajApp(seed=42)
            async with app.run_test(size=(100, 40)) as pilot:
                app.push_screen(DeathScreen(seed=42, turn=1))
                await pilot.pause()
                await pilot.press(key)
                await pilot.pause()
                assert app.return_value == expected

    asyncio.run(run())
