# Wyraj

A **narrated roguelike** set in Slavic dark fantasy. Procedural world,
permadeath, turn-based tactics — and a narration engine that turns every
mechanical event into readable folk-horror prose. No goblins, no orcs:
leszy, strzyga, utopiec, bies, licho.

> *Wyraj* — the Slavic otherworld where souls fly as birds and return in spring.

![Wyraj screenshot](docs/screenshot.svg)

**Status:** pre-alpha. Milestones M0–M7 plus the intro ("Próg") are
complete: the full loop — village, forest, marsh, three crypt levels,
death, and what survives it — is playable in English and Polish, with
the M7 "Sylwetka" character pane and quickslots on top.

## What makes it different

- **Read the log like a story.** Events carry facts; a deterministic
  template engine with context tags (wounds, darkness, recency) composes
  each turn into one paragraph of prose. Meeting a strzyga is an *event*:
  "Lamplight eyes catch yours through the branches. A strzyga — and she
  has already counted your nights."
- **Slavic folklore played straight.** Bestiary with per-creature
  folklore and weaknesses, folk remedies (odwar, gromnica, sól święcona),
  story hooks, village rumors, shrines of Perun and Weles — all
  data-driven YAML under `data/`.
- **A world with a shape.** The wieś (rest, trade, the skrzynia) → the
  puszcza → the bagna, where utopce swim → three kurhany crypt levels,
  dark unless your thunder-candle burns. Somewhere below, a wandering
  dziad sells at cruel prices and remembers you across deaths.
- **Permadeath with heirlooms — "Powroty".** Everything on the body is
  lost, always. But the chest keeps what you stored, silver banks in the
  village, the codex keeps what your deaths taught you, and some deaths
  unlock new origins ("die to the strzyga three times…"). Carry-over is
  heirlooms, not a savings account — a 50-run simulation enforces it.
- **Crane flight.** No teleports: hold a crane feather under open sky,
  stand still for six turns while nothing watches, and a wedge of birds
  carries you home. In the crypts, only where the ceiling has collapsed.
- **A pane that is a portrait, not a stat block.** The character panel
  composites a layered figure from YAML art: posture hunches as wounds
  deepen, armor changes the outline, a lit gromnica warms the frame, and
  surviving a near-death leaves a permanent blizna scar. Below it: a
  six-slot paper-doll (`e` to manage), a status row, and quickslots
  `1-4` — bind an odwar in the pack and drink it mid-fight without
  opening a menu. A weapon that kills seven of one species *earns a
  name* ("Wilcza Zguba"), and the dziad greets it. Every death captures
  the final portrait — scars, gear, and all — into the morgue file.
- **An intro worth reading.** Title screen under drifting cranes, a paged
  typewriter prologue that differs by origin, and a whisper system that
  teaches the game diegetically — one dim aside per first encounter,
  once per profile, and never a tutorial popup.
- **Fully bilingual.** `--lang pl` switches to natively authored Polish
  narration — real case declension (*strzygę, strzygą, strzydze*) via
  per-noun form tables, never machine-mapped from English.
- **Deterministic to the bone.** Same seed + same meta-state + same
  inputs = same run, golden-transcript tested. Saves restore RNG streams
  bit-exactly and are consumed on load.
- **Optional AI narrator.** `--narrator llm` lets a local Ollama model
  rephrase the template prose under a strict fact-grounding contract,
  falling back to templates on any timeout. Off by default; the game is
  fully playable offline.

## Play

```sh
uv sync
uv run wyraj                 # title screen: new journey, continue, codex, morgue
uv run wyraj --seed 42       # skip the ceremony: straight into a seeded run
uv run wyraj --lang pl       # cała narracja po polsku
uv run wyraj --origin zielarka
uv run wyraj --history       # your past deaths, remembered
uv run wyraj --reset-intro   # replay the prologue and whispers (keeps progress)
uv run wyraj --ascii         # CP437-safe glyphs
uv run wyraj --portrait half # halfblock portrait (default: box-drawing)
uv run wyraj --narrator llm  # optional local-LLM narration (Ollama)
```

**Keys:** `hjkl`/`yubn`/arrows move (bump a creature to strike it — or a
villager, to talk), `.` wait, `g` gather, `i` pack, `x` examine,
`e` worn & wielded, `c` codex, `L` legend of the map's signs, `1-4`
use an at-hand item (`Shift+1-4` clears; bind in the pack with `1-4`
then a letter), `>`/`<` stairs, `r` rest (village), `?` help,
`s` save+quit, `q` quit (it asks first — an abandoned run is not
saved). Death offers `n` set out again, `m` back to the title screen,
`q` leave.

**Your files** (all under `~/.wyraj/`, override with `WYRAJ_HOME`):

| File | What it is |
|---|---|
| `save.json.gz` | the single run save — consumed on load, deleted on death |
| `meta.yml` | what survives death: stash, silver, codex, dziad memory, unlocks. Human-editable by design; edits are flagged, never punished |
| `history.db`, `morgue/` | every run, remembered — each morgue file carries the final portrait |
| `config.yml` | `ascii`, `portrait`, `origin`, `lang`, `narrator`, `llm`, `hints`, `text_speed`, `quickslots` (`auto_refill: false` for hardcore slots) |

## Develop

```sh
uv run pytest              # 240+ tests incl. golden transcript & 50-run meta sim
uv run ruff check .        # lint
uv run mypy                # strict on core/ and narration/
```

Docs: [architecture](docs/ARCHITECTURE.md) ·
[authoring content](docs/CONTENT.md) ·
[authoring narration](docs/NARRATION.md) ·
[contributing](CONTRIBUTING.md)

Design specs: `docs/WYRAJ_PROJECT.md` (core game),
`docs/WYRAJ_M6_POWROTY.md` (meta-progression),
`docs/WYRAJ_PROG_SPEC.md` (intro & onboarding),
`docs/WYRAJ_M7_SYLWETKA.md` (character pane & quickslots);
roadmap and status: `docs/IMPLEMENTATION_PLAN.md`.

## License

- **Code:** [AGPL-3.0-or-later](LICENSE)
- **Game content** (everything under `data/` — bestiary, items, narration,
  lore): [CC BY-SA 4.0](data/LICENSE)
- Contributions require agreeing to the [CLA](CLA.md) — see
  [CONTRIBUTING.md](CONTRIBUTING.md).
