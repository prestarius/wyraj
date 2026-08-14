"""Textual Pilot smoke tests (async driven via asyncio.run — no plugin needed)."""

import asyncio

from textual.widgets import RichLog

from wyraj.core.components import AI, Health, OnLevel, Position
from wyraj.ui.app import WyrajApp
from wyraj.ui.screens import CodexScreen, DeathScreen, ExamineScreen, InventoryScreen
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
            assert app.game.turn == start_turn + 3  # modals cost no turns

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

    asyncio.run(run())
