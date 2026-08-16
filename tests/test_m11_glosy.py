"""M11 "Głosy": the AudioSystem listens, the game never notices."""

from pathlib import Path

from wyraj.content.audio import AudioCatalog, SoundSpec, load_audio_catalog
from wyraj.core.game import Game
from wyraj.ui.audio import AudioSystem, NullBackend

SEED = 42


class FakeBackend:
    """Records every call — the audio twin of the LLM FakeBackend."""

    def __init__(self) -> None:
        self.played: list[tuple[str, float]] = []
        self.beds: list[tuple[str, float]] = []
        self.stops = 0
        self.shutdowns = 0

    def play(self, path: Path, volume: float) -> None:
        self.played.append((path.name, round(volume, 3)))

    def loop_bed(self, path: Path, volume: float, fade_ms: int) -> None:
        self.beds.append((path.name, round(volume, 3)))

    def stop_bed(self, fade_ms: int) -> None:
        self.stops += 1

    def shutdown(self) -> None:
        self.shutdowns += 1


# ---- US 14.1: skeleton ----------------------------------------------------


def test_empty_catalog_is_total_silence() -> None:
    game = Game(seed=SEED, meta_autosave=False)
    backend = FakeBackend()
    system = AudioSystem(game, AudioCatalog(), backend)
    from wyraj.core.actions import Wait

    game.step(Wait())
    assert backend.played == [] and backend.beds == []
    system.shutdown()
    assert backend.shutdowns == 1


def test_null_backend_is_silent_by_construction() -> None:
    game = Game(seed=SEED, meta_autosave=False)
    AudioSystem(game, AudioCatalog(), NullBackend())  # must not raise
    from wyraj.core.actions import Wait

    game.step(Wait())


def test_audio_config_round_trips(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WYRAJ_HOME", str(tmp_path))
    from wyraj.persistence.config import load_config, save_config

    save_config({"audio": {"enabled": False, "master": 0.5}})
    config = load_config()
    assert config["audio"] == {"enabled": False, "master": 0.5}


def test_app_boots_silent_without_backend(monkeypatch) -> None:
    """Missing extra / refused device — exactly the degraded path."""
    import asyncio

    import wyraj.ui.app as app_module
    from wyraj.ui.app import WyrajApp
    from wyraj.ui.audio import AudioUnavailable

    def refuse() -> None:
        raise AudioUnavailable("no extra in this test")

    monkeypatch.setattr(app_module, "PygameBackend", refuse)

    async def run() -> None:
        app = WyrajApp(seed=SEED)
        async with app.run_test(size=(100, 40)) as pilot:
            assert app.audio is None  # missing extra → silent, noted once
            assert app._audio_note is True
            await pilot.press("full_stop")
            assert app.game.turn == 1

    asyncio.run(run())


def test_app_wires_audio_when_backend_available(monkeypatch) -> None:
    import asyncio

    import wyraj.ui.app as app_module
    from wyraj.ui.app import WyrajApp

    backend = FakeBackend()
    monkeypatch.setattr(app_module, "PygameBackend", lambda: backend)

    async def run() -> None:
        app = WyrajApp(seed=SEED)
        async with app.run_test(size=(100, 40)):
            assert app.audio is not None
            assert backend.beds  # the wieś bed started with the app
        assert backend.shutdowns == 1  # unmount closes the mixer

    asyncio.run(run())


def test_app_mute_flag_skips_audio_entirely() -> None:
    import asyncio

    from wyraj.ui.app import WyrajApp

    async def run() -> None:
        app = WyrajApp(seed=SEED, mute=True)
        async with app.run_test(size=(100, 40)):
            assert app.audio is None
            assert app._audio_note is False  # muted ≠ missing: no note

    asyncio.run(run())


def test_missing_sounds_yml_loads_empty_catalog(tmp_path) -> None:
    assert load_audio_catalog(tmp_path) == AudioCatalog()


# ---- US 14.2: catalog & starter assets ------------------------------------


def test_catalog_files_exist_and_are_credited() -> None:
    from wyraj.content.audio import audio_dir, load_audio_credits

    catalog = load_audio_catalog()
    assert catalog.beds and catalog.events and catalog.voices
    credited = {entry.file for entry in load_audio_credits()}
    root = audio_dir()
    referenced = [
        spec.file
        for group in (catalog.beds, catalog.events, catalog.voices)
        for spec in group.values()
    ]
    for rel in referenced:
        assert (root / rel).exists(), f"missing asset {rel}"
        assert rel in credited, f"uncredited asset {rel}"
    # Every shipped asset file is credited, referenced or not.
    for path in root.rglob("*.wav"):
        assert str(path.relative_to(root)) in credited, f"uncredited file {path.name}"


def test_credits_carry_no_nc_nd_licenses() -> None:
    from wyraj.content.audio import load_audio_credits

    for entry in load_audio_credits():
        assert "NC" not in entry.license and "ND" not in entry.license, entry.file


def test_catalog_event_keys_name_real_events() -> None:
    import re

    from wyraj.core import events as events_module
    from wyraj.core.events import GameEvent

    valid = {
        re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        for name, obj in vars(events_module).items()
        if isinstance(obj, type) and issubclass(obj, GameEvent) and obj is not GameEvent
    }
    for key in load_audio_catalog().events:
        base = key.split("/", 1)[0]
        assert base in valid, f"'{key}' names no known event"


def test_catalog_voices_name_real_monsters() -> None:
    from wyraj.content.bestiary import load_bestiary

    bestiary = load_bestiary()
    for key in load_audio_catalog().voices:
        assert key in bestiary, key


def test_every_bed_key_is_resolvable() -> None:
    catalog = load_audio_catalog()
    for bed in (
        "wies",
        "puszcza",
        "puszcza_noc",
        "bagna",
        "bagna_noc",
        "kurhany",
        "kurhany_deep",
        "dno",
        "kupala",
    ):
        assert bed in catalog.beds, bed


# ---- US 14.3: ambient beds -------------------------------------------------


def test_beds_follow_the_descent() -> None:
    from tests.conftest import goto_depth

    game = Game(seed=SEED, meta_autosave=False)
    backend = FakeBackend()
    AudioSystem(game, load_audio_catalog(), backend)
    assert [name for name, _v in backend.beds] == ["wies.wav"]
    for depth in (1, 2, 3, 4, 6, 8):
        goto_depth(game, depth)
    names = [name for name, _v in backend.beds]
    # 3→4 stays kurhany: one bed at a time, never re-triggered.
    assert names == [
        "wies.wav",
        "puszcza.wav",
        "bagna.wav",
        "kurhany.wav",
        "kurhany_deep.wav",
        "dno.wav",
    ]


def test_night_and_kupala_bed_variants() -> None:
    from wyraj.core import calendar

    game = Game(seed=SEED, meta_autosave=False)
    system = AudioSystem(game, load_audio_catalog(), FakeBackend())
    game.depth = 1
    game.turn = 170  # noc (phase window 160-239)
    assert system._bed_key() in ("puszcza_noc", "kupala")

    kupala_turn = next(
        t
        for t in range(0, calendar.DAY_TURNS * 12, 10)
        if calendar.festival_of(SEED, t) == "kupala" and calendar.phase_of(t) == "noc"
    )
    game.turn = kupala_turn
    assert system._bed_key() == "kupala"
    game.depth = 3
    assert system._bed_key() == "kurhany"  # the flower does not bloom underground


# ---- US 14.4: event SFX ----------------------------------------------------


def test_sfx_follow_rule_keys() -> None:
    from wyraj.core.events import AttackResolved, EntityDied, EntityRef, Outcome, Waited

    game = Game(seed=SEED, meta_autosave=False)
    backend = FakeBackend()
    AudioSystem(game, load_audio_catalog(), backend)
    player = EntityRef(entity=game.player, key="player", name="you", is_player=True)
    bies = EntityRef(entity=999, key="bies", name="bies")
    game.bus.publish(
        AttackResolved(
            attacker=player,
            defender=bies,
            weapon=None,
            damage=5,
            outcome=Outcome.KILL,
            defender_hp_frac=0.0,
        )
    )
    game.bus.publish(Waited(actor=player))  # unmapped: silent by design
    game.bus.publish(EntityDied(entity=player))
    assert [name for name, _v in backend.played] == ["kill.wav", "death.wav"]


def test_stairs_sound_and_bed_change_together() -> None:
    from tests.conftest import goto_depth

    game = Game(seed=SEED, meta_autosave=False)
    backend = FakeBackend()
    AudioSystem(game, load_audio_catalog(), backend)
    goto_depth(game, 1)
    assert ("stairs_down.wav", backend.played[0][1]) in backend.played
    assert backend.beds[-1][0] == "puszcza.wav"


# ---- US 14.5: creature voicing at a distance -------------------------------


def _voicing_setup() -> tuple[Game, FakeBackend, int]:
    from wyraj.core.events import TurnEnded
    from wyraj.ui.audio import VOICE_MODULUS, _audio_hash

    game = Game(seed=SEED, meta_autosave=False)
    backend = FakeBackend()
    AudioSystem(game, load_audio_catalog(), backend)
    game.spawn_monster(game.bestiary["wilk"], 2, 15, depth=0)
    turn = next(t for t in range(1, 1000) if _audio_hash(SEED, t) % VOICE_MODULUS == 0)
    game.bus.publish(TurnEnded(turn))
    return game, backend, turn


def test_distant_unseen_monster_voices_deterministically() -> None:
    _game, first, _turn = _voicing_setup()
    _game2, second, _turn2 = _voicing_setup()
    assert first.played == second.played
    assert first.played and first.played[-1][0] == "wilk.wav"


def test_wrong_turn_or_visible_monster_stays_quiet() -> None:
    from wyraj.core.components import Position
    from wyraj.core.events import TurnEnded
    from wyraj.ui.audio import VOICE_MODULUS, _audio_hash

    game = Game(seed=SEED, meta_autosave=False)
    backend = FakeBackend()
    AudioSystem(game, load_audio_catalog(), backend)
    wilk = game.spawn_monster(game.bestiary["wilk"], 2, 15, depth=0)
    off_turn = next(t for t in range(1, 1000) if _audio_hash(SEED, t) % VOICE_MODULUS != 0)
    game.bus.publish(TurnEnded(off_turn))
    assert backend.played == []

    # Step into view: a seen wolf is the map's business, not the ear's.
    ppos = game.world.expect(game.player, Position)
    game.world.add(wilk, Position(ppos.x + 2, ppos.y))
    game._update_player_fov()
    on_turn = next(t for t in range(1, 1000) if _audio_hash(SEED, t) % VOICE_MODULUS == 0)
    game.bus.publish(TurnEnded(on_turn))
    assert backend.played == []


def test_voicing_draws_nothing_from_game_rng() -> None:
    game, _backend, _turn = _voicing_setup()
    before = game.rng.get_states()
    from wyraj.core.events import TurnEnded
    from wyraj.ui.audio import VOICE_MODULUS, _audio_hash

    turn = next(t for t in range(1, 2000) if _audio_hash(SEED, t) % VOICE_MODULUS == 0)
    game.bus.publish(TurnEnded(turn))
    assert game.rng.get_states() == before


def test_event_sound_fallback_chain() -> None:
    catalog = AudioCatalog(
        events={
            "attack_resolved/player_kill": SoundSpec(file="kill.wav"),
            "level_changed": SoundSpec(file="stairs.wav"),
        }
    )
    assert catalog.event_sound("attack_resolved", "player_kill").file == "kill.wav"
    assert catalog.event_sound("attack_resolved", "player_hit") is None
    assert catalog.event_sound("level_changed", "down").file == "stairs.wav"
