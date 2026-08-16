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


def test_app_boots_silent_without_backend() -> None:
    """The dev environment has no pygame-ce — exactly the degraded path."""
    import asyncio

    from wyraj.ui.app import WyrajApp

    async def run() -> None:
        app = WyrajApp(seed=SEED)
        async with app.run_test(size=(100, 40)) as pilot:
            assert app.audio is None  # missing extra → silent, noted once
            await pilot.press("full_stop")
            assert app.game.turn == 1

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
