"""AudioSystem (M11 "Głosy"): one more listener on the bus.

Audio is a listener, never a participant: it subscribes like the narration
engine, publishes nothing, saves nothing, and draws nothing from the four
save-versioned game RNG streams — anything chance-flavored uses local
sha256(seed, "audio", turn) hashes (the calendar pattern), so the golden
transcript cannot move. The game runs identically silent; audio is never
the sole carrier of any information.
"""

import contextlib
import hashlib
import os
from pathlib import Path
from typing import Any, Protocol

from wyraj.content.audio import AudioCatalog, audio_dir
from wyraj.core.components import AI, Lore, Position
from wyraj.core.events import FestivalDawned, GameEvent, LevelChanged, PhaseChanged, TurnEnded
from wyraj.core.game import LAST_SKY_DEPTH, MAX_DEPTH, Game
from wyraj.core.systems.movement import level_of
from wyraj.narration.templates import rule_key

# M11 tuning table (spec §4-5)
BED_FADE_MS = 1200
SFX_CHANNELS = 6  # concurrent one-shots; the bed holds its own reserved channel
VOICE_MODULUS = 17  # a distant voice roughly every 17 turns, when anyone is out there
VOICE_RADIUS = 12  # Chebyshev tiles
VOICE_VOLUME_SCALE = 0.6  # distance keeps its manners


class AudioUnavailable(Exception):
    """The sound extra is missing or the audio device refused — run silent."""


class AudioBackend(Protocol):
    def play(self, path: Path, volume: float) -> None: ...

    def loop_bed(self, path: Path, volume: float, fade_ms: int) -> None: ...

    def stop_bed(self, fade_ms: int) -> None: ...

    def shutdown(self) -> None: ...


class NullBackend:
    """Silence, implemented."""

    def play(self, path: Path, volume: float) -> None:
        pass

    def loop_bed(self, path: Path, volume: float, fade_ms: int) -> None:
        pass

    def stop_bed(self, fade_ms: int) -> None:
        pass

    def shutdown(self) -> None:
        pass


class PygameBackend:
    """SDL mixing via pygame-ce. Audio-subsystem only — never pygame.init(),
    never a window. Mixing happens on SDL's own thread; play() returns
    immediately, so Textual's asyncio loop is untouched (spec §1)."""

    def __init__(self) -> None:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        try:
            import pygame
        except ImportError as exc:
            raise AudioUnavailable("pygame-ce is not installed") from exc
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(SFX_CHANNELS + 1)
            pygame.mixer.set_reserved(1)  # channel 0 belongs to the bed
        except Exception as exc:  # pygame.error: no device, no driver…
            raise AudioUnavailable(str(exc)) from exc
        self._pygame = pygame
        self._bed = pygame.mixer.Channel(0)
        self._cache: dict[Path, Any] = {}

    def _sound(self, path: Path) -> Any:
        sound = self._cache.get(path)
        if sound is None:
            sound = self._pygame.mixer.Sound(str(path))
            self._cache[path] = sound
        return sound

    def play(self, path: Path, volume: float) -> None:
        try:
            sound = self._sound(path)
            sound.set_volume(volume)
            channel = self._pygame.mixer.find_channel()
            if channel is not None:  # pool exhausted = drop the sound, sparse anyway
                channel.play(sound)
        except Exception:
            pass  # a broken asset must never take a turn down with it

    def loop_bed(self, path: Path, volume: float, fade_ms: int) -> None:
        try:
            sound = self._sound(path)
            sound.set_volume(volume)
            self._bed.play(sound, loops=-1, fade_ms=fade_ms)
        except Exception:
            pass

    def stop_bed(self, fade_ms: int) -> None:
        self._bed.fadeout(fade_ms)

    def shutdown(self) -> None:
        with contextlib.suppress(Exception):
            self._pygame.mixer.quit()


def _audio_hash(seed: int, *parts: object) -> int:
    payload = ":".join(str(p) for p in (seed, "audio", *parts))
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


class AudioSystem:
    """Beds follow (biome, depth, phase, festival); SFX follow rule keys;
    distant voices follow a deterministic schedule. One bed at a time."""

    def __init__(
        self,
        game: Game,
        catalog: AudioCatalog,
        backend: AudioBackend,
        master: float = 0.8,
        ambient: float = 0.7,
        sfx: float = 0.8,
        root: Path | None = None,
    ) -> None:
        self.game = game
        self.catalog = catalog
        self.backend = backend
        self.master = max(0.0, min(1.0, master))
        self.ambient = max(0.0, min(1.0, ambient))
        self.sfx = max(0.0, min(1.0, sfx))
        self._dir = audio_dir(root)
        self._current_bed: str | None = None
        game.bus.subscribe_all(self._on_event)
        # Game.__init__ publishes no LevelChanged — kick the first bed by hand.
        self._refresh_bed()

    # ---- dispatch ----------------------------------------------------------

    def _path(self, file: str) -> Path:
        path = Path(file)
        return path if path.is_absolute() else self._dir / path

    def _on_event(self, event: GameEvent) -> None:
        if isinstance(event, TurnEnded):
            self._voice_distance(event.turn)
            return
        if isinstance(event, LevelChanged | PhaseChanged | FestivalDawned):
            self._refresh_bed()
        key, subkey = rule_key(event)
        spec = self.catalog.event_sound(key, subkey)
        if spec is not None:
            self.backend.play(self._path(spec.file), self._level(spec.volume, self.sfx))

    def _level(self, base: float, category: float) -> float:
        return max(0.0, min(1.0, base * category * self.master))

    # ---- ambient beds (spec §4) -------------------------------------------

    def _bed_key(self) -> str | None:
        game = self.game
        depth, phase = game.depth, game.phase
        if game.festival == "kupala" and phase == "noc" and 1 <= depth <= 2:
            return "kupala"
        if depth == 0:
            return "wies"
        if depth == 1:
            return "puszcza_noc" if phase == "noc" else "puszcza"
        if depth == 2:
            return "bagna_noc" if phase == "noc" else "bagna"
        if depth == MAX_DEPTH:
            return "dno"
        if depth >= LAST_SKY_DEPTH:  # 6-7: the deep tiers (M8), nearer silence
            return "kurhany_deep"
        return "kurhany"

    def _refresh_bed(self) -> None:
        key = self._bed_key()
        if key is not None and key not in self.catalog.beds:
            base = key.removesuffix("_noc")
            key = base if base in self.catalog.beds else None
        if key == self._current_bed:
            return
        self._current_bed = key
        if key is None:
            self.backend.stop_bed(BED_FADE_MS)
            return
        spec = self.catalog.beds[key]
        self.backend.loop_bed(
            self._path(spec.file), self._level(spec.volume, self.ambient), BED_FADE_MS
        )

    # ---- creature voicing at a distance (spec §5) -------------------------

    def _voice_distance(self, turn: int) -> None:
        if not self.catalog.voices:
            return
        if _audio_hash(self.game.seed, turn) % VOICE_MODULUS != 0:
            return
        game = self.game
        player_pos = game.world.get(game.player, Position)
        if player_pos is None:
            return
        candidates: list[tuple[int, str]] = []
        for entity, (_ai, lore, pos) in game.world.query(AI, Lore, Position):
            if level_of(game.world, entity) != game.depth:
                continue
            if lore.key not in self.catalog.voices:
                continue
            distance = max(abs(pos.x - player_pos.x), abs(pos.y - player_pos.y))
            if distance > VOICE_RADIUS:
                continue
            if (pos.x, pos.y) in game.map.visible:
                continue  # you hear what you cannot see — that is the point
            candidates.append((entity, lore.key))
        if not candidates:
            return
        candidates.sort()  # entity ids: deterministic order
        _entity, key = candidates[_audio_hash(game.seed, "pick", turn) % len(candidates)]
        spec = self.catalog.voices[key]
        self.backend.play(
            self._path(spec.file), self._level(spec.volume * VOICE_VOLUME_SCALE, self.sfx)
        )

    def shutdown(self) -> None:
        self.backend.shutdown()
