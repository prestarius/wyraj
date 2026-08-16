# WYRAJ — Roadmap M8+ (post-Sylwetka)

> **Status:** Proposal v0.1 — milestone outlines for discussion; each becomes a full CC spec (like M6/M7) once approved
> **Baseline:** M0–M7 + Próg live on `main` (verified against repo, Aug 2026): full loop wieś→puszcza→bagna→3 crypt levels, EN/PL, meta-progression, LLM narrator, Sylwetka pane
> **Ordering rationale:** finish the game before widening it — M8 gives Wyraj an ending; M9–M10 deepen the living world; M11 gives it a voice; M12 opens the data to others. Public release/reach is deliberately parked (see Parking Lot).

---

## M8 — "DNO" (The Bottom): ending, antagonist, victory

**The gap it closes:** the prologue promises "whatever waits at the bottom of the dark." Nothing waits. A roguelike without a win condition is a treadmill; permadeath only means something when survival can *conclude*.

**Scope sketch:**

- **Depth extension:** crypt levels 4–6 beneath the kurhany, escalating in darkness rules (level 6: no ambient light at all — gromnica economy becomes the run's spine) and in narration register (the szept... changes sides: environment lines increasingly address the player directly).
- **The antagonist:** not a stat-block boss — this game's climax must be *narrated*. Proposal: **Wij** (folklore: the buried one whose gaze kills when his lids are lifted — the deepest-cut Slavic pick, and mechanically perfect for a light/sight game). The encounter is a multi-phase *situation*, not a slugfest: his servants must lift his eyelids; the player fights the lifting, in the dark, while the narration counts what he begins to see.
- **Victory & endings:** 2–3 epilogues driven by run state (codex completeness, god favor from shrine offerings, whether the dziad was befriended). Epilogue is prologue-format (paged, typewriter). A victory writes to `meta.yml` — winning origins get marked, title screen line changes forever ("The birds returned, once.").
- **Post-victory meta:** victory unlocks **"Głębiej"** (deeper) — NG+-style modifier runs (darker, richer, crueler drop tables) rather than level-cap inflation.
- **Balance doctrine:** win rate for a skilled player target ~10–20% (roguelike-honest); headless sims extended with a scripted "competent bot" baseline.

**Size:** large (procgen tiers, phase-encounter system, epilogue content ×2 languages). **The** milestone — everything after it decorates a finished game.

---

## M9 — "KOŁO ROKU" (Wheel of the Year): time, weather, festivals

**The gap it closes:** the world has space but no time. Slavic folklore is fundamentally *calendrical* — the year's turning is the mythology's engine, and it's sitting unused.

**Scope sketch:**

- **Day/night cycle** (turn-count based, visible as sky-tint on surface maps + a moon-phase glyph in the pane): night alters spawn tables (strzygi hunt, południca *only* at noon — she's a midday demon, the inversion writes itself), FOV radii, and narration palettes.
- **Weather:** rain (douses unprotected flame), mist (FOV), storm (Perun active — lightning as environmental event, his shrine blessings stronger).
- **Festival days** on a compressed in-game calendar, each a run-modifier event with unique narration, spawns, and one ritual opportunity: **Noc Kupały** (fern flower — one night, one legendary find), **Dziady** (the dead walk but are *talkable* — codex entries from conversation, not killing), **Gromnica/Candlemas** (candle items blessed), harvest/solstice hooks.
- Calendar state is per-run (seeded start date) — determinism preserved; festivals become part of seed identity ("seed 8814 is a Kupała-night start").

**Size:** medium. Highest fabular return-per-effort on the list; also the best blog material after the declension engine.

---

## M10 — "ZLECENIA" (Errands): the village asks things of you

**The gap it closes:** rumors exist but lead nowhere; the village is a service hub, not a community. (Deliberately deferred from M6's out-of-scope list — now it's time.)

**Scope sketch:**

- **Notice-post / rumor escalation:** village rumors become 1–3 concrete, procedurally assembled errands per run (bring back proof of the utopiec that took the miller's son; recover the shrine-keeper's censer from crypt 2; escort no one — this game doesn't do escorts).
- Rewards: silver, reputation with *named villagers* (persistent, meta.yml — the smith remembers souls the way the dziad does), rare stock unlocks.
- **Failure states that narrate:** ignored errands resolve badly off-screen between runs ("The mill stands empty now.") — the village changes across deaths. Light touch: 2–3 persistent village-state flags, not a simulation.
- Strictly bounded: no quest journal UI beyond a codex tab; no branching dialogue trees — requests and outcomes flow through the narration engine like everything else.

**Size:** medium, mostly content + a small errand-assembly system.

---

## M11 — "GŁOSY" (Voices): sound implementation

**The gap it closes:** the game speaks only through text; folk horror lives half in the ear. Even minimal, well-chosen audio (wind in the puszcza, the wet sound of the bagna, a strzyga's cry offscreen) multiplies dread far beyond its implementation cost.

**Scope sketch:**

- **Architecture first:** an `AudioSystem` subscribing to the existing event bus exactly like the narration engine does — events carry facts, audio reacts. Zero coupling to core (pillar: game must run identically silent). New events needed: none — everything worth hearing already emits.
- **Optional dependency:** shipped as an extra (`uv sync --extra sound`), candidate backends `pygame.mixer` vs `miniaudio` — **verify current state of both before the full spec** (maintenance, wheels for mac/Linux/Windows, latency, licensing). No audio dep installed → game runs silent with a single dim note at launch, nothing else changes.
- **Sound layers:**
  - **Ambient beds** per biome/depth (wieś hearth-and-hens, puszcza wind and corvids, bagna drips and bubbles, kurhany near-silence with stone settling — silence as a designed layer, not an absence; level 6 gets a *heartbeat*).
  - **Event SFX**, sparse by design: combat hits/kills, item pickup, gromnica lit/doused/dying, stairs, crane wedge arriving (the one "big" sound in the game), Wij phases (M8 tie-in).
  - **Creature voicing at a distance:** offscreen monsters within N tiles occasionally sound — audio as information (very roguelike: you *hear* the pack before you see it). Deterministic trigger via the narration RNG stream.
  - **UI ticks:** minimal — typewriter prologue murmur, quickslot use, death sting. No sound on every keypress, ever.
- **Day/night & festival variants** ride M9's calendar (night beds differ; Kupała night has distant singing).
- **Asset sourcing & licensing:** CC0-first (freesound.org), full attribution manifest `data/audio/CREDITS.yml`; audio assets live under `data/` → covered by the existing CC-BY-SA content license (verify per-asset compatibility: CC0/CC-BY only, no NC/ND).
- **Config:** `config.yml → audio: {enabled, master, ambient, sfx}` volumes; `--mute` flag; all szept/accessibility guarantees unchanged — audio is never the sole carrier of any information (the narration already says everything).

**Size:** medium — the system is small (one bus subscriber + asset loader); the real work is curation and mixing discipline. Sparse is the aesthetic: this is a game where one sound per minute lands harder than a soundtrack.

**Design guardrail:** no music in v1. Ambient beds and events only — folk horror wants the melody withheld. (A single title-screen drone is the permitted exception; revisit actual music post-M11.)

---

## M12 — "GUSŁA" (Folk Magic): data-pack modding, formalized

**The gap it closes:** the YAML-everything architecture is *implicitly* moddable; one step makes it a real modding surface — and turns CC-BY-SA contributors into content authors rather than patch submitters.

**Scope sketch:**

- **Pack format:** a `wyraj-pack/` directory (manifest + bestiary/items/narration/portrait overlays) loadable via `config.yml → packs:` — merge semantics defined (override vs. extend), schema-validated with friendly errors.
- `uv run wyraj --validate-pack ./mypack` developer command + a documented example pack in-repo ("Pack Pomorski": 3 coastal creatures).
- Localization packs ride the same mechanism (a DE pack becomes possible without touching core).
- Explicit non-goal: no scripting/plugin code execution — data only, keeping the AGPL boundary and the security story trivial.

**Size:** small-medium; mostly loader discipline + docs.

---

## Parking Lot (not milestones yet)

- **Release engineering & reach** (parked by decision — not going world-open for now): PyPI packaging, `textual serve` browser demo, itch.io, asciinema kit, launch posts (Show HN / r/roguelikes / RogueBasin), blog articles, community hygiene. Becomes a milestone whenever Prestarius decides the game is ready to meet people.
- Screen-reader deep pass beyond current color-blind/monochrome guarantees.
- Actual music (beyond M11's ambient beds) — folk instrumentation, only if a composer/collaborator materializes.
- Steam packaging — far future, only after a public release proves demand.
- Overworld travel between multiple villages (main-spec open decision #3) — remains open; M9+M10 may satisfy the "living world" need without it. Decide after M10.

## Recommended order & first action

**M8 → M9 → M10 → M11 → M12**, with M11 "Głosy" free to slide earlier (it only *shines* after M9's calendar, but its event-bus architecture has zero prerequisites beyond M0). Default proposal stays **M8 first regardless** — nothing competes with "the game can be won."

First action on approval: full M8 "Dno" spec in the established format (design, Wij encounter phases, epilogue prose drafts, implementation order, DoD).
