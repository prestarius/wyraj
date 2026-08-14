# WYRAJ — Implementation Plan

> Derived from `WYRAJ_PROJECT.md` (Draft v0.1). One epic per milestone.
> Detail is deliberately front-loaded: M0 is task-level, M1 story+task level,
> M2–M5 story-level only — they get broken down when their milestone starts
> (spec §12: no early scaffolding). IDs are stable; never renumber.

Each story lists a **Verify** step — the story is done when it passes.

---

## Epic 1 — M0: Walking Skeleton

Goal: `uv run wyraj --seed 42` is a completable-by-dying game; golden-run test replays it; CI green.

### US 1.1 — Repo scaffold & toolchain
- 1.1.1 — `pyproject.toml` (uv-managed): project metadata, `wyraj` entry point, deps: `textual`, `pyyaml`, `pydantic`; dev deps: `pytest`, `ruff`, `mypy`
- 1.1.2 — ruff (lint+format) and mypy config (strict on `core/`, `narration/`); `src/wyraj/` package layout per spec §9
- 1.1.3 — GitHub Actions CI: ruff, mypy, pytest
- 1.1.4 — `README.md` stub, `CHANGELOG.md`, `.gitignore`
- **Verify:** fresh clone → `uv sync && uv run pytest` green locally and in CI; `uv run wyraj` prints a placeholder and exits 0.

### US 1.2 — ECS core
- 1.2.1 — `core/ecs.py`: entity ids, component store (frozen dataclasses), query API (~200 lines, hand-rolled)
- 1.2.2 — Components: `Position`, `Renderable`, `Health`, `Melee`, `Player`, `AI`, `Lore`
- 1.2.3 — `core/rng.py`: named seeded streams (`worldgen`, `combat`, `loot`, `narration`) from one master seed
- **Verify:** `tests/test_core_ecs.py` — create/query/remove entities; same seed → identical stream draws.

### US 1.3 — Event bus & turn scheduler
- 1.3.1 — `core/events.py`: `GameEvent` base, typed events (`AttackResolved`, `EntityMoved`, `EntityDied`, `TurnEnded`), subscribe/publish bus
- 1.3.2 — Energy/speed-based `TurnScheduler` (actors accumulate energy, act at threshold)
- **Verify:** unit tests — event delivery order; two actors with different speeds interleave correctly over N turns.

### US 1.4 — Map, FOV, movement
- 1.4.1 — Cellular-automata forest map (pure function of `(seed, params)`), walkability
- 1.4.2 — Symmetric shadowcasting FOV + explored-tile memory
- 1.4.3 — `MovementSystem` + `InputSystem` intent queue; `@` moves with hjkl/arrows, walls block
- **Verify:** golden test — map for seed 42 matches snapshot; FOV symmetric on fixture map; scripted moves land where expected.

### US 1.5 — One monster, combat, death
- 1.5.1 — Bies defined in `data/bestiary/bies.yml`; pydantic loader in `content/`
- 1.5.2 — `AISystem` v0 (approach player), `CombatSystem` (melee, HIT/MISS/KILL outcomes via `combat` stream), `DeathSystem`
- 1.5.3 — Death screen with seed display; `--seed` CLI flag
- **Verify:** headless scripted run on seed 42 ends in player death; event log snapshot stable.

### US 1.6 — Narration pipeline v0
- 1.6.1 — `narration/engine.py`: bus subscription → `Narrator.compose()` → `NarrationLine`s (no enricher/coalescing yet)
- 1.6.2 — `narration/templates.py`: YAML grammar pack loader, weighted variant pick via `narration` stream, slot filling from event + `Lore`
- 1.6.3 — First EN pack: `data/narration/en/combat.yml` (attack/move/death lines)
- **Verify:** every pack entry renders against fixture events with no unresolved slots; same seed → same lines.

### US 1.7 — Textual UI shell
- 1.7.1 — Three-pane layout: `MapView` (colored Unicode, FOV dimming), `CharacterPanel` (static portrait + HP bar), `NarrativeLog` (scrollable), footer keybar
- 1.7.2 — "czarnoles" dark theme (.tcss); render loop reads core state read-only
- **Verify:** Textual `Pilot` smoke test — app boots, keys move `@`, log receives lines.

### US 1.8 — Golden-run harness
- 1.8.1 — Headless runner: seed + scripted input → full event log; snapshot in `tests/golden/`
- 1.8.2 — Tag `v0.0-m0`; CHANGELOG entry
- **Verify:** M0 definition of done — golden replay of seed 42 passes in CI.

---

## Epic 2 — M1: It Reads Like a Story

### US 2.1 — ContextEnricher
- 2.1.1 — HP bands (healthy/bloodied/dying), light/darkness, visibility ("something unseen")
- 2.1.2 — Recency memory: anti-repetition window + callback tags ("…again")
- **Verify:** same event renders differently under `player_dying` / `darkness` fixtures; no repeat within window.

### US 2.2 — TurnComposer (coalescing)
- 2.2.1 — Batch one turn's events into composed sentences before rendering
- **Verify:** multi-event turn fixture → single composed paragraph snapshot.

### US 2.3 — String-form tables
- 2.3.1 — `narration/forms.py`: form-table model (EN maps all cases to base form); template slots like `{target.name.def}` / `{target.name.bier}` resolve through it
- **Verify:** EN pack renders via form tables; a PL fixture entry with 7 cases resolves correctly (engine ready, content later).

### US 2.4 — Content wave 1
- 2.4.1 — 5 monsters (bies, wilk, utopiec, strzyga, martwiak) with `Lore` + narration entries
- 2.4.2 — 10 items + inventory/get/use; folk remedies (odwar, gromnica, sól święcona)
- 2.4.3 — Hunger clock (`HungerSystem`)
- **Verify:** content validation in CI; headless sim (random-walk bot, N seeds) crash-free.

### US 2.5 — Examine & bestiary codex
- 2.5.1 — Look/examine command; codex screen unlocking discovered `Lore` entries
- **Verify:** Pilot test — examine a monster, codex shows its folklore entry.

### US 2.6 — Reactive portrait
- 2.6.1 — Layered portrait: base + wielded weapon overlay + HP-band decals; prototype box-drawing vs halfblock (open decision #5 — show Maciek both)
- **Verify:** portrait snapshot changes across HP bands and weapon swaps.

---

## Epic 3 — M2: Depth & Danger *(stories only — break down at milestone start)*

- US 3.1 — Multi-level descent: kurhany BSP crypts, stairs, in-run level persistence
- US 3.2 — Status effects (bleeding, fear, poison, blessing) + lighting/light sources
- US 3.3 — Save/load, single slot, deleted on death (permadeath honored)
- US 3.4 — Loot tables, equipment slots, AI behaviors (pack wolves, ambusher strzyga, fleeing licho)
- US 3.5 — Story hooks v1 (3 hook types per biome)

## Epic 4 — M3: Public Release Cut

- US 4.1 — Bagna biome + village hub (rest, trade v0, rumor lines)
- US 4.2 — Character creation (Wygnaniec / Zielarka / Najemnik)
- US 4.3 — Morgue files + run history (SQLite), `--ascii`, config file
- US 4.4 — Docs polish (README GIF, CONTENT.md, NARRATION.md), CoC, issue templates → **publish; re-verify + register PyPI name first**
- US 4.5 — Licensing rollout (decided 2026-08-14): `LICENSE` = AGPL-3.0 for code, `data/LICENSE` = CC-BY-SA 4.0 for content, `CLA.md` + CLA-assistant (or DCO-style) flow for contributors; license headers/metadata in `pyproject.toml`

## Epic 5 — M4: Polski

- US 5.1 — PL narration packs authored natively; case-resolution exercised for real
- US 5.2 — `--lang pl` + UI catalog PL
- US 5.3 — Blog post: grammar-aware narration engine for Polish

## Epic 6 — M5: AI Narrator (optional)

- US 6.1 — `LLMNarrator` behind config flag (Ollama-first, OpenRouter fallback; timeout → template fallback; cosmetic-only contract)
- US 6.2 — Style-guide prompt + per-run cost/latency stats; comparative blog post

---

## Open decisions blocking future work (spec §13)

| # | Decision | Needed by | Spec recommendation |
|---|---|---|---|
| 2 | ~~License~~ — **RESOLVED 2026-08-14: AGPL-3.0 (code) + CC-BY-SA (data), with CLA** (US 4.5) | M3 publish | — |
| 3 | Overworld vs pure descent | post-M5 | descent + hub for now |
| 4 | Fear/mood: mechanic vs narration-only | M3 | narration-only until M3 |
| 5 | Portrait art direction | US 2.6 | prototype both in M1 |
