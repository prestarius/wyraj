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

Armor and trinkets may also declare a paper-doll `slot` (M7): armor
defaults to `torso` but can claim `head` or `feet` (baranica, łapcie);
a trinket with `slot: amulet` becomes wearable (szkaplerz). Slotted
items get a `[wear]` verb in the pack and their protection stacks.
Consumables are the only quickslot-bindable kind.

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

## Portrait art — `data/portrait/*.yml`

One file per art style (`box`, `half`, `ascii`), all implementing the
same layer contract so `--portrait` and `--ascii` stay swappable:

```yaml
style: box
base:                    # named figure variants, "default" required
  default: [ ...rows... ]
  hunched: [ ... ]       # used at the wounded/dying HP bands
  mini: [ ...4 rows... ] # short-terminal fallback
  # "<origin>" / "<origin>_hunched" override per origin if present
weapons:                 # item key → patches: [row, col, "char"]
  toporek: [[3, 9, "⊦"], [4, 9, "│"], [5, 9, "│"]]
armor: [[3, 2, "╔"], ...]        # torso outline when armored
wounds: { bloodied: [...], wounded: [...], dying: [...] }
status_marks:            # the NON-COLOR half of each status decal
  poison: [[2, 1, "~"]]
scars: [[1, 5, "╱"], ...]        # first N applied for N blizny
belt: [[6, 1, "▪"], ...]         # trophy-belt marks (max 2 shown)
```

Patches are `[row, col, char]` replacements over the base grid;
out-of-bounds patches are silently skipped (that's how `mini` works).
Color washes (band tint, poison edges, blessing bold, wet lower third,
halo) live in code — art files carry glyphs only. The test matrix
requires every band/status/scar/belt state to stay distinguishable in
monochrome, so give each state a visible mark.

## Epithets — `data/epithets/epithets.yml`

Named-weapon titles (M7 §6.2), one entry per species, both languages in
one file because an epithet is a single identity:

```yaml
wilk: { en: "Wolves' Bane", pl: "Wilcza Zguba" }
```

A weapon that kills seven of one species earns the epithet — but only
if the species has an entry here, and only if the `weapon_named:` rule
for that species exists in the narration packs (the announcement prose
carries the name in each language). Add all three together.

## Errands — `data/errands/*.yml` (M10)

The wieś's asks, 1–3 assembled per run, at most one per giver:

```yaml
syn_mlynarza:
  giver: mlynarz          # villager role
  kind: hunt              # hunt | fetch — no escorts, ever
  target: utopiec         # monster key (hunt) / item key (fetch)
  proof: utopcowa_luska   # hunt only: guaranteed drop while active
  depth: 2
  reward: { denary: 70, reputation: 1 }
  patience: 3             # ignored runs before the fate resolves (0 = none)
  fate: mlyn_pusty        # village flag this failure feeds ("" = rep only)
```

Every errand needs `errand_heard/<key>` and `errand_completed/<key>` rules
in both narration packs — the ask *is* the content. A fate needs its
`village_fate/<flag>` announcement too.

## Audio — `data/audio/` (M11)

`sounds.yml` maps names to files (never globbed): `beds:` per ambient
scene, `events:` keyed by narration rule keys (`attack_resolved/player_kill`),
`voices:` per monster key for distance voicing. Every asset file must have
an entry in `CREDITS.yml` (`file/author/source_url/license` — CC0/CC-BY/
CC-BY-SA only; NC/ND fails CI). The shipped starter set is synthesized by
`tools/gen_sounds.py`; replace files one by one with curated recordings
and update the credits by hand. Sparse is the aesthetic — unmapped events
are silent on purpose.

## Data packs — `examples/pack-pomorski/` (M12)

Everything above can also ship as a third-party pack: a folder shaped
like `data/` plus a `pack.yml` manifest, validated by
`uv run wyraj --validate-pack`. See `docs/MODDING.md` for the merge rules
and the authoring walkthrough — the in-repo example pack is the template.

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
