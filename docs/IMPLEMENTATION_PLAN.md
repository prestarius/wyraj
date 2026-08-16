# WYRAJ — Implementation Plan

> Derived from `WYRAJ_PROJECT.md` (Draft v0.1). One epic per milestone.
> Detail is deliberately front-loaded: M0 is task-level, M1 story+task level,
> M2–M5 story-level only — they get broken down when their milestone starts
> (spec §12: no early scaffolding). IDs are stable; never renumber.

Each story lists a **Verify** step — the story is done when it passes.

---

## Epic 1 — M0: Walking Skeleton — **DONE 2026-08-14 (v0.0-m0)**

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

## Epic 2 — M1: It Reads Like a Story — **DONE 2026-08-14 (v0.1-m1)**

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
- 2.6.1 — Layered portrait: base + wielded weapon overlay + HP-band decals; prototype box-drawing vs halfblock (open decision #5 — show Prestarius both)
- **Verify:** portrait snapshot changes across HP bands and weapon swaps.

---

## Epic 3 — M2: Depth & Danger — **DONE 2026-08-14 (v0.2-m2)**

- US 3.1 — Multi-level descent: kurhany BSP crypts, stairs, in-run level persistence
- US 3.2 — Status effects (bleeding, fear, poison, blessing) + lighting/light sources
- US 3.3 — Save/load, single slot, deleted on death (permadeath honored)
- US 3.4 — Loot tables, equipment slots, AI behaviors (pack wolves, ambusher strzyga, fleeing licho)
- US 3.5 — Story hooks v1 (3 hook types per biome)

## Epic 4 — M3: Public Release Cut — **DONE 2026-08-15 (v0.3-m3)**

- US 4.1 — Bagna biome + village hub (rest, trade v0, rumor lines)
- US 4.2 — Character creation (Wygnaniec / Zielarka / Najemnik)
- US 4.3 — Morgue files + run history (SQLite), `--ascii`, config file
- ~~US 4.4~~ — **DONE** docs polish (screenshot, CONTENT/NARRATION/ARCHITECTURE), CoC, issue templates. **Publish step awaits Prestarius: create GitHub repo + push. (No PyPI release — decided 2026-08-15.)**
- ~~US 4.5~~ — **DONE** (2026-08-15): AGPL-3.0 `LICENSE`, CC-BY-SA 4.0 `data/LICENSE`, `CLA.md`, CONTRIBUTING flow

## Epic 5 — M4: Polski — **DONE 2026-08-15 (v0.4-m4)**

- US 5.1 — PL narration packs authored natively; case-resolution exercised for real
- US 5.2 — `--lang pl` + UI catalog PL
- US 5.3 — Blog post: grammar-aware narration engine for Polish

## Epic 6 — M5: AI Narrator (optional) — **DONE 2026-08-15 (v0.5-m5)**

- ~~US 6.1~~ — `LLMNarrator` behind `--narrator llm` (Ollama-first, OpenRouter alternative; timeout → template fallback; cosmetic-only contract)
- ~~US 6.2~~ — Style-guide prompt + per-run latency/fallback stats; comparison blog skeleton awaiting LLM captures (`docs/blog/ai-narrator-comparison.md`)

## Epic 7 — M6: Powroty (meta-progression) — **DONE 2026-08-15 (v0.6-m6)** *(spec: `WYRAJ_M6_POWROTY.md`)*

All nine stories landed on `feat/m6-powroty`. Meta path is `~/.wyraj/meta.yml` (WYRAJ_HOME-aware) rather than XDG, matching existing persistence. Deferred per decisions: item wear dormant, gambling → M7, depth shrines, curse-cleansing UI.

- US 7.1 — Meta-persistence layer: versioned `meta.yml` (pydantic), HMAC tamper flag (`edited: true`, no punishment), unknown-field preservation, migrations, atomic writes, `MetaTransaction` events
- US 7.2 — Economy core: denary + trophy drop tables (lore-gated: beasts drop trophies, coins need a narrative excuse), buy/sell replacing barter v0, `data/economy/*` knobs
- US 7.3 — Skrzynia stash: single village chest, deposit/withdraw at chest only, body loss absolute, 4→10 slot upgrades, `memory_tag` heirloom narration (item wear dormant per decision #7)
- US 7.4 — Death integration: achievement counters, death-screen unlock announcements, morgue meta summary
- US 7.5 — Dziad wandering merchant: pity-guaranteed depth spawns, cruel prices, tiered stock, persistent reputation + recognition narration
- US 7.6 — Crane flight: żurawie pióro, 6-turn interruptible channel (no-LOS gate), znamię return mark, żerdź perch, shaft tiles in kurhany procgen, `crane.yml` packs (EN+PL)
- US 7.7 — Shrines & offerings: Perun/Weles, run-scoped blessings only, curse cleansing hook
- US 7.8 — Codex persistence (unknown→glimpsed→partial→full) + achievement-gated origin unlocks (Strzygobójca, Dziadowy Uczeń)
- US 7.9 — Balance pass: 50-run shared-meta headless sim; DoD: stash value plateaus, currency in/out within 20% per depth band, golden green with meta fixture

## Epic 8 — Próg: intro & onboarding — **DONE 2026-08-15 (v0.7-prog)** *(spec: `WYRAJ_PROG_SPEC.md`)*

- US 8.1 — Title screen: figlet WYRAJ, drifting crane glyphs (decision #13: prototype), rotating tagline, menu (New Journey / Continue / Codex / Morgue / Options / Quit), seeded start hidden in Options
- US 8.2 — Prologue: paged typewriter prose (skippable always, no first-run confirm per decision #12), origin-variant final pages, EN+PL authored natively, seen-flag in meta
- US 8.3 — Arrival + Szept: diegetic first-encounter whispers (fired once per profile, persisted in meta), forest-edge consent moment, hints on/off with auto-quiet
- US 8.4 — Help screen (`?`) in-voice reference; Pilot smoke tests; cut

Deviation note: intro content lives under `data/intro/{en,pl}/` rather than `data/narration/` — the narration dir is reserved for grammar packs, whose loader globs every `*.yml` there.

## Epic 9 — Szlif: UI polish & death flow — **DONE 2026-08-15**

- US 9.1 — Modal input fixes: Esc actually closes skrzynia/inventory/trade/shrine (their `on_key` called `event.stop()` before the Escape binding could fire); inventory no longer crashes on carried trophies; trinket/trophy letters keep the dialog open; DeathScreen made modal so app keys stop leaking through it
- US 9.2 — Visual pass: panel border titles (live place / origin / "The Tale"), modals as lit panels over the dimmed game (the `Middle`/`Center` wrappers had to go — full-screen containers block Textual's screen-through compositing), biome-tinted floors, damage flash on `@`, themed footer + scrollbar, narration pane at 40% height (min 12)
- US 9.3 — Narration presentation: cosmetic `NarrationLine.category` (combat/lore/loot/ambient, dominant family tints the paragraph), blank line between turn paragraphs; golden transcript byte-identical
- US 9.4 — Death & quit flow: death screen offers `n` new run / `m` main screen / `q` quit; `WyrajApp` exits a typed outcome and the entrypoint loops (a pinned `--seed` stays pinned on restart); mid-run `q` asks before abandoning

---

## Epic 10 — M7 "Sylwetka": character pane & quickslots — **DONE 2026-08-16** — spec `WYRAJ_M7_SYLWETKA.md`

Goal: the right-hand pane becomes the portrait of a soul in trouble — layered state-reactive
portrait, equipment paper-doll, status row, quickslots `1–4`. Feature branch `feat/m7-sylwetka`;
each story keeps `main` playable. Everything the pane shows is a projection of ECS state.

### US 10.1 — Portrait compositor (spec §2, §7.1) — **DONE 2026-08-16**
- 10.1.1 — Art moves to `data/portrait/{box,half,ascii}.yml`, pydantic-validated in `content/portrait.py`; all styles implement the same layer contract
- 10.1.2 — Pure compositor `(PortraitState, art) → Text`: base figure (per-origin + hunched posture variant) → equipment overlays (weapon marks, armor outline, gromnica halo wash) → wound decals (4 bands: healthy / bloodied <2/3 / wounded <1/3 / dying <10%) → status decals (each with a non-color mark, spec §6.1) → blizna scar marks
- 10.1.3 — `CharacterPanel` renders via the compositor from ECS (`Wielding`/`Wearing`/`LightSource`/`StatusEffects`); `--ascii` selects the ascii art
- **Verify:** matrix test (styles × bands × statuses × scars) renders; monochrome (plain-text) outputs stay pairwise distinguishable; ascii output is pure ASCII.

### US 10.2 — Equipment paper-doll (spec §3) — **DONE 2026-08-16**
- Six slots (head/torso/weapon/offhand/amulet/feet): core components + equip rules (offhand = shield xor light source), pane rows with enchant/curse coding (+ redundant glyph), gromnica burn turns, `e`/Tab unequip-swap flow
- **Verify:** pilot equips/swaps keyboard-only; core tests for slot rules.

### US 10.3 — Status row (spec §4) — **DONE 2026-08-16**
- Pure projection of `StatusEffects` with turn counters, color families + glyphs; overflow → 3 + `+N more`
- **Verify:** fixture renders incl. >4 statuses.

### US 10.4 — Quickslots (spec §5) — **DONE 2026-08-16** (golden transcript unchanged — the scripted walk never binds)
- `core/systems/quickslots.py` bind/use/clear/auto-refill (`quickslots.auto_refill` knob), inventory `1–4` binds, in-game `1–4` uses / `Shift+1–4` clears; `QuickslotBound/Cleared/Used/AutoRefilled` events + EN/PL narration rules + fixtures; `QuickslotBar` widget with use-flash; in-run save integration
- **Verify:** pilot bind → use → auto-refill → clear cycle; golden transcript regenerated intentionally.

### US 10.5 — Fabular layer (spec §2.5–6, §6.2; M6 integration) — **DONE 2026-08-16**
- Blizna tracking (survive dying → permanent-for-run scar, narrator notes it once), trophy-belt glyphs, named-weapon epithets (kill-count threshold knob, `data/narration/*/epithets.yml`), heirloom ⟲ markers + dziad recognition
- **Verify:** scripted run reaching dying twice → two blizny on the portrait; epithet earned at threshold shows in pane and log.

### US 10.6 — Morgue death-portrait capture (spec §6.2) — **DONE 2026-08-16**
- Final composited portrait (scars, wounds, gear) written into the morgue file
- **Verify:** scripted death leaves the portrait block in the morgue entry (two-blizna case per spec DoD).

### US 10.7 — Polish pass (spec §7.7, §6.1) — **DONE 2026-08-16 (with recorded cuts)**
- Shipped: short-terminal fallback (4-row mini portrait, filled slots only, no suffixes, quickslots always visible), last-foe mini-line with codex-tier mark, color-blind monochrome checks in the portrait/status/doll test matrix, `--ascii` degradation everywhere
- **Cut, recorded:** Tab focus-cycling (the pane is a single projection widget — `e` + in-pack `1-4` binding already cover keyboard-only flows); enchant/curse color coding (no identification/curse system exists yet); burden indicator (no stamina system exists — the spec's Sta bar is aspirational); quickslot use-flash animation
- **Verify:** pilot suite green; monochrome matrix green.

---

## Planned epics — roadmap `WYRAJ_ROADMAP_M8PLUS.md` (Proposal v0.1)

Outline-level on purpose (spec §12: no early scaffolding) — each gets a full
CC spec and story breakdown when its milestone starts. Recommended order
M8 → M9 → M10 → M11 → M12; M11 may slide earlier (no prerequisites past M0).

- **Epic 11 — M8 "Dno"** (the Bottom) — **DONE 2026-08-16** — spec
  `WYRAJ_M8_DNO.md`, built with all spec defaults (decisions 20–25).
  US 11.1 depth tiers 6–8 (darkness 3/2/1, no sky below 6, DeepDescended);
  US 11.2 authored vault + sługa `lift` behavior + niche respawns;
  US 11.3 lifting meter, phase events, gaze light-inversion (lit = seen,
  dark = hidden, douse-by-reuse), unkillable Wij; US 11.4 salt-consuming
  rite channel → victory, VictoryRecord meta + victory morgue file;
  US 11.5 three epilogues ×2 languages on the prologue renderer, permanent
  title line, ⁂ origin marks; US 11.6 Głębiej toggle (fov −1, +2 spawns,
  +1 loot, +25% prices); US 11.7 competent-bot sim — CI smoke + WYRAJ_SIM=1
  measurement (1/30 wins at cut; floor ≥1 win, ≤50%). Golden byte-identical.
  Follow-ups closed before the merge: `kurhany_deep` loot table (candles,
  salt, road food) for depths 6–7 + dziad tiers lean candles; szept
  side-switch whispers on DeepDescended/WijStirred (outside
  CORE_TRIGGERS so the farewell never waits on them); bespoke sługa
  first-sighting line EN/PL. Sim after: 2/30 wins (7%). The vault
  itself still carries no loot — by design.
- **Epic 12 — M9 "Koło Roku"** (Wheel of the Year) — **DONE 2026-08-16** —
  spec `WYRAJ_M9_KOLO_ROKU.md`, built with all spec defaults (decisions
  26–30). US 12.1 pure clock (240-turn day, 12-day wheel, seeded start;
  boundary events; the one sanctioned golden regeneration — seed 42 turned
  out to be a Gromniczna start); US 12.2 night/mist FOV, rain candle
  drain, storm-doubled Perun favor, deterministic lightning; US 12.3
  sky-read spawn pools (strzyga ×3 at noc, południca at midday only);
  US 12.4 the four festival rituals (half-burn, fern flower, free rest,
  the talkable dead + Peaceful truce); US 12.5 pane calendar line + sky
  tints; US 12.6 first-night szept, docs, sim floor re-verified (2/30).
- **Epic 13 — M10 "Zlecenia"** (Errands) — **DONE 2026-08-16** — spec
  `WYRAJ_M10_ZLECENIA.md`, built with all spec defaults (decisions 31–35).
  US 13.1 errand model & pure seeded assembly (data/errands, 1–3 per run,
  one per giver, silent); US 13.2 Radzim kowal + Bogusz młynarz (golden
  regenerated once — entity-id shift only, the walk bumps no one); US 13.3
  the loop (heard = taken on bump, guaranteed proof at the corpse, fetch
  stamping via hash-seeded RNG, banked rewards + `errand_done`); US 13.4
  `meta.villagers` + rep-gated good shelf + known_face recognition; US 13.5
  fates (patience 3 in `apply_death_to_meta`/victory, three flags with
  spawn/stock/narration consequences, told once ever on the next run's
  first step, morgue lines); US 13.6 codex Zlecenia tab (in-run + meta-only
  title view), gossip escalation variants, docs, sims (dno sim unchanged
  at 2/30; meta sim green). Deviation noted: the cold-forge "arrival line"
  is carried by the fate announcement + gossip variants, not a separate
  arrival rule.
- **Epic 14 — M11 "Głosy"** (Voices): optional-dependency AudioSystem on the
  event bus — ambient beds, sparse SFX, creature voicing at a distance;
  backend choice (pygame.mixer vs miniaudio) to be re-verified at spec time.
- **Epic 15 — M12 "Gusła"** (Folk Magic): data-pack modding — pack manifest,
  merge semantics, `--validate-pack`, example pack; data only, no scripting.

Parked (not epics): release engineering & public reach, screen-reader deep
pass, actual music, Steam, overworld travel (open decision #3 — revisit
after M10).

---

## Open decisions blocking future work (spec §13)

| # | Decision | Needed by | Spec recommendation |
|---|---|---|---|
| 2 | ~~License~~ — **RESOLVED 2026-08-14: AGPL-3.0 (code) + CC-BY-SA (data), with CLA** (US 4.5) | M3 publish | — |
| 3 | Overworld vs pure descent | post-M5 | **still open** — descent + hub shipped |
| 4 | Fear/mood | — | shipped as a status effect (bies) + narration tags; no separate meter |
| 6 | M6: feather consumed on interrupted channel? | US 7.6 | spec default: consumed (harsh) |
| 7 | M6: heirloom item wear/curse risk | US 7.3 | spec default: dormant (`meta.item_wear: false`) |
| 8 | M6: dziad gambling minigame | US 7.5 | spec default: defer (flag off) — likely M7 |
| 9 | M6: currency name | US 7.2 | spec default: denary (single tier) |
| 10 | M6: dziad unkillable hand-wave | US 7.5 | spec default: yes for v1 |
| 11 | Próg: prologue prose keep/edit | US 8.2 | implemented as drafted — awaiting Prestarius's read |
| 12 | Próg: confirm Esc-skip on first run | US 8.2 | **no** (spec lean; respect the player) |
| 13 | Próg: drifting bird glyphs | US 8.1 | prototyped in — judge by feel |
| 14 | Próg: szept in-log vs hint bar | US 8.3 | in-log dim italics (spec assumption) |
| 5 | Portrait art direction | US 2.6 | **prototyped in M1** — compare **RESOLVED 2026-08-15: box-drawing wins** — box is the default (`--portrait half` remains as an option); YAML layer files are a later cleanup |
| 15 | M7: offhand shield xor light — or belt-hung gromnica (weaker radius)? | US 10.2 | spec default: strict xor |
| 16 | M7: quickslot auto-refill default | US 10.4 | spec default: on (`quickslots.auto_refill: true`) |
| 17 | M7: named-weapon threshold + any mechanical bonus? | US 10.5 | default 7 kills, pure flavor |
| 18 | M7: death portrait — ASCII capture only, or also PNG export? | US 10.6 | ASCII only for v1 |
| 19 | M7: cross-run quickslot preferences (M6 meta) | post-M7 | per-run binding is part of the ritual |
| 20 | M8: antagonist — the Wij? | US 11.2 | spec default: Wij (his gaze inverts the light economy) |
| 21 | M8: rite consumes sól święcona at channel start? | US 11.4 | spec default: yes (feather doctrine) |
| 22 | M8: new creatures — sługa only, or +1 ambient horror? | US 11.2 | spec default: sługa only |
| 23 | M8: Głębiej stacking across victories | US 11.6 | spec default: single tier v1 |
| 24 | M8: 10–20% skilled win-rate target | US 11.7 | spec default: accept |
| 25 | M8: three epilogues or two? | US 11.5 | spec default: three |
| 26 | M9: 240-turn day, 12-day wheel | US 12.1 | spec default: accept |
| 27 | M9: południca as the one new creature | US 12.3 | spec default: yes |
| 28 | M9: kwiat paproci = full heal | US 12.4 | spec default: full heal |
| 29 | M9: time passes underground | US 12.1 | spec default: yes (folkloric) |
| 30 | M9: sanction one golden regeneration | US 12.1 | spec default: yes (calendar events force it) |
| 31 | M10: new villagers — Radzim kowal + Bogusz młynarz | US 13.2 | spec default: both, these names |
| 32 | M10: acceptance model — heard = taken, no accept/decline | US 13.1 | spec default: yes (a word given binds) |
| 33 | M10: patience — ignored runs before a fate resolves | US 13.5 | spec default: 3 |
| 34 | M10: fates irreversible (no redemption errand) | US 13.5 | spec default: irreversible v1 |
| 35 | M10: reward band 40–90 denary; golden regen only if walk bumps a villager | US 13.3/13.6 | spec default: accept |
