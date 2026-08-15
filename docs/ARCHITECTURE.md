# Wyraj — Architecture

Living document; mirrors `WYRAJ_PROJECT.md` §4 (plus the M6 and Próg
addenda) and tracks reality as of v0.7.

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
│ bagna │     │ │ locale catalogs, intro (title/prologue/szept) │
│ kurhany     │ └───────────────────────────────────────────────┘
└─────────────┘
┌───────────────────────────────────────────────────────────────┐
│  Persistence: run save (gzip JSON, single slot, consumed)     │
│  meta.yml (survives death) │ history.db │ morgue/ │ config.yml│
└───────────────────────────────────────────────────────────────┘
```

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
  consumed on load, deleted on death (permadeath honored).
- Morgue: text file per death; history: SQLite (`wyraj --history`).
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
  and help.
