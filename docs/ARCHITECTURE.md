# Wyraj — Architecture

Living document; mirrors `WYRAJ_PROJECT.md` §4 (plus the M6, Próg, and
M7 "Sylwetka" addenda) and tracks reality as of v0.8.

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│                      TUI Layer (Textual)                      │
│ TitleApp → OriginApp → PrologueApp → WyrajApp                 │
│   MapView │ CharacterPanel │ NarrativeLog │ Modals            │
└───────────────▲──────────────────────────────▲───────────────┘
                │ render state (read-only)      │ NarrationLines / szept
┌───────────────┴───────────────┐  ┌───────────┴───────────────┐
│         Game Core (ECS)       │  │      Narration Engine      │
│  World │ Systems │ Components │─▶│ enrich → buffer → flush    │
│  TurnScheduler │ RNG streams  │  │ TemplateNarrator (default) │
│  Meta transactions            │  │ LLMNarrator (optional)     │
└───────▲───────────▲───────────┘  │ SzeptSystem (hints)        │
        │           │              └────────────────────────────┘
┌───────┴─────┐ ┌───┴──────────────────────────────────────────┐
│  Procgen    │ │  Content (data/)                              │
│ village │   │ │ bestiary, items, hooks, loot, economy,        │
│ forest │    │ │ origins, narration packs (en/pl),             │
│ bagna │     │ │ locale catalogs, intro (title/prologue/szept),│
│ kurhany     │ │ portrait art (box/half/ascii), epithets       │
└─────────────┘ └───────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────┐
│  Persistence: run save (gzip JSON, single slot, consumed)     │
│  meta.yml (survives death) │ history.db │ morgue/ │ config.yml│
└───────────────────────────────────────────────────────────────┘
```

The TUI stages run as sequential Textual apps. `WyrajApp` exits with a
typed outcome — `"quit"`, `"restart"` (the death screen's "set out
again": a fresh run, same origin, new seed — or the same seed when
`--seed` pinned it), or `"title"` (back to the title screen) — and the
entrypoint in `app.py` loops on it.

**Golden rules**

- `core/` has zero imports from `ui/`. Core emits typed `GameEvent`s
  (frozen dataclasses carrying facts, never text); UI, narration, and
  szept subscribe to the `EventBus`.
- Deterministic core: same seed + same meta-state + same inputs = same
  run. Four named `random.Random` streams (`worldgen`, `combat`, `loot`,
  `narration`) derive from the master seed via SHA-256; per-level
  generation is a pure function of `sha256(seed, depth)`. Wall-clock time
  never touches core; narration variety cannot perturb gameplay.
- Data-driven content: everything nameable lives in YAML under `data/`,
  validated by pydantic models in `content/`.

## The world

A fixed vertical chain, generated lazily but deterministically:

| depth | biome    | generator            | notes                                  |
|------:|----------|----------------------|----------------------------------------|
| 0     | wieś     | authored template    | safe; NPCs, trade, rest, skrzynia, żerdź, shrines |
| 1     | puszcza  | cellular automata    | forest, barrow entrance                |
| 2     | bagna    | moisture random-walk | water pools; utopce swim               |
| 3–5   | kurhany  | BSP rooms+corridors  | dark (FOV 4 unless lit); 1–2 sky shafts |
| 6     | kurhany  | BSP rooms+corridors  | unlit FOV 3; the last sky shafts (last crane exit) |
| 7     | kurhany  | BSP rooms+corridors  | unlit FOV 2; no open sky — no way home but through |
| 8     | dno      | authored vault       | unlit FOV 1; the Wij's hall (M8) — cradle, niches, pillars |

Entities carry `OnLevel(depth)`; systems filter by the current depth and
off-level actors are frozen. The wandering dziad may spawn on crypt
levels (pity-guaranteed by the deepest).

## Turn loop

`Game.step(action)` executes one player action (crane channels tick here
too), updates FOV/discovery, ticks statuses and hunger, then runs every
other due actor (energy/speed scheduler; ties break by entity id). The
round closes with `TurnEnded`, which flushes the narration TurnComposer.

## Narration pipeline

```
GameEvent ──enrich(context tags)──▶ buffer ──TurnEnded──▶ compose_turn ──▶ NarrativeLog
```

- `ContextEnricher` tags events at capture: HP bands, darkness, unseen
  attackers, recency ("again").
- `TemplateNarrator` picks weighted variants from per-language YAML
  grammar packs (EN and natively authored PL with full rule parity),
  resolving grammar-aware slots through per-noun form tables — Polish
  cases work; English articles work; one engine, zero language logic.
- `LLMNarrator` (opt-in) wraps the template narrator: the deterministic
  paragraph plus raw facts go to a local Ollama / OpenRouter model that
  may only rephrase; timeout or any error falls back to the template.
- `SzeptSystem` is a separate thin subscriber emitting one-time
  first-encounter hints (persisted per profile in meta), styled apart
  from prose and never modal.
- Presentation only: each `NarrationLine` carries a cosmetic `category`
  (combat/lore/loot/ambient — the turn's dominant event family) that the
  log uses to tint the paragraph. It never feeds back into gameplay or
  the transcript text.

## Character pane (M7 "Sylwetka")

The right-hand panel is a *projection of ECS state* — no widget owns
game data. Its pieces are pure text builders, each unit-testable without
a running Textual app:

- **Portrait compositor** (`ui/portrait.py`): `PortraitState` (built
  from components by `portrait_state_for(game)`) × per-style art from
  `data/portrait/{box,half,ascii}.yml` → rich `Text`. Layer order per
  spec §2: base figure (hunched posture at wounded/dying, per-origin
  variants supported) → equipment overlays (weapon marks, armor
  outline, gromnica halo wash) → wound decals over four HP bands
  (dying < 10%) → status decals → blizna scars → trophy belt. Every
  color-coded state also carries a non-color mark (color-blind rule);
  the test matrix asserts monochrome renders stay distinguishable. A
  4-row `mini` base variant serves short terminals.
- **Paper-doll** (`ui/paper_doll.py`): six slots — weapon (`Wielding`),
  torso (`Wearing`), head/amulet/feet (`WornExtras`, fed by
  `ItemDef.slot`), offhand (the lit gromnica with burn turns from
  `LightSource`). Heirlooms wear the ⟲ rune; named weapons show their
  epithet. `e` opens `EquipScreen`; `UnequipSlot` frees a slot and
  publishes `ItemUnequipped`. `protection_of` sums all worn armor.
- **Quickslots** (`core/systems/quickslots.py`): the `Quickslots`
  component binds *item keys*, not entities — stack counts are derived,
  auto-refill is inherent, and the `quickslots.auto_refill: false`
  config knob makes an emptied slot unbind instead. Bind in the pack
  (`1-4` then a letter), use on `1-4` (an empty press costs no turn),
  `Shift+1-4` clears. Events: `QuickslotBound/Cleared/Used/Refilled`.
- **Fabular state on `Game`**: `blizny` (a dip under 10% HP survived →
  scar + `BliznaEarned`, narrated once), `weapon_kills` tallies per
  (weapon, species) — seven kills earn an `Epithet` component and
  `WeaponNamed`; the dziad greets a named weapon once per run
  (`WeaponRecognized`); epithets survive the skrzynia via the stash
  instance dict. All of it rides the run save.
- **Morgue capture**: `write_morgue` embeds the final composited
  portrait — the file shows who you were at the end.

## Time (M9 "Koło Roku")

`core/calendar.py` is stateless: day phase, wheel day, festival, weather,
and storm lightning are pure functions of `(seed, turn)` — nothing saved,
nothing to drift. `Game.step` publishes `PhaseChanged` / `WeatherChanged` /
`FestivalDawned` at boundaries; surface FOV, candle drain, offering bonuses,
and spawn-pool weights *read* the clock rather than being driven by it. The
one new save field is `kupala_bloomed`. This is also why the golden
transcript was regenerated exactly once at M9: a breathing calendar
necessarily enters the event log.

## The ending (M8 "Dno")

The Wij is engine-honest: a lifting meter on `Game`, sługa monsters with a
`lift` behavior (they path to the cradle and channel; niches respawn them),
threshold events, and a gaze tick that runs the game's own FOV *from the
cradle* — a lit player in that line takes true damage, an unlit one is part
of the dark. He has no `Health` component; the cradle bump either starts
the salt-consuming rite channel (mirrors the crane channel: `Rite`
component, interrupted by moving or damage) or narrates futility. Sealing
publishes `RiteCompleted`, sets `game.victory`, and the app exits with a
`"victory:<epilogue>"` outcome; the entrypoint plays the epilogue pages on
the prologue renderer and returns to the title. Victory state lives in
`meta.victories` (HMAC-covered like everything else). Głębiej is a
constructor flag with four numeric consequences — no second rule system.

## Meta-progression ("Powroty")

`meta.yml` survives death and mutates only through defined transactions
(banking, stash, purchases, offerings, codex, death), each published as a
`MetaTransaction` and written atomically. HMAC checksum flags hand-edited
profiles (`edited: true`) without punishing them. Contents: banked
denary, the skrzynia stash (with heirloom `memory_tag`s), dziad
reputation/memory, codex knowledge tiers, achievement counters, origin
unlocks, prologue/szept flags. The on-body purse is *not* meta — coins
die with you unless banked or carried home by crane.

## Persistence

- Run save: single gzip-JSON slot, RNG streams restored bit-exactly,
  consumed on load, deleted on death (permadeath honored). Components
  serialize by reflection — new flat dataclasses ride along for free;
  M7 run state (blizny, weapon kill tallies, quickslot bindings) is in.
- Morgue: text file per death, now carrying the death portrait;
  history: SQLite (`wyraj --history`).
- Config: `~/.wyraj/config.yml`, written by the title-screen Options.
- All under `~/.wyraj/` (`WYRAJ_HOME` overrides everything).

## Testing strategy

- Golden run: seed 42 + scripted walk (village → puszcza) → byte-stable
  transcript of all events and narration (`GOLDEN_REGEN=1` to regenerate
  deliberately). Meta enters as a default fixture — proven inert.
- Save/load roundtrip must reproduce the exact gameplay event log.
- 50-run shared-meta economic sim: stash plateaus, currency flattens,
  meta file stays valid and honest through 100 write/read cycles.
- Every grammar pack entry (EN and PL) renders against fixtures; PL must
  cover every EN rule; locale catalogs must not drift.
- FOV symmetry is property-tested; content YAML is schema-validated in
  CI; Textual `Pilot` smoke tests cover the UI including title, prologue,
  help, the equip flow, and the quickslot bind → use → clear cycle.
- Color-blind safety: the portrait/status/paper-doll matrix asserts that
  every band, status, scar, and equipment state stays pairwise
  distinguishable with styles stripped (plain text), in all three art
  styles including `--ascii`.
