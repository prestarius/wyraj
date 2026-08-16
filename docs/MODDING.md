# Modding Wyraj — data packs ("Gusła", M12)

A pack is a folder shaped like `data/`, plus a manifest. **Data only,
forever:** packs are YAML and asset files. Wyraj never imports, execs, or
evals anything from a pack directory — a pack can produce bad content,
never running code. That promise is an invariant, not a version note.

## Quick start

```sh
cp -r examples/pack-pomorski ~/wyraj-packs/mypack
$EDITOR ~/wyraj-packs/mypack/pack.yml          # name it, claim a key
uv run wyraj --validate-pack ~/wyraj-packs/mypack
```

Then enable it in `~/.wyraj/config.yml`:

```yaml
packs:
  - ~/wyraj-packs/mypack
```

Order matters: packs load after the base game, in list order, and **later
wins**. A broken pack is skipped with a dim note at launch — it never
blocks the game.

## What a pack may contain (the v1 surface)

```
mypack/
  pack.yml            # manifest — required (see below)
  bestiary/*.yml      # monsters      — same schema as data/bestiary/
  items/*.yml         # items         — same schema as data/items/
  hooks/*.yml         # story hooks
  loot/*.yml          # per-biome loot tables (file stem = biome)
  errands/*.yml       # village errands (M10)
  epithets/epithets.yml
  narration/<lang>/*.yml   # grammar packs, same format as data/narration/
  locale/<lang>.yml        # UI strings
  audio/sounds.yml + beds|sfx|voices/*  # with an audio/CREDITS.yml
```

Anything else (economy, origins, intro, portrait art) is base-only in v1
and ignored — `--validate-pack` warns so you aren't left guessing. Biomes,
mechanics, and event types are code, not content: never moddable.

## Merge rules — one rule everywhere

**Override by key, extend by new key.** An entry whose key already exists
replaces the base entry *whole* (no deep-merging half a monster); a new
key joins the catalog. Specifics:

| content | granularity |
|---|---|
| bestiary / items / hooks / errands / epithets | per entry key |
| loot | per file stem (whole table) |
| narration | per rule key, per language — redefining `talked_to/gossip` owns that whole variant list |
| locale | per string key |
| audio | per catalog key; files resolve inside *your* pack (you cannot point at base assets) |

**Languages:** shipping `locale/de.yml` and/or `narration/de/` makes
`--lang de` real. English is always merged underneath — anything you
don't translate stays English, and the intro/prologue falls back per
file. Author prose natively under your language key (`de:`), never
translate mechanically.

## The manifest

```yaml
name: "Pack Pomorski"     # shown to humans
key: pomorski             # [a-z0-9_-], unique among loaded packs
version: "1.0"            # part of the save fingerprint
author: "You"
license: "CC-BY-SA-4.0"   # content licensing; NC/ND are refused
description: "..."
```

Saves record the active pack set `(key, version)`: a run saved with packs
will not load without them (and vice versa) — permadeath is not going to
be argued with by a changed bestiary. Meta (`~/.wyraj/meta.yml`) is
tolerant: codex entries from a removed pack simply go dormant.

## Validation

`uv run wyraj --validate-pack ./mypack` checks every file against the
real game schemas and reports errors per file and field, in plain words.
It ends with the honest summary — what your pack **adds** and what it
**overrides** — and exits 0/1, so you can run it in your own CI. The
in-repo example is validated by Wyraj's CI on every commit.

## Licensing expectations

Base game content (`data/`) is CC-BY-SA 4.0. Your pack is your content
under your license, but Wyraj refuses NC/ND manifests and audio credits:
what plugs into a shared folk tradition stays shareable. Audio assets
need an `audio/CREDITS.yml` with `file / author / source_url / license`
per asset (CC0/CC-BY/CC-BY-SA).

## What good packs do

- Keep the register: dark, dry, folkloric. Read `docs/NARRATION.md` first.
- Give every creature `forms:` for each language you ship — Polish
  narration declines nouns through seven cases and will use them.
- Prefer adding to overriding; `--validate-pack` shows your override
  count for a reason.
- Weaknesses are promises to the player. Keep them.
