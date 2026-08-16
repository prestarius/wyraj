# WYRAJ — M11 "GŁOSY" — Sound Specification

> **Status:** Draft v0.1 — **Milestone 11**, addendum to `WYRAJ_PROJECT.md`; expands the M11 outline in `WYRAJ_ROADMAP_M8PLUS.md`
> **Prerequisites:** M0 event bus (everything else is flavor it reacts to: M9 calendar for night beds and festival variants, M8 for the Wij's chamber)
> **Principle:** audio is a *listener*, never a participant. An `AudioSystem` subscribes to the bus exactly like the narration engine; core emits nothing new, saves nothing new, draws nothing new. The game runs identically silent — audio is never the sole carrier of any information, because the narration already says everything. Sparse is the aesthetic: one sound per minute lands harder than a soundtrack. **No music in v1** (a single title-screen drone is the permitted exception, deferred).

---

## 1. Backend — verified 2026-08-16 (roadmap's mandated re-check)

**`pygame-ce >= 2.5.8`** as the single optional extra: `[project.optional-dependencies] sound = ["pygame-ce>=2.5.8"]`, installed via `uv sync --extra sound`.

- The maintained fork (upstream pygame dormant since 2024-09; pygame-ce released 2026-08-09 by the former core team, drop-in `import pygame`). Wheels cp310–cp315: macOS universal2, manylinux x86_64+aarch64, win amd64+arm64.
- `pygame.mixer.init()` initializes SDL audio only — truly headless, no window, no display server. `PYGAME_HIDE_SUPPORT_PROMPT=1` set before import; **never** `pygame.init()`.
- Everything needed with zero engine code: OGG/WAV loading, `loops=-1` ambient beds, per-Sound/per-Channel volume, N-channel mixing on SDL's own audio thread (`play()` returns immediately — no interaction with Textual's asyncio loop).
- License: LGPL-2.1 over zlib SDL — compatible with AGPL-3.0 code; as an optional pip dep we don't even redistribute it.
- **No fallback backend.** miniaudio (the paper runner-up: MIT, active) has no mixer — a fallback would mean owning a hand-rolled PCM mixing engine. Missing/broken backend ⇒ the game runs silent with a single dim launch note, nothing else changes. miniaudio is the *migration* target if pygame-ce ever sours, not a parallel path.

## 2. Architecture — one more listener on the bus

New module **`ui/audio.py`** (presentation layer; no new top-level package, and the headless paths — golden, sims — never construct it):

- `AudioSystem(game, catalog, backend, config)` does `bus.subscribe_all(...)` like `NarrationEngine`, plus an initial ambient kick at construction (`Game.__init__` publishes no `LevelChanged`).
- **Backend Protocol** (`play(key, volume)`, `loop_bed(key, volume)`, `stop_bed(fade_ms)`, `set_volumes(...)`) with two implementations: `PygameBackend` (guarded `try: import pygame` — the codebase's first import-optional dep) and a `NullBackend`. Tests inject a recording fake, the `FakeBackend` pattern from the LLM narrator; the real backend stays out of CI.
- **Determinism untouched:** audio never draws from the four save-versioned RNG streams (M9 rule: no new streams) and publishes no events — the golden transcript cannot move. Anything chance-flavored (voicing, §5) uses local `sha256(seed, "audio", turn)` hashes, the `calendar.py` pattern.
- Wiring mirrors the szept: `WyrajApp` builds it with an `enabled` flag; `--mute` and config decide; failure to init degrades to `NullBackend` with the dim note.

## 3. Sound catalog — data-driven, keyed like narration

`data/audio/` (covered by the existing `data/LICENSE` CC-BY-SA umbrella; no loader globs outside its own subdir, so assets are invisible to everything else):

- **`sounds.yml`** — pydantic-validated in `content/audio.py`; explicit filenames, never a glob (CREDITS.yml lives beside it):
  - `beds:` name → `{file, volume}` — the ambient layer (§4).
  - `events:` narration-rule key (`attack_resolved/player_kill`, `light_extinguished`, `level_changed/down`…) → `{file, volume}` — **the same `rule_key()` the narration uses**, so audio content is authored in the vocabulary the packs already speak. Unmapped events are silent by design.
  - `voices:` monster key → `{file, volume}` for distance voicing (§5).
- **`CREDITS.yml`** — per-asset manifest: `{file, source_url, author, license}`; CC0/CC-BY only, no NC/ND (verified per asset before inclusion); CI asserts every file in `sounds.yml` exists and every asset file has a credits entry.
- **v1 starter assets are synthesized, not sourced** (open decision #38): a checked-in stdlib-only generator `tools/gen_sounds.py` (deterministic: `wave` + math — filtered noise wind, marsh drips, stone settling, heartbeat, thumps, clicks) produces the starter set, committed as small mono OGG/WAV files, credited to the project itself. The system ships audible end-to-end; curation from freesound.org replaces files one by one later without code changes — that ongoing curation is content work, not milestone scope.

## 4. Ambient beds — silence as a designed layer

Selector reads `(game.map.biome, game.depth, game.phase, game.festival)` on `LevelChanged`, `PhaseChanged`, `FestivalDawned`, plus the initial kick; swaps with a short fade (`fade_ms` knob, default 1200):

| bed | when |
|---|---|
| `wies` | depth 0 — hearth-and-hens |
| `puszcza` / `puszcza_noc` | depth 1, noc variant at night (M9 phase) |
| `bagna` / `bagna_noc` | depth 2 — drips and bubbles |
| `kurhany` | depths 3–5 — near-silence, stone settling |
| `kurhany_deep` | depths 6–7 — nearer silence; the dark has a texture |
| `dno` | depth 8 — a heartbeat. His. |
| `kupala` (override) | Noc Kupały at night on the surface — distant singing |

Storm/rain ride the *event* layer (`weather_changed/burza` one-shot, `lightning_struck`), not extra beds — one bed at a time, always.

## 5. Event SFX & creature voicing — sparse by design

- **v1 SFX set** (~14 mappings, all existing events): player hit / enemy hit / kill (`attack_resolved/*`), player death sting (`entity_died/player`), `item_picked_up`, `quickslot_used`, gromnica lit (`item_used/light`) and dying (`light_extinguished`), stairs (`level_changed/down|up`), the crane wedge arriving (`crane_summon_completed` — **the one "big" sound in the game**), `wij_stirred` / `wij_lid_lifted` / `wij_gaze_opened`, `rite_completed`. Nothing on keypresses, ever. Typewriter murmur and title drone: deferred with the music guardrail.
- **Creature voicing at a distance** — audio as roguelike information (you *hear* the pack before you see it): every turn, `sha256(seed, "audio", turn) % VOICE_MODULUS == 0` (default 17) picks the trigger; the voicer queries `world.query(AI, Lore, Position)` on the current level, keeps monsters within `VOICE_RADIUS` (default 12, Chebyshev) whose tile is **not** in `map.visible` (the enricher's own "unseen" predicate), and the same hash picks one with a `voices:` entry. Deterministic per (seed, turn, world state); duplicates what szept/narration already hint at, never replaces it.
- **Mixing discipline:** dedicated bed channel + small SFX channel pool (default 6); voicing shares the SFX pool at lower volume; per-category volumes `master × ambient|sfx` clamped 0–1.

## 6. Config, CLI, options

- `config.yml → audio: {enabled: true, master: 0.8, ambient: 0.7, sfx: 0.8}` (`VALID_KEYS` + nested dict, the `llm`/`quickslots` precedent). Installed extra + `enabled: true` = sound on; the install is the consent (open decision #39).
- `--mute` CLI flag (argparse `store_true`, wins over config, session-only).
- Options screen: one toggle line (`a` — audio on/off, writes config like the others); volume numbers stay config-file-only in v1.
- No backend installed → one dim launch line in the log (locale keys EN/PL: "The world is silent. (`uv sync --extra sound`)" in-voice), then never mentioned again.

## 7. Implementation order (CC execution plan)

Feature branch `feat/m11-glosy`; each story keeps `main` playable; **golden byte-identical throughout** (audio subscribes, draws nothing, publishes nothing).

1. **US 14.1 — Backend & skeleton**: `sound` extra, backend Protocol + Pygame/Null backends, `AudioSystem` bus wiring, config keys + `--mute` + Options toggle + launch note. *Verify: app boots with and without the extra (Pilot); fake-backend unit tests; config round-trip; golden untouched.*
2. **US 14.2 — Catalog & starter assets**: `content/audio.py` loader, `sounds.yml` + `CREDITS.yml` schemas, `tools/gen_sounds.py` + committed starter set, CI existence/credit checks. *Verify: manifest validates; every referenced file exists and is credited.*
3. **US 14.3 — Ambient beds**: selector + fade, phase/festival variants, initial kick, dno heartbeat. *Verify: fake backend records the right bed across the (depth × phase × festival) matrix; exactly one bed at a time.*
4. **US 14.4 — Event SFX**: rule_key-keyed dispatch, the v1 set, death sting, the crane's big sound. *Verify: fixture events → expected sound keys; unmapped events stay silent.*
5. **US 14.5 — Distance voicing**: deterministic trigger, offscreen predicate, per-species voices. *Verify: same seed + route = same voicing schedule; visible monsters never voice; zero draws from game RNG streams.*
6. **US 14.6 — Polish & docs**: mixing/volume pass, README (`--extra sound`), ARCHITECTURE/CHANGELOG, locale parity, golden + sims re-verified.

**Definition of done:** (a) `uv run wyraj` without the extra is byte-identical to today, one dim note aside; (b) with the extra, beds follow depth/phase/festival and the v1 SFX set fires — provable via the recording fake without any audio hardware; (c) golden transcript and both sims untouched; (d) every asset validates against `CREDITS.yml` (CC0/CC-BY only) in CI; (e) mypy strict stays green outside `ui/`; (f) `--mute`, the config block, and the Options toggle all silence it completely.

## 8. Open Decisions (for Prestarius)

36. **Backend** — pygame-ce ≥ 2.5.8, no fallback backend, degrade to silence (spec default, per 2026-08-16 research) — confirmed?
37. **Placement** — `ui/audio.py` inside the existing UI package (spec default; audio is presentation) vs. a new `wyraj/audio/` top-level package (repo-layout change)?
38. **v1 assets** — synthesized starter set from a checked-in stdlib generator, replaced by curated freesound picks over time (spec default) vs. ship the system silent until hand-curation?
39. **Default state** — audio on when the extra is installed (spec default: installing is consent) vs. off until enabled in Options?
40. **Voicing knobs** — trigger modulus 17, radius 12 (spec defaults) — accept as tuning starting points?
