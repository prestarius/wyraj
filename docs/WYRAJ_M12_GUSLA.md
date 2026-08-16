# WYRAJ — M12 "GUSŁA" — Data-Pack Modding Specification

> **Status:** Draft v0.1 — **Milestone 12**, addendum to `WYRAJ_PROJECT.md`; expands the M12 outline in `WYRAJ_ROADMAP_M8PLUS.md`
> **Prerequisites:** the YAML-everything architecture (M0–M11) — this milestone adds no content system, it opens the existing ones
> **Principle:** the architecture is already *implicitly* moddable; one disciplined step makes it a real surface. **Data only, forever:** a pack is YAML and asset files — no scripting, no plugin code, no import hooks. That keeps the AGPL boundary clean and the security story trivial: loading a pack can produce bad content, never running code. CC-BY-SA contributors become content authors instead of patch submitters.

---

## 1. The pack — a folder shaped like `data/`

```
pack-pomorski/
  pack.yml            # manifest — required
  bestiary/*.yml      # same schemas as data/, validated by the same pydantic models
  items/*.yml
  hooks/*.yml
  loot/*.yml
  errands/*.yml
  epithets/*.yml
  narration/<lang>/*.yml
  locale/<lang>.yml
  audio/sounds.yml + beds|sfx|voices/*
```

Manifest (`content/packs.py`, pydantic):

```yaml
name: "Pack Pomorski"
key: pomorski            # slug, unique among loaded packs
version: "1.0"
author: "Prestarius"
license: "CC-BY-SA-4.0"  # packs are content; NC/ND refused like audio credits
description: "Three coastal horrors from the Pomeranian shore."
```

Enabled via `config.yml → packs: [~/packs/pomorski, ...]` (ordered — later packs win; `~` expanded). A missing or invalid pack **never blocks the game**: it is skipped with one dim launch note, the `_load_config_safely` doctrine.

**v1 surface (open decision #41):** the keyed catalogs above plus narration, locale, and audio. Economy knobs, origins, intro/prologue, and portrait art stay base-only in v1 — they are balance and onboarding, the places a bad pack hurts most quietly. Explicitly forever out: biomes/procgen, event types, mechanics — those are code.

## 2. Merge semantics — override by key, extend by new key

One rule everywhere, no per-type cleverness:

- **Root chain:** `content/paths.py` grows `data_roots()` → `[data/, pack1/, pack2/, …]`, a module registry set once at startup from config (tests keep the single-`root` override they already use). Every loader iterates the chain in order into one dict — a pack entry with an existing key **replaces it whole**; a new key **extends** the catalog. No deep-merging of half a monster.
- **Narration:** same rule at rule-key granularity per language — a pack that redefines `talked_to/gossip` owns that whole variant list (open decision #42); a pack adding `lore_discovered/topielica` extends. Languages are unioned across roots: a pack shipping `narration/de/` + `locale/de.yml` makes `--lang de` real, EN merged underneath as today (open decision #45 — `--lang` stops being a closed choice list).
- **Locale:** per-key merge over the chain.
- **Audio:** `sounds.yml` sections merge by key; each entry's file resolves **relative to the root that declared it** (the catalog stores resolved paths), so packs carry their own sounds. CC0/CC-BY/CC-BY-SA discipline extends to pack CREDITS.
- **Determinism unchanged:** same seed + same meta + **same pack set** = same run. No packs = byte-identical to today — golden and sims run pack-free and must not move.
- **Saves are pack-aware:** the save records `[(key, version), …]`; loading under a different pack set returns the same "no" as a version mismatch (permadeath-honest — a run can't continue in a world with different monsters in it; open decision #43). Meta is unaffected: codex/achievement keys from a removed pack simply go dormant (`extra="allow"` already tolerates unknown keys).

## 3. `--validate-pack` — friendly errors, then a report

`uv run wyraj --validate-pack ./pack-pomorski` (entrypoint command like `--history`):

- Validates the manifest, then every YAML against the real content models — errors reported per file, per field, in plain words ("bestiary/topielica.yml: hp must be a positive integer"), not pydantic tracebacks.
- Cross-checks: audio files exist and are credited; narration rule keys renderable against fixtures' vocabulary (event exists); PL/DE narration only warned, never required — a pack may be EN-only.
- Ends with the honest summary: `adds 3 monsters, 2 items, 14 narration rules; overrides 1 (talked_to/gossip)` — override visibility is the anti-footgun.
- Exit 0/1 so pack authors can CI their own repos.

## 4. Pack Pomorski — the in-repo example

`examples/pack-pomorski/` (open decision #44), maintained and CI-validated so the surface can't silently rot — three coastal creatures, EN+PL, full forms:

- **topielica** — the drowned bride of the shore-meres; the utopiec's grief-struck cousin (bagna; prefers water).
- **stolem** — a Pomeranian giant, slow and vast; less a fight than weather (puszcza, rare).
- **klabaternik** — the ship-spirit that walked inland when its wreck rotted; helpful right up until it isn't (bagna/puszcza).

Each: bestiary entry with weakness + folklore, discovery/narration lines, a trophy + drops-free loot (no economy surface in v1 — they drop nothing, which is itself coastal-poor flavor), one distance voice each reusing base voice files. Plus `docs/MODDING.md`: authoring walkthrough (copy the example, edit, validate, add to config), the merge rules table, the license expectations, and the "data only, no code, ever" invariant stated as a promise.

## 5. Implementation order (CC execution plan)

Feature branch `feat/m12-gusla`; each story keeps `main` playable; golden/sims pack-free and byte-identical throughout.

1. **US 15.1 — Pack core**: `content/packs.py` (manifest model, discovery, ordering), `data_roots()` chain + startup registration from config, skip-with-note on invalid packs, save pack-fingerprint + refuse-on-mismatch. *Verify: manifest validation; ordering; no-packs run byte-identical; save refuses under a changed pack set.*
2. **US 15.2 — Keyed-catalog merging**: bestiary/items/hooks/loot/errands/epithets loaders walk the chain (override whole entry, extend new keys). *Verify: fixture pack overrides one monster and adds one; base-only loads unchanged.*
3. **US 15.3 — Narration, locale, audio merging**: per-language rule-key override/extend, language union (+ dynamic `--lang`), locale key merge, audio per-root file resolution. *Verify: a DE mini-fixture renders end-to-end with EN fallback; PL-parity test stays base-only; pack sound resolves to the pack's file.*
4. **US 15.4 — `--validate-pack`**: schema walk with friendly per-file errors, cross-checks, adds/overrides summary, exit codes. *Verify: the example passes; deliberately broken fixtures name file and field.*
5. **US 15.5 — Pack Pomorski + docs**: the example pack (3 creatures ×2 languages), CI validates it, `docs/MODDING.md`, README/CHANGELOG/ARCHITECTURE refresh. *Verify: example validates via the command; a Pilot boot with the pack enabled discovers a topielica headlessly; full suite green with and without packs.*

**Definition of done:** (a) with no packs configured, every artifact — golden transcript, sims, tests — is byte-identical to v0.12; (b) a pack can override an existing monster and add a new one, with narration, purely from config; (c) a language pack makes a new `--lang` work with EN fallback and zero code changes; (d) `--validate-pack` gives friendly errors, an override summary, and CI-usable exit codes; (e) the example pack is validated in CI and documented in `docs/MODDING.md`; (f) a save made with packs refuses to load without them; (g) no code path ever imports, execs, or evals anything from a pack directory.

## 6. Open Decisions (for Prestarius)

41. **v1 surface** — keyed catalogs + narration + locale + audio; economy/origins/intro/portrait deferred (spec default)?
42. **Narration merge granularity** — whole-rule override (spec default: predictable ownership) vs. variant-append (richer, but two packs interleave unpredictably)?
43. **Saves under packs** — refuse load on pack-set mismatch (spec default, permadeath-honest) vs. load-with-warning?
44. **Example pack** — `examples/pack-pomorski/` with topielica / stolem / klabaternik (spec default; note: adds a top-level `examples/` dir — the sanctioned repo-layout change)?
45. **Dynamic languages** — packs may introduce new `--lang` values with EN fallback (spec default) vs. EN/PL closed list?
