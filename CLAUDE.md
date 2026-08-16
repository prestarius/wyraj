# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Wyraj** — a narrated roguelike in Slavic dark fantasy: ADOM-class systemic depth fused with rich adventure prose. Specs: `docs/WYRAJ_PROJECT.md` (core, M0–M5), `docs/WYRAJ_M6_POWROTY.md` (meta-progression), `docs/WYRAJ_PROG_SPEC.md` (intro/onboarding), `docs/WYRAJ_M7_SYLWETKA.md` (M7 character pane & quickslots), `docs/WYRAJ_M8_DNO.md` (M8 ending/victory), `docs/WYRAJ_M9_KOLO_ROKU.md` (M9 time/weather/festivals), `docs/WYRAJ_ROADMAP_M8PLUS.md` (M9–M12 outlines, proposal) — read the relevant one before non-trivial work. `docs/IMPLEMENTATION_PLAN.md` is the backlog and status board (Epics 1–12 are DONE through M9 "Koło Roku"; Epics 13–15 = M10–M12 are planned outlines).

Licensing (decided 2026-08-14): AGPL-3.0 for code, CC-BY-SA 4.0 for `data/` content, CLA for contributors. Maintainer is pseudonymous — **"Prestarius" everywhere**; never introduce a real name into the repo.

Python 3.12+, `uv`-managed, Textual TUI. Fully bilingual EN/PL: narration packs are per-language files authored natively (never translated), with per-noun case-form tables — don't hardcode strings that break this (UI chrome goes through `ui/i18n.t()` + `data/locale/`).

## Commands

- `uv sync` — install/update dependencies
- `uv run wyraj` — run the game (`--seed N` skips title/prologue for a deterministic run, `--lang pl`, `--ascii`, `--narrator llm`, `--history`)
- `uv run pytest` — all tests; single test: `uv run pytest tests/test_core_ecs.py -k name`
- `GOLDEN_REGEN=1 uv run pytest tests/test_golden_run.py` — intentionally regenerate the golden transcript (say so in the commit)
- `uv run ruff check .` and `uv run ruff format .` — lint/format
- `uv run mypy` — strict typing on `core/` and `narration/` (relaxed on `ui/`)

## Architecture (the rules that bind)

- **`core/` never imports from `ui/`.** Core emits typed `GameEvent` dataclasses (facts, not text) on an event bus; UI, narration, and the szept hint system subscribe. The game runs headless (tests, sims).
- **Deterministic core.** Same seed + same meta-state + same inputs = same run. Named seeded streams (`worldgen`, `combat`, `loot`, `narration`); per-level generation is a pure function of `sha256(seed, depth)`. No wall-clock in core (game time itself is `core/calendar.py`: pure functions of `(seed, turn)`). The LLM narrator is cosmetic-only.
- **World chain:** wieś(0) → puszcza(1) → bagna(2) → kurhany(3–8, no sky shafts below 6, the Wij's vault at 8); entities carry `OnLevel`, off-level actors are frozen.
- **Meta-progression:** `~/.wyraj/meta.yml` survives death and mutates only at defined transaction points (bank/stash/purchase/offering/codex/death), each publishing `MetaTransaction`; HMAC flags hand-edits without punishing. On-body purse and items are always lost on death.
- **Data-driven content.** Monsters, items, hooks, loot, economy, origins, narration packs → YAML under `data/`, pydantic-validated in `content/`. Intro/onboarding content is `data/intro/`, portrait layer art `data/portrait/`, weapon epithets `data/epithets/` (NONE of these belong in `data/narration/` — the pack loader eats every YAML there). Adding content must not require engine changes.
- **Narration pipeline:** `GameEvent → ContextEnricher(tags) → buffer → TurnEnded → TurnComposer paragraph`. New event type ⇒ add a `rule_key` mapping, EN + PL pack rules, and a fixture in `tests/test_narration_templates.py` (the PL-parity and render tests enforce all of it). Paragraphs carry a cosmetic `category` (combat/lore/loot/ambient, mapped in `category_of` in `templates.py`) used only for log tinting — unmapped events default to ambient.

## Working rules (from spec §12)

- Keep `main` playable; feature branch per story, merge `--no-ff`, tag milestone cuts (`v0.8-sylwetka` is current).
- Prefer many small data files over clever engine features; when mechanics and narration quality conflict, narration wins.
- **Ask Prestarius before:** adding dependencies beyond spec §3 (+httpx already sanctioned), changing the event schema, or altering the repo layout.
- Conventional commits; update CHANGELOG per milestone cut.

## Testing strategy

- Golden run: seed 42 + scripted walk (village → puszcza) → byte-stable event+narration transcript in `tests/golden/`; any diff must be intentional.
- 50-run shared-meta sim (`tests/test_meta_sim.py`) guards the economy doctrine.
- Every grammar pack entry (both languages) renders against fixtures; locale catalogs must not drift EN↔PL.
- Tests sandbox `WYRAJ_HOME` (autouse fixture in `tests/conftest.py`) — never touch the player's real `~/.wyraj`.
