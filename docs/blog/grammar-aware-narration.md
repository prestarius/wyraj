# A grammar-aware narration engine for Polish (in a roguelike)

*Draft for the blog — written during milestone M4 of [Wyraj](https://github.com/prestarius/wyraj),
a narrated roguelike set in Slavic dark fantasy.*

Wyraj's central conceit is that the message log is the game. Every
mechanical event — a hit, a candle guttering out, a strzyga stepping out
of the treeline — passes through a narration engine that composes prose.
English was the first language, but the game is Slavic folk horror; if it
was ever going to feel right anywhere, it had to feel right in Polish.

And Polish breaks naive game templating instantly.

## Why `{name}` doesn't survive contact with Polish

The classic roguelike interpolation looks like this:

```
"You hit the {name}!"
```

That works in English because English nouns barely inflect. Polish nouns
decline through seven cases, three genders, and an animacy distinction,
and verbs agree with all of it. The same monster is *strzyga* when she's
the subject, *strzygę* when you strike her, *strzygą* when something is
done with her, *strzydze* when something happens to her. One string per
noun cannot express this. Machine-translating English templates produces
the uncanny "Uderzasz strzyga!" that every Polish gamer recognizes as the
sound of localization done on the cheap.

The usual fixes are worse: either every sentence gets authored per-noun
(combinatorial explosion), or the prose is contorted into case-free
constructions ("Trafiony: strzyga"), which reads like a tax form.

## Form tables, not strings

Wyraj's answer: **every nameable thing declares a table of string forms,
not a single string.** Content is YAML; the strzyga's entry carries:

```yaml
strzyga:
  forms:
    en: { plural: "strzygi", pronoun_subj: "she", pronoun_poss: "her" }
    pl: { mian: "strzyga", dop: "strzygi", cel: "strzydze",
          bier: "strzygę", narz: "strzygą", miej: "strzydze",
          pronoun_subj: "ona", pronoun_poss: "jej" }
```

Narration templates request the form they need. A template slot is a
dotted path into the event object, and when the path lands on an entity,
the trailing token names a form:

```yaml
# data/narration/pl/combat.yml
- pl: "Twój cios sięga {defender.name.dop}; {defender.pronoun.subj} cofa się z sykiem."
- pl: "Trafiasz. {defender.name.Mian} wzdryga się, a czarna krew perli się tam, gdzie cięło ostrze."
```

A capitalized form spec (`Mian`) capitalizes the result — sentence-initial
position is the template author's decision, not the engine's guess. The
engine itself knows nothing about Polish: it resolves `bier` by looking it
up in the table, and any unknown form falls back to the base name — which
is exactly the English behavior, where "accusative of strzyga" is just
"strzyga". One resolution rule serves both languages.

Two language-specific wrinkles live in the *registry*, not the engine:
English entities get `def`/`indef` accessors that glue on articles
("the strzyga", "a strzyga"); for Polish the registry marks everything
article-less, so the same `def` slot degrades to the bare nominative and
an English template can be ported without exploding. And the player is a
first-class declining entity too: *ty, ciebie, tobie, tobą* — because "the
bies bears **you** down" needs a case in Polish like anything else.

## Packs are authored, never translated

The second design rule: narration packs are **per-language files, authored
natively**. `data/narration/pl/` is not a translation of
`data/narration/en/` — it's Polish prose written for the same event
schema. The English pack says a wounded strzyga "sways aside like a branch
in wind"; the Polish pack was free to reach for its own register
(*"usuwa się jak gałąź na wietrze"*) or abandon the image entirely where
Polish rhythm wanted something else. The event carries facts — attacker,
defender, outcome, damage — and each language decides how to tell them.

A test enforces *rule parity* (every event rule covered in EN must be
covered in PL) without enforcing sentence parity, and a runtime fallback
narrates any genuinely missing rule from the English pack rather than
going silent. Another test renders every pack entry in both languages
against fixture events and fails on any unresolved slot — so
`{defender.name.bier}` typos die in CI, not in a player's log.

## Determinism as a localization feature

Wyraj's core rule — same seed, same run — turns out to matter for
localization too. Variant selection draws from a dedicated seeded RNG
stream, so narration in any language can never perturb gameplay, and the
whole game is regression-tested by a golden transcript: fixed seed,
scripted input, byte-identical log of every event *and* narration line.
When the Polish packs landed, the English golden transcript didn't move by
a byte. That's the proof the narration layer is genuinely cosmetic — and
that a translator can never break a save.

## What I'd tell you to steal

1. **Form tables per noun, form specs per slot.** The engine stays
   language-agnostic; grammar lives in data.
2. **Author per-language, verify per-event.** Parity of coverage, freedom
   of prose.
3. **Fall back loudly-but-gracefully.** Unknown form → base name; missing
   rule → source language. Never crash, never go mute.
4. **Golden transcripts.** If your narration can't change without a test
   noticing, your localizers can be fearless.

The full implementation is ~200 lines across
[`forms.py`](https://github.com/prestarius/wyraj/blob/main/src/wyraj/narration/forms.py)
and
[`templates.py`](https://github.com/prestarius/wyraj/blob/main/src/wyraj/narration/templates.py),
AGPL-licensed. The strzyga is waiting, in either language.
