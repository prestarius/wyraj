# Authoring Narration Packs

Narration packs turn mechanical events into prose. They live in
`data/narration/<lang>/*.yml` — per-language files, authored natively,
never machine-translated from another language's structure.

## Pack format

```yaml
attack_resolved:            # event rule
  player_hit:               # subkey (see table below)
    - weight: 3             # relative pick weight (default 1)
      en: "Your blow bites into {defender.name.def}; it recoils."
    - weight: 4
      tags: [player_dying]  # only eligible when ALL tags are in context
      importance: high      # "high" lines render emphasized
      en: "Hands shaking, you strike — and the world narrows to it."

move_blocked:               # rules without subkeys hold a plain list
  player:
    - en: "The trees stand shoulder to shoulder here."
```

Selection: variants whose `tags` are a subset of the current context are
eligible; the most tag-specific eligible variants win; weighted choice
among them via the seeded `narration` RNG stream; the same template is
never picked twice in a row for one rule. Rules with per-key subkeys fall
back to a `default` subkey, then to a bare rule.

Presentation: `importance: high` renders emphasized (bold red). Each
turn's paragraph is also tinted by its dominant event family — combat
ember, loot gold, lore purple, ambient grey. That category is derived in
code from the event type (`category_of` in `narration/templates.py`);
packs never author it, and it never changes the prose.

## Rule keys

| event            | subkeys                                            |
|------------------|----------------------------------------------------|
| `attack_resolved`| `player_hit/miss/kill/graze`, `enemy_hit/...`      |
| `entity_died`    | `player`, `enemy`                                  |
| `move_blocked`   | `player`, `enemy`                                  |
| `item_picked_up` | —                                                  |
| `item_used`      | effect: `heal`, `feed`, `bless`, `light`           |
| `item_wielded` / `item_worn` | —                                      |
| `hunger_changed` | `sated`, `hungry`, `starving`                      |
| `starvation_hit` | —                                                  |
| `status_applied/tick/expired` | kind: `bleeding`, `poison`, `fear`, `blessing` |
| `light_extinguished` | —                                              |
| `lore_discovered`| the creature/hook key (e.g. `strzyga`), or `default` |
| `level_changed`  | `down`, `up`                                       |
| `talked_to`      | `innkeeper`, `trader`, `gossip` (rumor pool!), `dziad_wedrowny` |
| `rested`         | —                                                  |
| `item_bought` / `item_sold` | —                                       |
| `coins_picked` / `coins_banked` | —                                   |
| `stash_deposited` / `stash_upgraded` | —                              |
| `stash_withdrawn`| `own`, `heirloom`                                  |
| `heirloom_wielded` / `dziad_recognized` | —                           |
| `crane_summon_started/completed` / `crane_return` | —                 |
| `crane_summon_interrupted` | `moved`, `damage`                        |
| `crane_refused`  | `watched`, `no_sky`, `in_village`                  |
| `shrine_visited` / `offering_made` | `perun`, `weles`                 |
| `item_unequipped` | —                                                 |
| `quickslot_bound` | — (`quickslot_cleared/used/refilled` exist but are deliberately silent) |
| `blizna_earned`  | — (a near-death survived; the scar line)           |
| `weapon_named`   | the species key (`wilk`, `bies`, …) — the prose carries the epithet |
| `weapon_recognized` | — (the dziad greets a named weapon)             |
| `deep_descended` | — (first step past the last sky shaft)             |
| `wij_stirred` / `wij_lid_lifted` / `wij_gaze_opened` | — (M8 phases)   |
| `seen_by_wij`    | — (a lit turn under the open gaze)                 |
| `wij_attack_futile` | — (bumping the cradle without salt)             |
| `rite_started` / `rite_completed` | —                                 |
| `rite_interrupted` | `moved`, `damage`                                |

## Context tags

`player_healthy` / `player_bloodied` / `player_dying`, `darkness`,
`unseen_attacker`, `again` (rule fired within the last 3 turns).

## Slots and string forms

Slots are dotted paths into the event: `{damage}`, `{attacker.name}`.
When the path reaches an `EntityRef`, grammar-aware forms apply:

- `{x.name.def}` → "the strzyga" · `{x.name.indef}` → "a strzyga"
- `{x.name.plural}` → "strzygi" · capitalized spec capitalizes: `{x.name.Def}`
- `{x.pronoun.subj|obj|poss}` → she/her/her (from the form table)
- Any other form key (`bier`, `dop`, …) reads the entity's per-language
  form table — this is how Polish cases work; EN falls back to the base.

Form tables are declared on content entries:

```yaml
strzyga:
  forms:
    en: { plural: "strzygi", pronoun_subj: "she", pronoun_obj: "her", pronoun_poss: "her" }
    pl: { mian: "strzyga", dop: "strzygi", bier: "strzygę", ... }
```

The player's forms are built in ("you"/"your", no article).

## The optional LLM narrator (M5)

`--narrator llm` (or `narrator: llm` in `~/.wyraj/config.yml`) wraps the
template narrator in `LLMNarrator` (`narration/llm.py`). Contract:

- The deterministic template paragraph is composed first and sent as the
  DRAFT with the raw event facts; the model may only rephrase, never invent.
- Strict timeout (`llm.timeout`, default 2.5 s); any error, timeout, or
  empty reply falls back to the template text. Output capped at 60 words.
- Backends: `llm.backend: ollama` (default, local, `llm.model`, `llm.url`)
  or `openrouter` (needs `OPENROUTER_API_KEY`).
- Per-run stats (turns narrated, fallbacks, average latency) print to the
  log at the end of a run.
- Golden runs and all tests use templates only — the LLM is garnish, and
  the game is fully playable offline without it.

## What is *not* a grammar pack

Szept hints, the prologue, title taglines, and the help page live under
`data/intro/` with their own loaders — they are UI/onboarding content,
not event narration, and the PL/EN parity test does not govern them
(their own schema tests do). UI chrome strings live in `data/locale/`.

## Rules of the house

- Every entry must render against test fixtures with no unresolved slots —
  `uv run pytest tests/test_narration_templates.py` enforces it. If you
  add a new *rule key*, add a fixture there too.
- An unwritten rule is silence, and silence is a valid choice — routine
  movement is deliberately unnarrated.
- Tone: folk horror told straight. Short sentences land harder. The
  narrator has seen this before and is worried anyway.
