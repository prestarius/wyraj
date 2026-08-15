# Authoring Content

All game content is YAML under `data/`, validated by pydantic schemas in
`src/wyraj/content/`. Invalid content fails CI — you cannot ship a broken
monster.

## Bestiary — `data/bestiary/*.yml`

```yaml
strzyga:
  name: "strzyga"
  glyph: "s"              # single char, Unicode ok
  ascii_glyph: "s"        # single char, CP437-safe (--ascii mode)
  style: "red3"           # Rich style/color
  hp: 14
  speed: 110              # energy per tick; 100 = player baseline
  damage: 5
  to_hit: 70              # percent
  behavior: ambush        # approach | pack | ambush | flee | (yours?)
  spawn_weight: 1
  biomes: [puszcza, kurhany]   # wies never spawns monsters
  swims: false            # may cross open water
  prefers_water: false    # spawn placement hugs pools
  attack_status: { kind: bleeding, chance: 40, duration: 4, power: 1 }
  weakness: "Revealed in the codex at tier 'known' — one practical sentence."
  epithets: ["the twice-souled"]
  forms:                  # string-form table, see NARRATION.md
    en: { plural: "strzygi", pronoun_subj: "she", pronoun_obj: "her", pronoun_poss: "her" }
  description: >
    Shown in the examine view and the codex. Write it like folklore,
    not like a stat block.
```

Give every monster a first-sighting line in
`data/narration/en/discovery.yml` under `lore_discovered:` — otherwise it
gets the generic default.

## Items — `data/items/*.yml`

Kinds and their required fields:

- `weapon` — `damage`
- `armor` — `protection` (damage soaked; a fully absorbed hit is a GRAZE)
- `consumable` — `effect` (`heal` | `feed` | `bless` | `light` | `crane`)
  and `power` (HP / satiation / blessing turns / candle turns / channel turns)
- `trinket` — no mechanics, all flavor
- `trophy` — monster drops with no use but a sell price (see economy)

Common fields mirror the bestiary (glyph, style, `forms`, `description`).
`spawn_weight` matters only when a biome has no loot table.

## Loot tables — `data/loot/<biome>.yml`

```yaml
count: 6            # items per level
count_per_depth: 1  # extra per depth level
weights:            # item key → weight; keys must exist in items/
  gromnica: 4
  sol_swiecona: 4
```

## Story hooks — `data/hooks/*.yml`

Discoverable narrative set-pieces, three per biome. Same display fields as
items; `biomes` decides placement. Each hook needs a `lore_discovered`
entry in `data/narration/en/hooks.yml` — that line is the hook's moment,
make it count.

## Origins — `data/origins.yml`

Character creation. `hp`, `to_hit`, `damage`, `satiation`,
`starting_items` (item keys), `intro` (opening narration), `description`
(selection screen), plus `title_pl` / `intro_pl` / `description_pl` for
Polish. Optional `unlock` gates an origin behind deeds:

```yaml
unlock: { type: achievement, key: strzyga_deaths, threshold: 3 }
# or: { type: dziad_reputation, threshold: 5 }
```

Locked origins are hidden at selection and rejected by `--origin`. Money
must never buy them.

## Economy — `data/economy/`

- `drops.yml` — per-monster drops. Lore rule: beasts and spirits drop
  trophies; coins require a narrative excuse (the drowned, the buried).
- `prices.yml` — buy prices, `sell_ratio`, dziad markup/discounts, stash
  upgrade costs. Every number is a tuning knob.
- `shop_village.yml` — guaranteed + chance-rolled trader stock per run.
- `shop_dziad.yml` — spawn chances/pity, reputation-gated stock tiers.
- `offerings.yml` — shrine costs and the run-scoped favors they buy.

## Intro — `data/intro/{en,pl}/`

Title taglines (`title_lines.yml`), the paged prologue with per-origin
final pages (`prologue.yml`), the szept hint table (`szept.yml`), and the
`?` help page (`help.yml`). This directory is *outside* `data/narration/`
on purpose: the narration dir belongs to grammar packs, whose loader
consumes every YAML it finds. Missing PL files fall back to EN per file.

## Checklist for any new content

1. `uv run pytest` — schema validation and narration fixtures must pass.
2. Does it read like folklore someone believes? (Pillar 1: if it doesn't
   narrate well, cut it.)
3. Polish names are welcome and encouraged; add `forms.en` so English
   articles behave, and leave room for `forms.pl` (M4).
