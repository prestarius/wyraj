"""M9 "Koło Roku" core: the pure clock, weather mechanics, festivals."""

import pytest

from wyraj.core import calendar
from wyraj.core.actions import Move, Rest, Wait
from wyraj.core.components import (
    Health,
    Hunger,
    LightSource,
    Peaceful,
    Position,
    StatusEffects,
)
from wyraj.core.events import (
    FestivalDawned,
    KupalaBloom,
    PhaseChanged,
    TalkedToDead,
    WeatherChanged,
)
from wyraj.core.game import Game

# ---- US 12.1: the clock is pure -------------------------------------------


def test_phases_partition_the_day() -> None:
    assert calendar.phase_of(0) == "swit"
    assert calendar.phase_of(19) == "swit"
    assert calendar.phase_of(20) == "dzien"
    assert calendar.phase_of(139) == "dzien"
    assert calendar.phase_of(140) == "zmierzch"
    assert calendar.phase_of(160) == "noc"
    assert calendar.phase_of(239) == "noc"
    assert calendar.phase_of(240) == "swit"  # the wheel keeps turning


def test_calendar_is_seed_identity() -> None:
    assert calendar.start_day(42) == calendar.start_day(42)
    days = {calendar.start_day(seed) for seed in range(200)}
    assert days == set(range(calendar.WHEEL_DAYS))  # every start day occurs
    assert calendar.weather_of(42, 100) == calendar.weather_of(42, 100)
    kinds = {calendar.weather_of(7, day * calendar.DAY_TURNS) for day in range(60)}
    assert kinds == set(calendar.WEATHERS)  # all four weathers happen


def test_boundary_events_fire() -> None:
    game = Game(seed=42, meta_autosave=False)
    phases: list[PhaseChanged] = []
    weathers: list[WeatherChanged] = []
    festivals: list[FestivalDawned] = []
    game.bus.subscribe(PhaseChanged, phases.append)
    game.bus.subscribe(WeatherChanged, weathers.append)
    game.bus.subscribe(FestivalDawned, festivals.append)
    for _ in range(calendar.DAY_TURNS + 1):
        game.step(Wait())
    assert [p.phase for p in phases] == ["dzien", "zmierzch", "noc", "swit"]
    assert len(weathers) == 1  # one dawn crossed
    assert weathers[0].kind == calendar.weather_of(42, calendar.DAY_TURNS)
    next_festival = calendar.festival_of(42, calendar.DAY_TURNS)
    assert [f.festival for f in festivals] == ([next_festival] if next_festival else [])


# ---- US 12.2: night and weather mechanics ----------------------------------


def test_surface_fov_follows_the_sky(monkeypatch: pytest.MonkeyPatch) -> None:
    game = Game(seed=42, meta_autosave=False)
    game._change_level(1, "down")
    game.turn = 60  # dzien
    assert game.fov_radius == 8
    game.turn = 150  # zmierzch
    assert game.fov_radius == 6
    game.turn = 200  # noc
    assert game.fov_radius == 5
    monkeypatch.setattr(calendar, "weather_of", lambda seed, turn: "mgla")
    game.turn = 60
    assert game.fov_radius == 6  # mist shortens the day
    game.turn = 200
    assert game.fov_radius == 3  # night + mist bottoms at the floor
    game.world.add(game.player, LightSource(turns=50))
    assert game.fov_radius == 6  # a carried flame pushes back some


def test_rain_drains_unprotected_flame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calendar, "weather_of", lambda seed, turn: "deszcz")
    monkeypatch.setattr(calendar, "festival_of", lambda seed, turn: None)
    game = Game(seed=42, meta_autosave=False)
    game.world.add(game.player, LightSource(turns=10))
    game.step(Wait())
    light = game.world.expect(game.player, LightSource)
    assert light.turns == 8  # the usual tick plus the rain's bite


def test_gromniczna_blesses_the_flame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calendar, "festival_of", lambda seed, turn: "gromniczna")
    monkeypatch.setattr(calendar, "weather_of", lambda seed, turn: "jasno")
    game = Game(seed=42, meta_autosave=False)
    game.world.add(game.player, LightSource(turns=10))
    for _ in range(4):
        game.step(Wait())
    light = game.world.expect(game.player, LightSource)
    assert light.turns == 8  # half rate: four turns cost two


def test_storm_doubles_peruns_favor(monkeypatch: pytest.MonkeyPatch) -> None:
    game = Game(seed=42, meta_autosave=False)
    spec = game.offerings["perun"]
    game.meta.currency.denary = spec.cost * 10
    monkeypatch.setattr(calendar, "weather_of", lambda seed, turn: "burza")
    game._make_offering("perun")
    statuses = game.world.expect(game.player, StatusEffects)
    favor = next(e for e in statuses.effects if e.kind == spec.kind)
    assert favor.duration == spec.duration * 2


# ---- US 12.3: sky-aware spawns ---------------------------------------------


def test_poludnica_keeps_her_hours() -> None:
    game = Game(seed=42, meta_autosave=False)
    poludnica = game.bestiary["poludnica"]
    game.turn = 60  # dzien
    assert game._spawn_weight(poludnica, "puszcza") == 3
    game.turn = 200  # noc
    assert game._spawn_weight(poludnica, "puszcza") == 0
    strzyga = game.bestiary["strzyga"]
    assert game._spawn_weight(strzyga, "puszcza") == strzyga.spawn_weight * 3
    game.turn = 60
    assert game._spawn_weight(strzyga, "puszcza") == strzyga.spawn_weight


def test_population_depends_deterministically_on_visit_time() -> None:
    def keys_at(turn: int) -> list[str]:
        game = Game(seed=99, meta_autosave=False)
        game.turn = turn
        game._change_level(1, "down")
        from wyraj.core.components import AI, Lore

        return sorted(lore.key for _e, (_ai, lore) in game.world.query(AI, Lore))

    assert keys_at(60) == keys_at(60)  # same visit time = same forest
    night = keys_at(200)
    assert "poludnica" not in night


# ---- US 12.4: festivals -----------------------------------------------------


def test_dziady_the_dead_talk_and_the_codex_learns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(calendar, "festival_of", lambda seed, turn: "dziady")
    game = Game(seed=42, meta_autosave=False)
    talked: list[TalkedToDead] = []
    game.bus.subscribe(TalkedToDead, talked.append)
    ppos = game.world.expect(game.player, Position)
    martwiak = game.spawn_monster(game.bestiary["martwiak"], ppos.x + 1, ppos.y, 0)
    assert game.world.get(martwiak, Peaceful) is not None  # born into the truce
    game.step(Move(1, 0))
    assert talked and game.world.is_alive(martwiak)
    assert game.meta.codex.known.get("martwiak") == "partial"
    game.step(Move(1, 0))
    assert game.meta.codex.known.get("martwiak") == "full"  # conversation completes it
    game._apply_dziady(False)  # the day ends; the truce lifts
    assert game.world.get(martwiak, Peaceful) is None


def test_kupala_blooms_once_and_survives_the_save(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(calendar, "festival_of", lambda seed, turn: "kupala")
    game = Game(seed=42, meta_autosave=False)
    game._change_level(1, "down")
    blooms: list[KupalaBloom] = []
    game.bus.subscribe(KupalaBloom, blooms.append)
    game.turn = 159  # the edge of zmierzch
    game.step(Wait())  # noc falls on Kupała
    assert len(blooms) == 1
    assert game.kupala_bloomed
    from wyraj.core.components import Item

    assert any(item.key == "kwiat_paproci" for _e, (item,) in game.world.query(Item))
    game.turn = 159 + calendar.DAY_TURNS
    game.step(Wait())
    assert len(blooms) == 1  # once a run, and the run remembers

    from wyraj.persistence.save import load_game, save_game

    path = tmp_path / "save.json.gz"
    save_game(game, path)
    loaded = load_game(path)
    assert loaded is not None and loaded.kupala_bloomed


def test_dozynki_rest_is_free(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calendar, "festival_of", lambda seed, turn: "dozynki")
    game = Game(seed=42, meta_autosave=False)
    game.world.add(game.player, Health(5, 24))
    before = game.world.expect(game.player, Hunger).satiation
    game.step(Rest())
    hunger = game.world.expect(game.player, Hunger)
    assert game.world.expect(game.player, Health).hp == 24
    assert hunger.satiation >= before - 2  # only the turn's own hunger tick
