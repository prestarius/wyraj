# Wyraj

A **narrated roguelike** set in Slavic dark fantasy. Procedural world, permadeath,
turn-based tactics — and a narration engine that turns every mechanical event into
readable folk-horror prose. No goblins, no orcs: leszy, strzyga, utopiec, bies.

> *Wyraj* — the Slavic otherworld where souls fly as birds and return in spring.

**Status:** pre-alpha, milestone M1 ("it reads like a story") complete.

## Run

```sh
uv sync
uv run wyraj                 # play
uv run wyraj --seed 42       # deterministic run
uv run wyraj --portrait box  # box-drawing portrait (default: halfblock)
```

Keys: `hjkl`/`yubn`/arrows move (bump to attack), `.` wait, `g` get,
`i` inventory, `x` examine, `c` codex, `q` quit.

## Develop

```sh
uv run pytest           # tests
uv run ruff check .     # lint
uv run mypy             # typecheck (strict on core/ and narration/)
```

See `docs/WYRAJ_PROJECT.md` for the full project specification and
`docs/IMPLEMENTATION_PLAN.md` for the roadmap.
