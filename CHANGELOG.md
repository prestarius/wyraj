# Changelog

All notable changes to Wyraj. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.4-m4] — 2026-08-15 — Polski

### Added
- Native Polish narration packs (`data/narration/pl/`) with full rule
  parity to English, authored as original prose — not translations.
- Case-form tables (mian/dop/cel/bier/narz/miej) for every monster and
  item; the strzyga is *ona*, the player declines as *ty/ciebie/tobą*;
  per-rule English fallback if a PL rule is ever missing.
- `--lang pl` (also a `lang:` config key); UI catalog in
  `data/locale/{en,pl}.yml` covering panel, screens, death, trade, and
  character creation; Polish origin intros and descriptions.
- Blog draft: docs/blog/grammar-aware-narration.md.

## [0.3-m3] — 2026-08-15 — Public Release Cut

### Added
- The wieś: an authored village hub with karczmarka (rest), handlarz
  (barter trade v0), and the dziad whose rumors feed the narration.
  Bumping a villager talks; nobody in the wieś wants a fight.
- Bagna biome between forest and crypts: water pools you can see across
  but not wade, swimming utopce that haunt the shorelines, marsh loot and
  three new story hooks (the sunken cross, the fowler's hut, błędne ogniki).
- Character creation: Wygnaniec, Zielarka, Najemnik — distinct stats,
  starting kits, and opening narration; data-driven in `data/origins.yml`;
  `--origin` flag and selection screen.
- Morgue files on death, SQLite run history (`wyraj --history`),
  `~/.wyraj/config.yml`; cause of death tracked and shown.
- Licensing: AGPL-3.0-or-later (code), CC BY-SA 4.0 (`data/`), CLA;
  CONTRIBUTING, Code of Conduct, issue templates.
- Docs: ARCHITECTURE.md, CONTENT.md, NARRATION.md, README with screenshot.

### Changed
- World is now a fixed chain: wieś (0) → puszcza (1) → bagna (2) →
  kurhany (3–5); crypt darkness starts at depth 3. Save format v2.

## [0.2-m2] — 2026-08-14 — Depth & Danger

### Added
- Multi-level descent: BSP kurhany crypts under the puszcza, stairs,
  in-run level persistence, frozen off-level actors, lazy deterministic
  per-level generation (pure function of seed and depth).
- Status effects: bleeding and grave-rot poison (damage over time), fear
  and blessing (to-hit modifiers); inflicted by strzyga/martwiak/bies
  attacks from bestiary data; blessed salt now blesses.
- Lighting: crypts are dark (short FOV); the gromnica burns as a real
  light source and the `darkness` narration context goes live.
- Loot tables per biome; armor slot (wolfskin cloak, quilted kaftan) with
  full-absorb GRAZE outcome; AI behaviors: pack wilki with flanking bonus,
  ambusher strzyga, fleeing licho (new monster).
- Story hooks v1: three discoverable narrative seeds per biome with
  one-shot first-sight narration.
- Save/load: single gzip-JSON slot, RNG streams restored bit-exactly,
  save consumed on load and deleted on death (permadeath honored);
  `s` saves and quits, plain `wyraj` continues a saved run.

## [0.1-m1] — 2026-08-14 — It Reads Like a Story

### Added
- ContextEnricher: HP-band, unseen-attacker, and recency ("again") context
  tags; tag-filtered variant selection with anti-repetition.
- TurnComposer: one composed narrative paragraph per full round.
- Grammar-aware string-form tables (spec §7): EN def/indef/plural/pronoun
  accessors, PL case tables supported and tested; slots like
  `{defender.name.def}` in packs.
- Content wave 1: five monsters (bies, wilk, utopiec, strzyga, martwiak),
  ten items (folk remedies, weapons, trinkets), weighted spawns.
- Inventory (get/use/wield), hunger clock with starvation, weapon damage
  flowing into combat events.
- Examine screen, bestiary codex unlocked by sightings, per-monster
  first-sighting narration (`LoreDiscovered`).
- Reactive portrait: HP-band color wash + wound decals + weapon overlay;
  two prototype art directions (`--portrait half|box`) for decision #5.

## [0.0-m0] — 2026-08-14 — Walking Skeleton

### Added
- Project scaffold: uv-managed package, ruff/mypy/pytest toolchain, CI.
- Minimal hand-rolled ECS, typed event bus (events carry facts, not text),
  energy/speed-based turn scheduler, named seeded RNG streams.
- Cellular-automata puszcza map, symmetric shadowcasting FOV with
  explored-tile memory, bump movement.
- First monster (bies, YAML bestiary + pydantic validation), melee combat,
  permadeath with death screen showing the seed; `--seed` and `--ascii` flags.
- Narration pipeline v0: TemplateNarrator with weighted YAML grammar packs,
  first EN combat pack; narration draws from its own RNG stream.
- Textual three-pane UI ("czarnoles" dark theme): map with FOV dimming,
  character panel with portrait and HP bar, scrollable narrative log.
- Golden-run regression: seed 42 + scripted walk → full event+narration
  transcript snapshot (`GOLDEN_REGEN=1` to regenerate intentionally).
