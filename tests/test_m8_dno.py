"""M8 "Dno" core: depth tiers, the Wij, the gaze, the rite, Głębiej."""

from dataclasses import replace

from wyraj.core.actions import Get, Move, Wait
from wyraj.core.components import (
    Health,
    Inventory,
    Item,
    LightSource,
    Lore,
    Position,
    Rite,
    Villager,
)
from wyraj.core.events import (
    DeepDescended,
    RiteCompleted,
    RiteInterrupted,
    RiteStarted,
    SeenByWij,
    WijAttackFutile,
    WijGazeOpened,
    WijLidLifted,
    WijStirred,
)
from wyraj.core.game import (
    LAST_SKY_DEPTH,
    MAX_DEPTH,
    RITE_TURNS,
    WIJ_GAZE_AT,
    WIJ_KNOCKBACK,
    Game,
)
from wyraj.core.map import Tile
from wyraj.core.systems import death


def descend_to(game: Game, depth: int) -> None:
    for d in range(game.depth + 1, depth + 1):
        game._change_level(d, "down")


def give_item(game: Game, key: str) -> int:
    ppos = game.world.expect(game.player, Position)
    entity = game.spawn_item(game.items_catalog[key], ppos.x, ppos.y, depth=game.depth)
    game.step(Get())
    return entity


def clear_slugi(game: Game) -> None:
    for sluga in game._alive_slugi():
        game.world.destroy(sluga)
    game._wij_respawn = 10_000  # the niches hold their breath for these tests


# ---- US 11.1: depth tiers --------------------------------------------------


def test_world_reaches_depth_eight_and_sky_ends_at_six() -> None:
    game = Game(seed=42)
    descend_to(game, MAX_DEPTH)
    assert game.depth == MAX_DEPTH
    assert game.vault is not None
    for depth in range(3, MAX_DEPTH + 1):
        tiles = {tile for row in game.levels[depth].tiles for tile in row}
        if depth > LAST_SKY_DEPTH:
            assert Tile.SHAFT not in tiles, f"depth {depth} must have no open sky"
    # At least one crypt at or above LAST_SKY_DEPTH keeps a shaft (seeded, stable)
    shallow = {tile for row in game.levels[3].tiles for tile in row}
    assert Tile.SHAFT in shallow


def test_darkness_escalates_and_gromnica_restores_sight() -> None:
    game = Game(seed=42)
    expectations = {5: 4, 6: 3, 7: 2, 8: 1}
    descend_to(game, MAX_DEPTH)
    for depth, radius in expectations.items():
        game.depth = depth
        assert game.fov_radius == radius, f"depth {depth}"
    game.world.add(game.player, LightSource(turns=50))
    assert game.fov_radius == 8
    game.world.remove(game.player, LightSource)


def test_deep_descended_fires_once_at_seven() -> None:
    game = Game(seed=42)
    events: list[DeepDescended] = []
    game.bus.subscribe(DeepDescended, events.append)
    descend_to(game, MAX_DEPTH)
    assert [e.depth for e in events] == [LAST_SKY_DEPTH + 1]
    game._change_level(6, "up")
    game._change_level(7, "down")
    assert len(events) == 1  # the marker is once per run


# ---- US 11.2-11.3: the Wij -------------------------------------------------


def test_slugi_lift_and_their_deaths_knock_back() -> None:
    game = Game(seed=42)
    descend_to(game, MAX_DEPTH)
    assert game.vault is not None
    cx, cy = game.vault.cradle
    slugi = game._alive_slugi()
    assert len(slugi) == 2  # the vault wakes with two pallbearers
    for i, sluga in enumerate(slugi):
        game.world.add(sluga, Position(cx - 1, cy - 1 + i))
    game.step(Wait())
    assert game.wij_lift == 4  # two channeling servants
    lift_before = game.wij_lift
    death.kill(game.world, game.bus, slugi[0])
    assert game.wij_lift == max(0, lift_before - WIJ_KNOCKBACK)


def test_phases_fire_in_order_and_brighten_the_hall() -> None:
    game = Game(seed=42)
    descend_to(game, MAX_DEPTH)
    clear_slugi(game)
    fired: list[str] = []
    game.bus.subscribe(WijStirred, lambda e: fired.append("stirred"))
    game.bus.subscribe(WijLidLifted, lambda e: fired.append("lid"))
    game.bus.subscribe(WijGazeOpened, lambda e: fired.append("gaze"))
    game.wij_lift = 30
    game.step(Wait())
    assert game.wij_phase == "stirring"
    game.wij_lift = 70
    game.step(Wait())
    assert game.wij_phase == "lid"
    assert game.fov_radius == 2  # his light, and it is wrong
    game.wij_lift = WIJ_GAZE_AT
    game.step(Wait())
    assert game.wij_phase == "gaze"
    assert fired == ["stirred", "lid", "gaze"]


def test_gaze_light_inversion() -> None:
    game = Game(seed=42)
    descend_to(game, MAX_DEPTH)
    clear_slugi(game)
    assert game.vault is not None
    cx, cy = game.vault.cradle
    game.world.add(game.player, Position(cx - 4, cy))  # open floor, in his line
    game.wij_lift = WIJ_GAZE_AT
    game.wij_phase = "gaze"
    seen: list[SeenByWij] = []
    game.bus.subscribe(SeenByWij, seen.append)
    hp_dark = game.world.expect(game.player, Health).hp
    game.step(Wait())  # unlit: the dark keeps you
    assert not seen
    assert game.world.expect(game.player, Health).hp == hp_dark
    game.world.add(game.player, LightSource(turns=50))
    game.step(Wait())  # lit: the flame marks you
    assert seen
    assert game.world.expect(game.player, Health).hp < hp_dark


def test_wij_cannot_be_fought() -> None:
    game = Game(seed=42)
    descend_to(game, MAX_DEPTH)
    clear_slugi(game)
    assert game.vault is not None
    cx, cy = game.vault.cradle
    wij = next(e for e, (lore, _p) in game.world.query(Lore, Position) if lore.key == "wij")
    assert game.world.get(wij, Health) is None  # no HP bar, by design
    futile: list[WijAttackFutile] = []
    game.bus.subscribe(WijAttackFutile, futile.append)
    game.world.add(game.player, Position(cx - 1, cy))
    game.step(Move(1, 0))  # bump the cradle bare-handed
    assert futile
    assert game.world.expect(game.player, Position) == Position(cx - 1, cy)


# ---- US 11.4: the rite and victory ----------------------------------------


def prepare_rite(game: Game) -> None:
    descend_to(game, MAX_DEPTH)
    clear_slugi(game)
    assert game.vault is not None
    cx, cy = game.vault.cradle
    game.world.add(game.player, Position(cx - 2, cy))
    give_item(game, "sol_swiecona")
    game.world.add(game.player, Position(cx - 1, cy))


def test_rite_wins_the_run() -> None:
    game = Game(seed=42, meta_autosave=False)
    started: list[RiteStarted] = []
    completed: list[RiteCompleted] = []
    game.bus.subscribe(RiteStarted, started.append)
    game.bus.subscribe(RiteCompleted, completed.append)
    prepare_rite(game)
    game.step(Move(1, 0))  # hands on the lids; the salt is spent
    assert started and game.world.get(game.player, Rite) is not None
    inventory = game.world.expect(game.player, Inventory)
    assert not any(
        (item := game.world.get(e, Item)) is not None and item.key == "sol_swiecona"
        for e in inventory.items
    )
    for _ in range(RITE_TURNS):
        game.step(Wait())
    assert completed
    assert game.victory and game.game_over
    assert game.wij_phase == "sealed"
    assert game.victory_epilogue in ("swit", "gospodarz", "ptaki")
    assert not game._alive_slugi()  # they folded where they stood


def test_rite_breaks_on_moving_and_salt_is_lost() -> None:
    game = Game(seed=42, meta_autosave=False)
    interrupted: list[RiteInterrupted] = []
    game.bus.subscribe(RiteInterrupted, interrupted.append)
    prepare_rite(game)
    game.step(Move(1, 0))
    game.step(Move(0, 1))  # you stepped back
    assert interrupted and interrupted[0].reason == "moved"
    assert game.world.get(game.player, Rite) is None
    assert not game.victory


def test_bare_hands_cannot_start_the_rite() -> None:
    game = Game(seed=42)
    descend_to(game, MAX_DEPTH)
    clear_slugi(game)
    assert game.vault is not None
    cx, cy = game.vault.cradle
    game.world.add(game.player, Position(cx - 1, cy))
    game.step(Move(1, 0))
    assert game.world.get(game.player, Rite) is None


def test_victory_writes_meta_once() -> None:
    game = Game(seed=42, meta_autosave=False)
    prepare_rite(game)
    game.step(Move(1, 0))
    for _ in range(RITE_TURNS):
        game.step(Wait())
    assert game.victory
    game.apply_victory_to_meta()
    assert len(game.meta.victories) == 1
    record = game.meta.victories[0]
    assert record.origin == "wygnaniec" and record.seed == 42
    assert record.epilogue == game.victory_epilogue
    assert game.meta.achievements["victories"] == 1


def test_epilogue_selection_branches() -> None:
    game = Game(seed=42, meta_autosave=False)
    assert game._epilogue_key() == "swit"
    for key in game.bestiary:
        game.meta.codex.known[key] = "partial"
    assert game._epilogue_key() == "ptaki"
    game.dziad_met_this_run = True
    game.meta.dziad.reputation = 3
    assert game._epilogue_key() == "gospodarz"  # the dziad outranks the birds


# ---- Głębiej and persistence ----------------------------------------------


def test_glebiej_darkens_and_gouges() -> None:
    plain = Game(seed=42, meta_autosave=False)
    deeper = Game(seed=42, meta_autosave=False, glebiej=True)
    assert deeper.fov_radius == plain.fov_radius - 1
    trader_plain = next(
        e for e, (v, _p) in plain.world.query(Villager, Position) if v.role == "trader"
    )
    trader_deep = next(
        e for e, (v, _p) in deeper.world.query(Villager, Position) if v.role == "trader"
    )
    assert deeper.price_for("odwar", trader_deep) > plain.price_for("odwar", trader_plain)


def test_save_roundtrip_keeps_dno_state(tmp_path) -> None:
    from wyraj.persistence.save import load_game, save_game

    game = Game(seed=42, meta_autosave=False, glebiej=True)
    descend_to(game, MAX_DEPTH)
    game.wij_lift = 42
    game.wij_phase = "stirring"
    path = tmp_path / "save.json.gz"
    save_game(game, path)
    loaded = load_game(path)
    assert loaded is not None
    assert loaded.glebiej is True
    assert loaded.wij_lift == 42 and loaded.wij_phase == "stirring"
    assert loaded.vault is not None
    assert loaded.vault.cradle == game.vault.cradle  # type: ignore[union-attr]


def test_dying_hp_band_still_earns_blizna_at_depth() -> None:
    game = Game(seed=42, meta_autosave=False)
    descend_to(game, MAX_DEPTH)
    clear_slugi(game)
    health = game.world.expect(game.player, Health)
    game.world.add(game.player, replace(health, hp=1))
    game.step(Wait())
    game.world.add(game.player, replace(health, hp=health.max_hp))
    game.step(Wait())
    assert game.blizny == 1


# ---- US 11.5-11.6: epilogues, title, victory outcome ------------------------


def test_epilogues_exist_in_both_languages_with_parity() -> None:
    from wyraj.content.intro import load_epilogues

    en = load_epilogues("en").endings
    pl = load_epilogues("pl").endings
    assert set(en) == set(pl) == {"swit", "gospodarz", "ptaki"}
    for lang in (en, pl):
        for key, pages in lang.items():
            assert len(pages) >= 3, f"{key} needs at least three pages"
            assert all(page.strip() for page in pages)


def test_victory_outcome_reaches_the_app_boundary() -> None:
    import asyncio

    from wyraj.ui.app import WyrajApp

    async def run() -> None:
        app = WyrajApp(seed=42)
        async with app.run_test(size=(120, 40)) as pilot:
            game = app.game
            prepare_rite(game)
            await pilot.press("l")  # step east onto the cradle: hands on the lids
            for _ in range(RITE_TURNS):
                await pilot.press("full_stop")
            await pilot.pause()
        assert app.return_value is not None
        assert app.return_value.startswith("victory:")
        assert app.game.victory
        assert len(app.game.meta.victories) == 1

    asyncio.run(run())


def test_title_remembers_a_victory() -> None:
    from wyraj.persistence.meta import MetaState, VictoryRecord
    from wyraj.ui.title import TitleApp

    meta = MetaState()
    plain = TitleApp(meta, has_save=False, rng_seed=1)
    assert "glebiej" not in [key for key, _ in plain._menu_entries()]
    meta.victories.append(VictoryRecord(origin="wygnaniec", seed=42, turn=800, epilogue="swit"))
    proud = TitleApp(meta, has_save=False, rng_seed=1)
    assert "glebiej" in [key for key, _ in proud._menu_entries()]
    assert "The birds returned, once." in proud._render_body().plain
