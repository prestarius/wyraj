# Template vs. LLM: narrating the same turn twice

*Draft #2 for the blog — companion to "A grammar-aware narration engine for
Polish". Status: skeleton — the template column is real game output; the
LLM column needs capturing on a machine with Ollama installed
(`uv run wyraj --seed 42 --narrator llm`, then copy the log).*

Wyraj's narration is deterministic by design: seeded template packs, one
composed paragraph per turn. M5 added an optional LLM pass on top — not a
replacement, a *garnish*. The model receives the mechanical facts and the
already-composed template paragraph as ground truth, and is allowed to do
exactly one thing: rephrase. On any timeout, error, or oversized reply,
the template text ships instead. The game cannot tell the difference; the
log can.

## The contract in one paragraph

The prompt says: here are the FACTS (typed event data), here is the DRAFT
(the deterministic rendering), rewrite the draft in the house voice, at
most 60 words, never invent a creature, number, or outcome. The output is
sanitized, capped, and replaced by the draft if anything is off. Determinism
of *gameplay* is untouched — the LLM sees prose, produces prose, and the
golden-run transcript (templates only) never moves.

## Same seed, same turn, two narrators

| Turn | TemplateNarrator (deterministic) | LLMNarrator (llama3.2, local) |
|---|---|---|
| First sighting | "Grey on grey against the treeline: a wilk, watching you the way a butcher watches a fattened pig." | *(capture)* |
| Melee round | "Your blow bites into the bies; it recoils with a wet hiss. The bies circles and comes at you again, patient as winter." | *(capture)* |
| The candle dies | "The gromnica gutters, flares once, and dies. The dark steps closer." | *(capture)* |
| Death | "The strzyga bears you down into the cold moss. The last thing you hear is its breathing. Darkness closes over you. Somewhere above the canopy, a bird takes wing toward Wyraj." | *(capture)* |

*(Also capture: per-run stats line, e.g. "LLM narrator: 41/48 turns
narrated by the model (7 template fallbacks), avg 900 ms".)*

## Early observations to verify when capturing

- Small local models are surprisingly good at *rephrasing* and terrible at
  *restraint* — the 60-word cap and the "never invent" clause do most of
  the work.
- Latency is the real cost: with a 2.5 s timeout a slow machine plays a
  turn-based game with a hiccup. Fallback statistics make the trade
  visible instead of mysterious.
- The template voice remains the benchmark. The interesting question is
  not "is the model better?" but "does variety beat curation over a long
  run?" — which is exactly what the comparison table should answer.
