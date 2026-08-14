# Changelog

All notable changes to Wyraj. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
