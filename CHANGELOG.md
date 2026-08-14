# Changelog

All notable changes to Wyraj. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
