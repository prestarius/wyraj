"""Próg (intro/onboarding) tests: content schemas, szept behavior, screens."""

import asyncio

from wyraj.content.intro import load_help, load_prologue, load_szept, load_title_lines
from wyraj.core.actions import Move, Wait
from wyraj.core.components import AI, Health, OnLevel, Position
from wyraj.core.game import Game
from wyraj.narration.szept import CORE_TRIGGERS, SzeptSystem
from wyraj.persistence.meta import MetaState

# -- content ------------------------------------------------------------


def test_title_lines_exist_both_languages() -> None:
    for lang in ("en", "pl"):
        lines = load_title_lines(lang)
        assert len(lines) >= 3
        assert all(line.strip() for line in lines)


def test_prologue_schema_and_parity() -> None:
    for lang in ("en", "pl"):
        prologue = load_prologue(lang)
        assert len(prologue.common) == 3
        assert prologue.fallback.strip()
        assert {"wygnaniec", "zielarka", "najemnik"} <= set(prologue.origins)
        for page in [*prologue.common, prologue.fallback, *prologue.origins.values()]:
            assert page.strip()


def test_szept_tables_cover_all_triggers() -> None:
    for lang in ("en", "pl"):
        table = load_szept(lang)
        missing = [k for k in (*CORE_TRIGGERS, "farewell") if k not in table]
        assert not missing, f"{lang} szept missing {missing}"


def test_help_loads_both_languages() -> None:
    for lang in ("en", "pl"):
        help_text = load_help(lang)
        assert help_text.title and help_text.keys and help_text.world


# -- szept behavior -----------------------------------------------------


def szept_game(enabled: bool = True) -> tuple[Game, list[str]]:
    game = Game(seed=42, meta=MetaState(), meta_autosave=False)
    heard: list[str] = []
    SzeptSystem(game, table=load_szept("en"), sink=heard.append, enabled=enabled)
    return game, heard


def test_first_move_whispers_once_and_persists() -> None:
    game, heard = szept_game()
    game.step(Move(0, -1))
    game.step(Move(0, 1))
    moves = [h for h in heard if "village is quiet" in h]
    assert len(moves) == 1
    assert "first_move" in game.meta.szept_seen

    # A later run sharing the profile stays silent about it.
    second = Game(seed=7, meta=game.meta, meta_autosave=False)
    heard2: list[str] = []
    SzeptSystem(second, table=load_szept("en"), sink=heard2.append)
    second.step(Move(0, -1))
    assert not [h for h in heard2 if "village is quiet" in h]


def test_hints_off_stays_silent() -> None:
    game, heard = szept_game(enabled=False)
    game.step(Move(0, -1))
    game.step(Wait())
    assert heard == []
    assert game.meta.szept_seen == []


def test_hostile_and_kill_whispers() -> None:
    game, heard = szept_game()
    game._ensure_level(1)
    monster = game.world.entities_with(AI)[0]
    ppos = game.world.expect(game.player, Position)
    game.world.add(monster, OnLevel(0))
    game.world.add(monster, Position(ppos.x + 1, ppos.y))
    game.world.add(monster, Health(1, 1))
    game.step(Wait())  # sighting
    assert any("bump into" in h for h in heard)
    game.step(Move(1, 0))  # kill it
    assert any("codex remembers" in h for h in heard)


def test_forest_edge_fires_on_village_stairs() -> None:
    from wyraj.core.map import Tile

    game, heard = szept_game()
    spot = game.map.find_tile(Tile.STAIRS_DOWN)
    assert spot is not None
    game.world.add(game.player, Position(*spot))
    game.step(Wait())
    assert any("puszcza begins" in h for h in heard)


def test_farewell_after_all_core_triggers() -> None:
    game, heard = szept_game()
    system_meta = game.meta
    system_meta.szept_seen = list(CORE_TRIGGERS[:-1])  # all but one
    game._ensure_level(1)
    monster = game.world.entities_with(AI)[0]
    game.world.add(monster, OnLevel(0))
    game.world.add(monster, Health(1, 1))
    ppos = game.world.expect(game.player, Position)
    game.world.add(monster, Position(ppos.x + 1, ppos.y))
    game.step(Move(1, 0))  # the last core trigger: first_kill
    assert any("whispers fall silent" in h for h in heard)
    assert "farewell" in system_meta.szept_seen


# -- screens ------------------------------------------------------------


def test_title_menu_flow() -> None:
    from wyraj.ui.title import TitleApp

    async def run() -> None:
        app = TitleApp(MetaState(), has_save=False, rng_seed=1)
        async with app.run_test(size=(100, 34)) as pilot:
            entries = [key for key, _ in app._menu_entries()]
            assert "continue" not in entries  # no save yet
            await pilot.press("enter")  # first entry: New Journey
        assert app.return_value == "new"

    asyncio.run(run())


def test_title_continue_when_save_exists() -> None:
    from wyraj.ui.title import TitleApp

    async def run() -> None:
        app = TitleApp(MetaState(), has_save=True, rng_seed=1)
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.press("down")
            await pilot.press("enter")
        assert app.return_value == "continue"

    asyncio.run(run())


def test_prologue_skip_and_readthrough() -> None:
    from wyraj.ui.prologue import PrologueApp

    async def skip() -> None:
        app = PrologueApp("wygnaniec", text_speed="instant")
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.press("escape")
        assert app.return_value is False

    async def read() -> None:
        app = PrologueApp("zielarka", text_speed="instant")
        async with app.run_test(size=(100, 34)) as pilot:
            for _ in range(len(app.pages)):
                await pilot.press("enter")
        assert app.return_value is True

    asyncio.run(skip())
    asyncio.run(read())


def test_help_screen_opens_in_game() -> None:
    from wyraj.ui.app import WyrajApp
    from wyraj.ui.screens import HelpScreen

    async def run() -> None:
        app = WyrajApp(seed=42)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.press("question_mark")
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("escape")

    asyncio.run(run())


def test_reset_intro_flag(monkeypatch, capsys) -> None:
    import sys

    from wyraj.app import main
    from wyraj.persistence.meta import MetaState, load_meta, save_meta

    meta = MetaState()
    meta.prologue_seen = True
    meta.szept_seen = ["first_move", "farewell"]
    meta.currency.denary = 77  # progress must survive the reset
    save_meta(meta)

    monkeypatch.setattr(sys, "argv", ["wyraj", "--reset-intro"])
    main()
    assert "forgets you" in capsys.readouterr().out

    reset = load_meta()
    assert reset.prologue_seen is False
    assert reset.szept_seen == []
    assert reset.currency.denary == 77
    assert not reset.edited  # a sanctioned reset is not a hand-edit
