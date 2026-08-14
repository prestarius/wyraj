# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Wyraj** — a narrated roguelike in Slavic dark fantasy: ADOM-class systemic depth fused with rich adventure prose. The full specification is `docs/WYRAJ_PROJECT.md` — read it before non-trivial work. `docs/IMPLEMENTATION_PLAN.md` is the working backlog (epics/stories/tasks per milestone).

Licensing (decided 2026-08-14): AGPL-3.0 for code, CC-BY-SA 4.0 for `data/` content, CLA for contributors (files land in M3, US 4.5).

Python 3.12+, `uv`-managed, Textual TUI. English first; Polish is a first-class localization target — never hardcode assumptions that break grammar-aware templating (string form tables, per-language narration packs).

## Commands

- `uv sync` — install/update dependencies
- `uv run wyraj` — run the game (`--seed N` for deterministic replay, `--ascii` for CP437 fallback)
- `uv run pytest` — all tests; single test: `uv run pytest tests/test_core_ecs.py -k name`
- `uv run ruff check .` and `uv run ruff format .` — lint/format
- `uv run mypy src/wyraj/core src/wyraj/narration` — strict typing on core and narration

## Architecture (the rules that bind)

- **`core/` never imports from `ui/`.** Core emits typed `GameEvent` dataclasses (facts, not text) on an event bus; UI and the narration engine are subscribers. The game must run headless (tests, sims, balance bots).
- **Deterministic core.** Same seed + same inputs = same run. Separate seeded `random.Random` streams: `worldgen`, `combat`, `loot`, `narration`. Never use wall-clock randomness. The optional LLM narrator is cosmetic-only and must never affect game state.
- **Data-driven content.** Monsters, items, effects, and narration templates live in YAML under `data/`, validated with pydantic schemas in `content/`. Adding content must not require engine changes.
- **Narration pipeline:** `GameEvent → ContextEnricher → Narrator.compose() → NarrativeLog`. Default narrator is the deterministic `TemplateNarrator` (Tracery-style YAML grammar packs); `LLMNarrator` is an optional backend behind the same interface.
- Hand-rolled minimal ECS (entities are int ids, components are frozen dataclasses); energy/speed-based turn scheduler.

## Working rules (from spec §12)

- Work milestone by milestone (M0–M5 in the spec); **do not scaffold future milestones early**.
- After M0, keep `main` playable; feature branches per system.
- Prefer many small data files over clever engine features; when mechanics and narration quality conflict, narration wins.
- **Ask Maciek before:** adding dependencies beyond spec §3, changing the event schema, or altering the repo layout.
- Conventional commits; update CHANGELOG per milestone.

## Testing strategy

- Golden-run tests: fixed seed + scripted input → full event-log snapshot in `tests/golden/`; any core change that alters a log must be intentional.
- Every grammar pack entry is rendered against fixture contexts (no unresolved slots, no repetition within window).
- CI fails on invalid YAML content; Textual `Pilot` smoke tests for the UI.
