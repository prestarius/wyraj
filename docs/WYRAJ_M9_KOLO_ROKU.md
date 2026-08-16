# WYRAJ — M9 "KOŁO ROKU" — Time, Weather, Festivals Specification

> **Status:** Draft v0.1 — **Milestone 9**, addendum to `WYRAJ_PROJECT.md`; expands the M9 outline in `WYRAJ_ROADMAP_M8PLUS.md`
> **Prerequisites:** M0–M8 (surface biomes, gromnica/light economy, shrines & favors, codex tiers, szept, narration engine)
> **Principle:** Slavic folklore is calendrical — the year's turning is the mythology's engine. Time must be *pure*: every clock, sky, weather, and festival is a deterministic function of `(seed, turn)`. Nothing is stored that can be derived; nothing random that cannot be replayed.

---

## 1. The clock — pure functions of the turn

New module `core/calendar.py`, no state, no RNG streams:

- **Day = 240 turns**, four phases: świt (dawn) 0–19, dzień (day) 20–139, zmierzch (dusk) 140–159, noc (night) 160–239.
- **The wheel = 12 days.** The run's starting day is `sha256(seed, "calendar") % 12` — festivals become part of seed identity ("seed 8814 is a Kupała-night start").
- **Festivals** at fixed wheel positions: **Gromniczna** (day 2), **Noc Kupały** (day 5), **Dożynki** (day 8), **Dziady** (day 11).
- **Weather** is one roll per absolute day, `sha256(seed, "weather", day)`: jasno (clear, weight 5), deszcz (rain, 3), mgła (mist, 2), burza (storm, 2). Surface-only; the crypts have their own weather and it is called the dark.
- **Time passes underground** (open decision #29): the wheel turns whether you watch it or not — surfacing into a different festival than you left is folklore working as intended.

`Game.step` detects phase/day boundaries by comparing before and after the turn increment and publishes: `PhaseChanged(phase, day, festival)`, `WeatherChanged(kind)` at each dawn, `FestivalDawned(festival)` on festival mornings. **This means the golden transcript changes** — the seed-42 walk crosses at least one phase boundary. Regenerated once, intentionally, in the story that introduces the events (open decision #30).

## 2. Night and weather — mechanics

All surface-only (depths 1–2; the wieś keeps full sight — lit windows, dogs, habit):

- **FOV:** dzień 8 · świt/zmierzch 6 · noc 5; **mgła** −2 on top; floor 3. Crypts unchanged (their darkness is M8's).
- **Rain (deszcz/burza) douses unprotected flame:** a lit gromnica on the surface loses 1 extra turn per turn while it rains; when rain finishes it, the usual `LightExtinguished` fires.
- **Burza:** rain effects, plus Perun is *present*: an offering at his shrine during a storm grants double favor duration, and lightning cracks as a deterministic ambient event (`LightningStruck`, `sha256(seed, turn) % 37 == 0` during storms — cosmetic, narrated).
- **Spawn tables read the sky at generation time.** Level population already happens once, at first visit — the phase at that moment shifts the weights (still fully deterministic: same seed + same route = same world): at **noc**, strzyga weight ×3 in puszcza/bagna; the **południca** — a new noon demon (`data/bestiary/poludnica.yml`: fast, fear-striking, wheat-glare bright) — enters the puszcza pool *only* during dzień. The midday demon is the inversion that writes itself.

## 3. Festivals — one ritual opportunity each

Each festival holds for its whole wheel-day and is announced at świt (narrated, EN/PL):

- **Gromniczna** — candles are blessed: every lit gromnica burns at half rate for the day (its turns decrement every other turn).
- **Noc Kupały** — when noc falls and the player stands on a surface level, the fern flowers: one **kwiat paproci** blooms on a random floor tile of that level (worldgen stream; once per run, saved as a flag) and `KupalaBloom` narrates the direction the dark got warmer. The flower is a consumable (full heal — the legendary find is walking away alive).
- **Dożynki** — the harvest asks nothing back: resting in the wieś costs no satiation that day.
- **Dziady** — the dead walk but are *talkable*: bumping a martwiak converses instead of striking (`TalkedToDead` — first talk opens the codex entry at *partial*, a second completes it at *full*: entries from conversation, not killing), and martwiaki carry a `Peaceful` component for the day — they will not initiate, though they defend themselves.

## 4. Presentation

- **Pane line** (CharacterPanel, under the turn counter): phase glyph (☀ ☾ with dawn/dusk variants), day name, moon glyph cycling over the wheel, weather mark (☂ mist ≋ storm ⚡), festival name in gold. ASCII fallbacks throughout; every state also differs in text (color-blind rule).
- **Sky tint:** surface floor styles shift with the phase — warm at świt, plain at dzień, ember at zmierzch, blue-dark at noc. Cosmetic, `MapView` only.
- **Narration palettes:** `phase_changed` (per phase), `weather_changed` (per kind), `festival_dawned` (per festival), `kupala_bloom`, `talked_to_dead`, `lightning_struck` — all EN+PL, all fixtures.

## 5. Determinism & persistence

- Calendar, weather, festivals: derived — **zero saved state**. The only new save field is `kupala_bloomed` (the once-per-run flower). `Peaceful` rides component reflection.
- No new RNG streams (the schema is save-versioned): everything time-flavored uses `sha256(seed, …)`, spawn-weight shifts ride the existing `worldgen` draws.
- Golden transcript: regenerated once with `GOLDEN_REGEN=1`, in the same commit that introduces `PhaseChanged`, with the regeneration named in the commit message (the sanctioned procedure).

## 6. Implementation order (CC execution plan)

Feature branch `feat/m9-kolo-roku`; each story keeps `main` playable.

1. **US 12.1 — The clock**: `core/calendar.py` pure functions + boundary events in `step` + golden regeneration. *Verify: calendar unit tests (phase math, wheel, seeded start, weather distribution); same seed = same calendar; golden regenerated intentionally.*
2. **US 12.2 — Night & weather mechanics**: surface FOV modifiers, rain candle drain, storm offering bonus, lightning. *Verify: FOV table per phase/weather; a candle dies faster in the rain; storm doubles favor.*
3. **US 12.3 — Sky-aware spawns**: phase-shifted weights, południca (bestiary + discovery + codex + forms). *Verify: populate at noc vs dzień differs deterministically; południca never spawns at night.*
4. **US 12.4 — Festivals**: the four rituals, `Peaceful`, kwiat paproci, dziady talk/codex, festival announcements. *Verify: each festival's effect headlessly; bloom fires once and survives save; talked martwiak opens codex without a kill.*
5. **US 12.5 — Presentation**: pane calendar line, sky tints, ascii fallbacks. *Verify: pane renders all phase/weather/festival combos, mono-distinguishable.*
6. **US 12.6 — Polish & docs**: szept for first night ("The dark between the trees is not the dark between walls."), legend/help notes, CHANGELOG, docs refresh, sim re-measured (night spawns touch difficulty).

**Definition of done:** (a) calendar/weather/festival state is provably derived — a fresh `Game(seed)` at turn N equals a stepped one; (b) golden regenerated exactly once and stable thereafter; (c) all four festivals have headless tests and EN/PL narration; (d) południca and strzyga spawn shifts are deterministic per route; (e) the pane shows the wheel in both art modes; (f) the descent sim still lands inside the M8 sanity floor.

## 7. Open Decisions (for Prestarius)

26. **Clock size** — 240-turn day, 12-day wheel (spec default), or a longer/shorter year?
27. **Południca** — confirmed as the new monster? (She is the noon demon of Polish folklore; the only new creature in M9.)
28. **Kwiat paproci effect** — full heal (spec default: the legend is surviving) vs. a permanent codex/meta unlock?
29. **Underground time** — the wheel turns while you're below (spec default, folkloric) vs. surface-only time?
30. **Golden regeneration** — sanction the one intentional transcript regeneration that calendar events force?
