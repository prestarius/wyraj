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
| `talked_to`      | `innkeeper`, `trader`, `gossip` (rumor pool!)      |
| `rested` / `item_traded` | —                                          |

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

## Rules of the house

- Every entry must render against test fixtures with no unresolved slots —
  `uv run pytest tests/test_narration_templates.py` enforces it. If you
  add a new *rule key*, add a fixture there too.
- An unwritten rule is silence, and silence is a valid choice — routine
  movement is deliberately unnarrated.
- Tone: folk horror told straight. Short sentences land harder. The
  narrator has seen this before and is worried anyway.
