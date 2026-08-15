# WYRAJ — M6 "POWROTY" (Returns) — Meta-Progression Specification

> **Status:** Draft v0.1 — addendum to `WYRAJ_PROJECT.md`, standalone file (main spec is
> under active CC execution — do not modify it; merge this as M6 only after M5 lands)
> **Prerequisite:** M0–M5 complete and stable
> **Theme:** Wyraj is the place souls *return from*. Meta-progression is not a gamey
> bolt-on — it is the mythology. What was carried to Wyraj comes back with the next soul.

---

## 1. Design Intent

Add **light roguelite meta-progression** on top of honored permadeath:

1. **Stash persistence** — items deliberately secured in the village survive death;
   everything on the body is lost.
2. **Economy** — currency + trophy drops, spent at merchants, shrines, stash upgrades.
3. **The wandering merchant (dziad)** — persistent, uncanny, remembers you across runs.
4. **Return travel (crane flight)** — costly, interruptible teleport to village and back.
5. **Knowledge persistence** — bestiary codex survives death.
6. **Origin unlocks** — achievement-gated, never purchased.

**Balance doctrine:** carry-over must feel like *heirlooms, not a savings account*.
Persisted power stays modest; the tension of a single run is sacred. Every mechanic
below has a knob explicitly marked TUNING KNOB.

**Pillar compliance:** determinism (pillar 3) preserved — meta-state is an *input* to a
run, loaded at run start and immutable during the run except through defined
transactions (stash deposit, purchase, shrine offering). Same seed + same meta-state +
same inputs = same run.

---

## 2. Persistence Architecture

Three cleanly separated layers (extends `persistence/`):

| Layer | Format | Lifetime | Content |
|---|---|---|---|
| In-run save | gzip JSON (existing) | Deleted on death — permadeath honored | Full world state, single slot |
| **Meta-state** | **YAML** (`~/.local/share/wyraj/meta.yml`, XDG-aware) | Forever | Stash, currency, dziad memory, codex, unlocks, achievement counters |
| Run history | SQLite (existing) | Forever | Morgue records, stats, per-run summaries |

### 2.1 `meta.yml` schema (pydantic-validated, versioned)

```yaml
schema_version: 1
checksum: "<hmac-sha256 of canonical payload>"   # anti-tamper, see 2.2
currency:
  denary: 148
stash:
  slots_total: 4          # upgradeable, see 3.2
  items:
    - item_id: "miecz_zerdzawy"
      instance: { enchant: 1, curse_risk: 0.1, memory_tag: "run_0042" }
dziad:
  reputation: 3
  met_count: 7
  unlocked_stock_tiers: [1, 2]
codex:
  known: { bies: full, strzyga: partial, utopiec: full }
unlocks:
  origins: [wygnaniec, zielarka, najemnik, strzygobojca]
achievements:
  strzyga_deaths: 3
  deepest_level: 9
```

### 2.2 Tamper policy

- YAML is deliberately human-readable and editable — **modding/self-cheating is a
  feature** in a single-player OSS game.
- `checksum` (HMAC over canonical dump, key = fixed app constant) verified on load. On
  mismatch: game loads normally but flags the profile `edited: true`; morgue files and
  any future leaderboard exports mark it. No punishment, just honesty.
- Unknown fields preserved on rewrite (forward compat); `schema_version` migrations in
  `persistence/meta_migrations.py`.

### 2.3 Transaction model

- Meta-state mutations happen **only** at defined points: village interactions (stash,
  shop, shrine), dziad interactions, codex discovery events, death (counters), run end.
- Each mutation = a `MetaTransaction` event through the existing bus → narration can
  react ("The skrzynia's iron lid falls shut. Whatever happens now, this is safe.").
- Write-on-transaction with atomic replace (tmp file + rename); never write mid-combat.

---

## 3. Stash — the Skrzynia

### 3.1 Rules (the chosen gate)

- A single **skrzynia** (iron-bound chest) in the village. Items inside persist across
  deaths.
- **Everything on the body is lost on death. No exceptions.** Equipped, carried, quest
  items — gone. This is the push-your-luck engine: *"do I walk this sword back to the
  village now, or push one more level?"*
- Deposits/withdrawals only while standing at the skrzynia. No remote access, ever (the
  crane flight exists precisely to make the trip a costed decision, §6).
- Stack rules: consumables stack in one slot up to item-defined stack size; equipment
  is one slot each.

### 3.2 Slots & upgrades (money sink #1)

- Start: **4 slots**. Village upgrades: 4 → 6 → 8 → 10 (steeply super-linear cost
  curve; TUNING KNOB `stash.upgrade_costs`). Hard cap 10. Scarcity is the point —
  choosing *what deserves a slot* is a real decision.

### 3.3 Item memory (flavor + soft balance)

- Persisted items gain `memory_tag` (run of origin). Narrator uses it on first wield in
  a new run: "The blade remembers a hand that is no longer yours."
- OPTIONAL (off by default, `meta.item_wear: false`): each death an item survives in
  the stash adds small `curse_risk`; on withdrawal, roll — cursed variants get a
  folklore twist, removable at shrines. Ship the hook, tune later.

---

## 4. Economy

### 4.1 Currency & trophies

- Currency: **denary** (silver coins). Dropped by humanoids, found in kurhany burial
  hoards, hidden caches.
- Beasts and spirits do **not** drop coins — they drop **trophies**: pelts (*kuny* —
  historically pelts *were* proto-currency), fangs, wax, herbs. Sellable to merchants.
  Bestiary codex gains a "trophy/value" line.
- Lore rule for drop tables: coins on non-humanoids need a narrative excuse (utopiec:
  coins *from the drowned it pulled under* — narration handles it).
- Data-driven: `data/economy/drops.yml`, `data/economy/prices.yml` (sell ≈ 30–40% of
  buy — TUNING KNOB).

### 4.2 Money sinks (mandatory — coins must not pile up)

1. Stash slot upgrades (§3.2)
2. Village shop & dziad purchases (§5)
3. Shrine offerings (§7)
4. Crane feathers (§6)
5. Curse cleansing at shrines
6. OPTIONAL: dziad gambling (§5.4)

### 4.3 What money must NEVER buy

Origins/unlocks (achievement-gated only), codex entries, XP/levels, resurrection.
Meta-power stays earned or modest.

---

## 5. Merchants

### 5.1 Village shop (baseline)

- Static merchant in the village hub (extends M3 "trade v0"): weapons, armor,
  potions/odwary, scrolls/modlitwy, food, gromnice, crane feathers (limited stock).
- Inventory refreshes per run start from tiered tables (`data/economy/shop_village.yml`).

### 5.2 The dziad — wandering merchant in the depths

- A **wędrowny dziad**: uncanny old peddler encountered *below*, always already there,
  deeper than any living man should be. Never explained.
- **Spawning:** eligible from dungeon level 3; on each eligible level, spawn chance 60%
  if not yet seen this run, with **pity guarantee by level 5**; after first encounter
  in a run, re-eligible every 2 levels at 40%. (TUNING KNOBS: `dziad.first_eligible`,
  `dziad.base_chance`, `dziad.pity_level`, `dziad.repeat_interval`.) Finding him must
  stay an *event*, not a schedule.
- **Stock:** things the village never carries, at cruel prices (1.5–2.5× village
  equivalents; TUNING KNOB). Depth-scaled tiers; higher tiers unlock via reputation.
- Non-hostile and unkillable in v1 (attacking him: he is simply *not there anymore*;
  reputation −2; narration goes appropriately cold).

### 5.3 Dziad memory (persistent — the face of meta-progression)

- Lives in `meta.yml → dziad`. Reputation +1 per run in which the player traded with
  him (cap +1/run), −2 for aggression.
- Effects: small discount tiers, stock tier unlocks, and — most importantly —
  **narration**: first meeting of a new run at rep ≥ 3: "You again. Or... no. Someone
  *like* you." He recognizes stash heirlooms on your belt. He is the one NPC who seems
  to know what Wyraj does to souls.

### 5.4 OPTIONAL: gambling (three shells)

- Kubki/shells minigame with the dziad, small stakes, *rigged* (win ~35%; narration
  hints at the cheat if a perception-adjacent stat is high). Pure money sink +
  character. Flag `features.gambling`, off by default until balanced.

---

## 6. Crane Flight — return travel ("klucz żurawi")

### 6.1 Concept

Birds are what travel between this world and Wyraj. The player does not "teleport" —
they are **carried by a wedge of cranes**. Vehicle item: **żurawie pióro** (crane
feather), consumable.

### 6.2 Mechanics

- **Outbound:** using a feather begins a **summoning channel of 6 turns** (TUNING KNOB
  `crane.channel_turns`). Any damage interrupts and **consumes the feather anyway**
  (harsh but keeps it non-escape; TUNING KNOB `crane.consume_on_interrupt`). On
  completion: carried to the village; a **znamię** (mark) entity is left on the
  departure tile.
- **Return:** standing on the village **żerdź (perch) tile** flies you back to the
  znamię **free within the same run** (the feather covered the round trip). Znamię
  expires on death or run end. Only one znamię may exist; a second feather elsewhere
  moves it.
- **NOT an escape tool:** channel is long, interruptible, and cannot start while any
  hostile has LOS ("The cranes will not descend while something watches."). The
  feather saves the long walk, not your life.
- **Sky rule:** flight requires open sky. Surface biomes (puszcza, bagna): usable
  anywhere. **Kurhany crypts: only on shaft tiles** — procgen guarantees 1–2
  collapsed-ceiling shafts per crypt level (doubling as light wells and ambush
  setpieces). Depth remains meaningfully far from home.
- **Economy:** feathers expensive and scarce — village stocks 0–1 per run, dziad 1–2 at
  depth prices (TUNING KNOBS). No monster drops; rare find in nests/hoards.

### 6.3 Events & narration

New events: `CraneSummonStarted/Interrupted/Completed`, `ZnamiePlaced/Expired`,
`CraneReturn`. A narration showcase — the wedge circling down through shaft light, the
world small below, the dziad's knowing look if nearby. Pack: `narration/en/crane.yml`.

---

## 7. Shrines & Offerings (money sink + ritual texture)

- Village shrine pair: **Perun** (storm/order) and **Weles** (underworld/wealth —
  thematically *the* god for this game). Depth shrines rarely at uroczyska.
- **Offerings (denary or trophies):** grant **run-scoped** blessings only (never
  persistent): Perun — combat-leaning (first-strike bonus vs. night creatures);
  Weles — wealth/underworld-leaning (better drop rolls, calm animals). Modest numbers;
  table `data/economy/offerings.yml` (TUNING KNOB).
- **Curse cleansing** for stash heirlooms (§3.3) happens here, for a price.
- Offering at one god slightly disfavors the other within the run (flavor stat,
  narration-only in v1).

---

## 8. Knowledge & Unlock Persistence

### 8.1 Bestiary codex (pure win, zero balance risk)

- Knowledge tiers per monster: `unknown → glimpsed → partial → full` (kill count /
  examine / lore-item thresholds). Persists in `meta.yml → codex`.
- Full entries reveal trophy value, a mechanical weakness hint line, and the full
  folklore write-up. The codex becomes the player's growing *scholarly work across all
  their deaths* — the most Wyraj feature possible.

### 8.2 Origin unlocks (achievement-gated)

- Base three origins (M3) always available. New origins unlock via deeds in
  `meta.yml → achievements`, e.g.:
  - **Strzygobójca** — die to a strzyga 3 times (unlock via *failure* — very roguelike).
  - **Dziadowy Uczeń** — reach dziad reputation 5.
  - **Wodnik** — placeholder, define with content.
- Unlocks announced on the death screen ("Something of you remains...") — turning
  deaths into progress moments.

---

## 9. Explicitly Out of Scope for M6

Town-building, crafting trees, daily challenges, NPC questlines beyond dziad/shrine
interactions, multiplayer/leaderboards (checksum groundwork only). Different, bigger
games.

---

## 10. Implementation Order (CC execution plan)

Each step keeps `main` playable; feature branch `feat/m6-powroty`.

1. **Meta-persistence layer** — `meta.yml` schema (pydantic), load/validate/migrate,
   HMAC, atomic writes, `MetaTransaction` events. Headless tests: corrupt file, unknown
   fields, migration, tamper flag.
2. **Economy core** — denary component, drop tables, trophy items, sell/buy flows on
   existing village trade. Golden-run update.
3. **Skrzynia** — stash UI (Textual modal), deposit/withdraw transactions, slot
   upgrades, `memory_tag` + first-wield narration.
4. **Death integration** — body loss (already true), achievement counters, death-screen
   unlock announcements, morgue file gains meta summary.
5. **Dziad** — spawn logic (chances/pity), shop tiers, reputation persistence,
   recognition narration pack.
6. **Crane flight** — feather item, new `ChannelSystem` in core, znamię entity, LOS
   gate, shaft tiles in kurhany procgen, `crane.yml` pack.
7. **Shrines & offerings** — offering transactions, run-scoped blessing statuses,
   curse cleansing.
8. **Codex persistence + origin unlocks** — knowledge tiers, unlock rules, codex UI.
9. **Balance pass** — headless sims: coins earned vs. sunk per depth band; assert no
   runaway accumulation across 50 sequential simulated runs sharing meta-state.

**Definition of done:** 50-run headless simulation with shared meta-state shows
(a) median stash value plateaus (heirlooms, not savings account), (b) currency
inflow/outflow within 20% balance per depth band, (c) all golden-run tests green with
meta-state as a fixed fixture input.

## 11. Open Decisions (for Prestarius)

1. Feather consumed on interrupted channel — harsh (spec default) or refunded?
2. Item wear/curse-risk on heirlooms (§3.3) — enable at M6 or leave dormant?
3. Gambling minigame — M6 scope or M7?
4. Currency name final? (Alternative: denary/grzywny two-tier.)
5. Dziad unkillable hand-wave OK for v1, or does he need a (terrible) consequence path?
