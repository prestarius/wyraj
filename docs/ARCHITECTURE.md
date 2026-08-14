# Wyraj — Architecture

Living document; mirrors `WYRAJ_PROJECT.md` §4 and tracks reality.

## Layers

```
┌────────────────────────────────────────────────────────────┐
│                     TUI Layer (Textual)                     │
│   MapView │ CharacterPanel │ NarrativeLog │ Modals/Menus    │
└───────────────▲────────────────────────────▲───────────────┘
                │ render state (read-only)    │ NarrationLines
┌───────────────┴───────────────┐  ┌─────────┴───────────────┐
│         Game Core (ECS)       │  │     Narration Engine     │
│  World │ Systems │ Components │─▶│ enrich → buffer → flush  │
│  TurnScheduler │ RNG streams  │  │ TemplateNarrator (def.)  │
└───────────────▲───────────────┘  └─────────────────────────┘
                │
┌───────────────┴───────────────┐  ┌─────────────────────────┐
│         Procgen               │  │     Content (data/)      │
│  village │ forest │ bagna │   │  │ YAML: bestiary, items,   │
│  kurhany │ population │ loot  │  │ hooks, loot, origins,    │
└───────────────────────────────┘  │ narration packs          │
                                   └─────────────────────────┘
```

**Golden rules**

- `core/` has zero imports from `ui/`. Core emits typed `GameEvent`s
  (frozen dataclasses carrying facts, never text); UI and narration
  subscribe to the `EventBus`.
- Deterministic core: same seed + same inputs = same run. Four named
  `random.Random` streams (`worldgen`, `combat`, `loot`, `narration`)
  derive from the master seed via SHA-256. Wall-clock time never touches
  core; narration variety cannot perturb gameplay.
- Data-driven content: monsters, items, hooks, loot tables, origins, and
  narration templates live in YAML under `data/`, validated by pydantic
  models in `content/`.

## The world

A fixed vertical chain of levels, generated lazily but deterministically
(each level's layout and population is a pure function of
`sha256(master_seed, depth)`):

| depth | biome    | generator            | notes                          |
|------:|----------|----------------------|--------------------------------|
| 0     | wieś     | authored template    | safe; NPCs, trade, rest        |
| 1     | puszcza  | cellular automata    | forest, barrow entrance        |
| 2     | bagna    | moisture random-walk | water pools; utopce swim       |
| 3–5   | kurhany  | BSP rooms+corridors  | dark (FOV 4 unless lit)        |

Entities carry `OnLevel(depth)`; systems filter by the current depth and
off-level actors are frozen (they gain no energy).

## Turn loop

`Game.step(action)` executes one player action, updates FOV/discovery,
ticks statuses and hunger, then runs every other due actor
(energy/speed scheduler, ADOM-style; ties break by entity id). The round
closes with `TurnEnded`, which flushes the narration TurnComposer.

## Narration pipeline

```
GameEvent ──enrich(context tags)──▶ buffer ──TurnEnded──▶ compose_turn ──▶ NarrativeLog
```

- `ContextEnricher` tags events at capture time: HP bands, darkness,
  unseen attackers, recency ("again").
- `TemplateNarrator` picks weighted variants from YAML grammar packs,
  preferring variants whose `tags` match the context; per-rule
  anti-repetition; string forms resolve grammar-aware slots
  (see `NARRATION.md`).
- One composed paragraph per round; duplicate sentences collapse into
  "And again."

## Persistence

- Save: single gzip-JSON slot (`~/.wyraj/save.json.gz`, `WYRAJ_HOME`
  overrides). Serializes world components, level maps, RNG stream states
  (restored bit-exactly), and meta. Consumed on load; deleted on death.
- Morgue: text file per death under `~/.wyraj/morgue/`.
- History: SQLite `~/.wyraj/history.db` (`wyraj --history`).

## Testing strategy

- Golden run: seed 42 + scripted walk → byte-stable transcript of all
  events and narration (`GOLDEN_REGEN=1` to regenerate deliberately).
- Save/load roundtrip must reproduce the exact gameplay event log.
- Every grammar pack entry renders against fixtures (no unresolved slots).
- FOV symmetry is property-tested; content YAML is schema-validated in CI.
- Textual `Pilot` smoke tests for the UI.
