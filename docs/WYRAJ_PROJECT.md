# WYRAJ — Narrated Roguelike Project Specification

> **Status:** Draft v0.1 — foundation spec for Claude Code execution
> **Author:** Prestarius (concept & architecture) / Claude (spec)
> **Visibility:** Private first → public GitHub release after M3
> **Name:** *WYRAJ* — the Slavic otherworld where souls fly as birds and return in spring; fitting for a permadeath roguelike. Verified Aug 2026: GitHub near-clean (1 unrelated repo), PyPI `wyraj` free. Fallback if ever needed: *Zaswiaty* (0 collisions).

---

## 1. Vision

A **narrated roguelike**: ADOM-class systemic depth (procedural world, permadeath, turn-based tactics, character progression) fused with **rich adventure prose**. Every mechanical event passes through a narration layer that composes contextual, readable story text — the message log is a first-class narrative pane, not an afterthought.

**Setting:** Slavic dark fantasy. No goblins, no orcs. Instead: leszy, strzyga, południca, utopiec, bies, licho, rusałka, wąpierz, żmij. Villages, bagna (marshes), primeval forest (puszcza), pagan uroczyska, burial mounds (kurhany). Tone: folk horror — *The Witcher* short stories meets *Darkwood* meets classic roguelike.

**Differentiators:**

1. **Narration engine** — mechanical facts → flowing prose, context-aware (health, light, mood, history, biome).
2. **Slavic bestiary and folklore** as core content identity, not reskin.
3. **Rich TUI presentation** — colored Unicode map with fog-of-war/lighting, character portrait panel reflecting state (wounds, equipment, statuses).
4. **Bilingual by design** — English first, Polish as a first-class localization target (architecture must not block it).
5. **Optional AI narrator mode** — pluggable narrator interface; deterministic template engine by default, local LLM (Ollama) as opt-in garnish. The game must be fully playable offline with zero AI.

---

## 2. Design Pillars (tie-breakers for all decisions)

1. **Read the log like a story.** If a feature doesn't produce interesting narration or interesting decisions, cut it.
2. **Depth before breadth.** One biome that feels alive beats four that feel empty.
3. **Deterministic core.** Same seed + same inputs = same run. Narration variety comes from seeded RNG streams, never from wall-clock randomness. LLM narrator is cosmetic-only and never affects game state.
4. **Data-driven content.** Monsters, items, effects, narration templates live in data files (YAML). Adding content must not require touching engine code.
5. **Ship small, layer forever.** Every milestone is a playable game.

---

## 3. Tech Stack

| Concern | Choice | Rationale |
|---|---|---|
| Language | Python 3.12+ | Prestarius's primary; rapid iteration; Claude Code friendly |
| Package/runner | `uv` (`uv run`, `uv sync`) | Established personal convention |
| TUI framework | **Textual** (latest stable) | Actively maintained, MIT, CSS-like styling, widget system, reactive, testable (`Pilot`); verified Aug 2026 |
| Rendering | Rich (via Textual) | Colors, styles, Unicode |
| Data files | YAML (`ruamel.yaml` or `pyyaml`) | Human-editable content |
| Save format | Compressed JSON (gzip) or `msgpack` | Simple, debuggable |
| Persistence (meta) | SQLite (stdlib) | Run history, morgue files, stats |
| i18n | Custom string-catalog + template system (see §7) | gettext alone can't handle grammar-aware narration |
| Optional LLM | OpenRouter or local Ollama via `httpx` | Pluggable `Narrator` backend |
| Tests | `pytest` + Textual `Pilot` + snapshot tests | Deterministic core makes golden-run tests possible |
| Lint/format | `ruff` (lint + format), `mypy` (strict on `core/`) | Public-repo hygiene from day one |
| CI | GitHub Actions (lint, typecheck, tests, seed-replay regression) | Ready before going public |

**Explicit non-goals for now:** graphics tiles, mouse-driven UI, multiplayer, web build (Textual supports `textual serve` — nice-to-have later, free win).

---

## 4. Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                        TUI Layer (Textual)                  │
│   MapView │ CharacterPanel │ NarrativeLog │ Modals/Menus    │
└───────────────▲────────────────────────────▲───────────────┘
                │ render state (read-only)    │ NarrationEvents
┌───────────────┴───────────────┐  ┌─────────┴───────────────┐
│         Game Core (ECS)       │  │     Narration Engine     │
│  World │ Systems │ Components │─▶│ EventBus → Narrator(s)   │
│  TurnScheduler │ RNG streams  │  │ TemplateNarrator (def.)  │
│                               │  │ LLMNarrator (optional)   │
└───────────────▲───────────────┘  └─────────────────────────┘
                │
┌───────────────┴───────────────┐  ┌─────────────────────────┐
│         Procgen               │  │     Content (data/)      │
│  MapGen per biome │ StoryHooks│  │ YAML: bestiary, items,   │
│  Population │ Loot tables     │  │ effects, narration packs │
└───────────────────────────────┘  └─────────────────────────┘
```

**Golden rule:** `core/` has **zero imports from `ui/`**. Core emits `GameEvent`s; UI and Narration subscribe. The game must be runnable headless (critical for tests, balance sims, and AI-driven playtesting).

### 4.1 ECS Core

Hand-rolled minimal ECS (no heavy framework — `esper` is an option but a small bespoke one is ~200 lines and fully under our control):

- **Entity** = int id.
- **Components** = frozen dataclasses: `Position`, `Renderable`, `Health`, `Melee`, `Inventory`, `AI`, `Player`, `LightSource`, `StatusEffects`, `Lore` (narrative metadata: name forms, epithets, description keys), `Portrait`.
- **Systems** (ordered per turn): `InputSystem → AISystem → MovementSystem → CombatSystem → StatusSystem → HungerSystem → FovSystem → DeathSystem`.
- **TurnScheduler:** energy/speed-based (ADOM-style) — actors accumulate energy, act at threshold. Simple but supports speed differences.

### 4.2 Event Bus & GameEvents

Every mechanically meaningful outcome emits a typed event (frozen dataclass), e.g.:

```python
@dataclass(frozen=True)
class AttackResolved(GameEvent):
    attacker: EntityRef
    defender: EntityRef
    weapon: EntityRef | None
    damage: int
    outcome: Outcome  # HIT / MISS / CRIT / KILL / GRAZE
    defender_hp_frac: float
```

Events carry **facts, not text**. Subscribers: `NarrationEngine`, `UI`, `AudioCueSystem` (future), `RunLogger` (morgue file / replay).

### 4.3 RNG Streams

Separate seeded streams (`numpy` not needed — `random.Random` instances): `worldgen`, `combat`, `loot`, `narration`. Narration variety never perturbs gameplay determinism. Seed shown on death screen; `--seed` CLI flag for replay.

---

## 5. Narration Engine (the star)

### 5.1 Pipeline

```
GameEvent → ContextEnricher → Narrator.compose() → NarrationLine(s) → NarrativeLog
```

**ContextEnricher** attaches situational context the raw event lacks:

- actor/target `Lore` (name forms, epithets), visibility ("something unseen"),
- environment: biome, light level, weather, nearby landmark hooks,
- player state: HP band (healthy/bloodied/dying), active statuses, fear/mood meter,
- recency memory: what was narrated in the last N turns (anti-repetition, callbacks: "the strzyga circles you *again*").

### 5.2 TemplateNarrator (default, deterministic)

- Tracery-style grammar packs in YAML: rules keyed by `(event_type, outcome, context_tags)`.
- Weighted variants selected via the `narration` RNG stream.
- Slot filling with **grammar-aware string forms** (see §7 — this is what makes Polish possible later).
- Tone modifiers: the same `AttackResolved/HIT` renders differently under `ctx.player_dying` or `ctx.darkness`.
- **Coalescing:** batch events from one turn into composed sentences ("You strike; the utopiec shrieks and slips beneath the black water.") — a `TurnComposer` groups events before rendering. This is the single biggest quality lever over classic roguelike logs.

Example pack entry:

```yaml
attack_resolved:
  hit:
    - weight: 3
      en: "Your {weapon.name} bites into the {target.name.def}, tearing {target.pronoun.poss} flesh."
    - weight: 1
      tags: [darkness]
      en: "You swing into the dark and feel the blade catch something wet."
```

### 5.3 LLMNarrator (optional, later milestone)

- Same `Narrator` interface; receives the enriched event batch + a strict style guide + recent log excerpt.
- Hard rules: cosmetic only, bounded latency (async, falls back to templates on timeout), never invents facts not present in events, output length capped.
- Backend configurable: Ollama local / OpenRouter. Off by default.

---

## 6. UI Design (Textual)

Three-pane primary screen + footer keybar:

```
┌ WYRAJ ────────────────────────────────────────────────────────┐
│ ┌ Map (flex) ───────────────┐ ┌ Character ──────────────────┐ │
│ │  colored Unicode tiles     │ │  [portrait: box-drawing/    │ │
│ │  FOV + light falloff       │ │   halfblock art, state-     │ │
│ │  entity glyphs w/ styles   │ │   reactive: wounds, gear]   │ │
│ │  landmark highlights       │ │  HP/Stamina/Hunger bars     │ │
│ │                            │ │  statuses, equipment slots  │ │
│ └────────────────────────────┘ └─────────────────────────────┘ │
│ ┌ Narrative Log (tall, scrollable, Rich-formatted prose) ────┐ │
│ │  Turn-composed paragraphs; important lines styled;         │ │
│ │  auto-scroll; PgUp history                                 │ │
│ └────────────────────────────────────────────────────────────┘ │
│ [h/j/k/l+arrows move] [g get] [i inv] [c character] [? help]   │
└────────────────────────────────────────────────────────────────┘
```

- **Map:** Unicode glyph set with CP437 fallback (`--ascii` flag). Light levels via style dimming; remembered-but-unseen tiles desaturated.
- **Portrait panel:** layered ASCII/halfblock template — base figure + equipment overlays + wound/status decals. Data-driven layers so it evolves with the character. (Stretch: seasonal variants — hood in rain, etc.)
- **Modals:** inventory, character sheet, look/examine (with full `Lore` description — folklore entries as discoverable "bestiary codex").
- Textual CSS themes: default "czarnoles" dark theme; ensure 16-color terminal degradation is acceptable.

---

## 7. Localization Strategy (EN first, PL first-class)

Polish grammar (7 cases, 3 genders, animacy, verb aspect) breaks naive `{name}` templating. Design for it **now**, implement PL **later**:

- Every nameable thing declares a **string form table**, not a single string:

```yaml
strzyga:
  en: { name: "strzyga", plural: "strzygas", article: "a" }
  pl: { mian: "strzyga", dop: "strzygi", cel: "strzydze", bier: "strzygę",
        narz: "strzygą", miej: "strzydze", gender: f }
```

- Template slots request forms: `{target.name.bier}` (accusative) — EN packs simply map all cases to the base form.
- Narration packs are **per-language files**, not translated strings: PL prose is authored natively, not machine-mapped from EN structure.
- UI chrome strings via simple catalog (`locale/en.yml`, `locale/pl.yml`).
- CLI/config: `--lang en|pl`.
- **Milestone rule:** engine supports form tables from M1; PL content authored from M4.

---

## 8. Procgen

- **Biomes (in content order):** Puszcza (primeval forest — cellular automata + tree density noise), Bagna (marsh — moisture map, unsafe tiles, utopce), Kurhany (barrow field — BSP crypts under mounds), Wieś (village hub — semi-authored, quest board later).
- **Story hooks:** generators place narrative seeds — a ransacked chapel of Perun, a dead traveler with a journal fragment, a whisper-tree — as entities with `Lore` + one-shot narration triggers. The narrator weaves them in on discovery.
- **Population & loot:** depth-scaled weighted tables in YAML; ecology constraints (utopce near water, leszy in deep forest).
- Every generator is a pure function of `(seed, depth, biome_params)`.

---

## 9. Repository Layout

```
wyraj/
├── pyproject.toml            # uv-managed; ruff/mypy/pytest config
├── README.md                 # public-facing from day one
├── LICENSE                   # MIT (decide before M3 publish)
├── CHANGELOG.md
├── docs/
│   ├── ARCHITECTURE.md       # living doc, mirrors this spec
│   ├── NARRATION.md          # grammar pack authoring guide
│   └── CONTENT.md            # bestiary/item authoring guide
├── src/wyraj/
│   ├── core/                 # ECS, events, scheduler, rng — NO ui imports
│   │   ├── ecs.py
│   │   ├── events.py
│   │   ├── systems/
│   │   └── rng.py
│   ├── narration/
│   │   ├── engine.py         # bus subscription, ContextEnricher, TurnComposer
│   │   ├── templates.py      # grammar pack loader + renderer
│   │   ├── forms.py          # string-form tables, case resolution
│   │   └── llm.py            # optional backend (stub until M5)
│   ├── procgen/
│   ├── content/              # loaders + validation (pydantic models for YAML)
│   ├── ui/                   # Textual app, screens, widgets, themes (.tcss)
│   ├── persistence/          # saves, morgue, sqlite meta
│   └── app.py                # entrypoint: `uv run wyraj`
├── data/
│   ├── bestiary/*.yml
│   ├── items/*.yml
│   ├── narration/en/*.yml
│   ├── narration/pl/*.yml    # from M4
│   └── locale/{en,pl}.yml
└── tests/
    ├── test_core_*.py
    ├── test_narration_*.py
    ├── golden/               # seed-replay snapshot runs
    └── test_ui_pilot.py
```

---

## 10. Milestones

Each milestone = playable, tagged, demo-able.

### M0 — Walking Skeleton (the brutal minimum)
- Repo scaffold, uv, ruff/mypy/pytest, CI green.
- ECS core + energy scheduler + event bus.
- One cellular-automata forest map, FOV (symmetric shadowcasting), `@` moves.
- One monster (**bies**), melee combat, death screen with seed.
- TemplateNarrator v0: single EN pack, no coalescing yet — but events→narration pipeline fully in place.
- Textual 3-pane layout with static portrait.
- **Definition of done:** `uv run wyraj --seed 42` is a completable-by-dying game; golden-run test replays it.

### M1 — It Reads Like a Story
- ContextEnricher (HP bands, darkness, recency memory) + TurnComposer coalescing.
- String-form tables wired through templates (EN trivial mapping).
- 5 monsters (bies, wilk, utopiec, strzyga, martwiak), 10 items, hunger clock, potions/scrolls-equivalents (folk remedies: odwar, gromnica, sól święcona).
- Examine command + bestiary codex screen.
- Portrait reflects HP band + wielded weapon.

### M2 — Depth & Danger
- Multi-level descent (kurhany crypts), stairs, level persistence in-run.
- Status effects system (bleeding, fear, poison, blessing), lighting/light sources (gromnica as torch-with-meaning).
- Save/load (single save slot, deleted on death — permadeath honored).
- Loot tables, equipment slots, simple AI behaviors (pack wolves, ambusher strzyga, fleeing licho).
- Story hooks v1 (3 hook types per biome).

### M3 — Public Release Cut
- Bagna biome, village hub (rest, trade v0, rumor lines feeding narration).
- Character creation (3 origins: Wygnaniec / Zielarka / Najemnik — mechanical + narrative differences).
- Morgue files, run history (SQLite), `--ascii` fallback, config file.
- Docs polished (README with GIF via `textual` recording, CONTENT.md, NARRATION.md).
- License, CoC, issue templates. **→ publish to GitHub.**

### M4 — Polski
- PL narration packs authored natively; case-resolution engine exercised for real.
- `--lang pl`, UI catalog PL.
- Blog post: "Grammar-aware narration engine for Polish in a roguelike" (this is genuinely novel content).

### M5 — AI Narrator (optional mode)
- `LLMNarrator` behind config flag; Ollama-first, OpenRouter fallback.
- Style-guide prompt, fact-grounding contract, timeout→template fallback, per-run cost/latency stats.
- Comparative screenshots for a second blog post.

---

## 11. Testing & Quality Strategy

- **Golden-run tests:** fixed seed + scripted input → full event log snapshot. Any core change that alters the log must be intentional.
- **Narration tests:** every grammar pack entry rendered against fixture contexts; assert no unresolved slots, no repetition within window.
- **Content validation:** pydantic schemas for all YAML; CI fails on invalid content.
- **Headless sims:** random-walk bot plays N turns per seed batch — crash detection + rough balance stats (deaths per depth).
- **UI:** Textual `Pilot` smoke tests (app boots, keys navigate, modals open).
- mypy strict on `core/` and `narration/`; ruff everywhere.

## 12. Claude Code Execution Notes

- Work milestone by milestone; **do not scaffold future milestones early**.
- After M0, always keep `main` playable; feature branches per system.
- Prefer many small data files over clever engine features (pillar 4).
- When in doubt between mechanics vs. narration quality — narration wins (pillar 1).
- Ask Prestarius before: adding dependencies beyond §3, changing the event schema, altering repo layout.
- Conventional commits; CHANGELOG updated per milestone.

## 13. Open Decisions (for Prestarius)

1. ~~**Final name**~~ — **RESOLVED: Wyraj** (GitHub/PyPI verified Aug 2026). Re-verify + register PyPI name just before M3 publish.
2. **License** — MIT (max reach) vs AGPL (protect against closed forks). Recommendation: MIT for a portfolio flagship.
3. **Overworld or pure descent?** M0–M3 assume descent + village hub; ADOM-style overworld is a post-M5 question.
4. **Fear/mood meter** as a core mechanic (Darkwood-style) or narration-only context? Spec assumes narration-only until M3.
5. **Portrait art direction:** box-drawing line art vs. halfblock "pixel" art. Prototype both in M1.
