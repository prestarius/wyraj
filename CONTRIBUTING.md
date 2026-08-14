# Contributing to Wyraj

Dziękujemy! Contributions are welcome — bug reports, folklore-faithful
content, code, and Polish localization help most of all.

## Ground rules

- **CLA:** first-time contributors must agree to the [CLA](CLA.md) —
  one line in your first PR description.
- **Licensing:** code is AGPL-3.0-or-later; everything under `data/` is
  CC BY-SA 4.0. By contributing you license your work accordingly.
- **Determinism is sacred.** Same seed + same inputs = same run. Never
  use wall-clock time or unseeded randomness in `core/`, `procgen/`, or
  `narration/`. The golden-run test will catch you if you do.
- `core/` must never import from `ui/`.
- Content lives in YAML under `data/` — adding a monster, item, or
  narration pack entry should not require touching engine code.

## Workflow

```sh
uv sync
uv run pytest              # must be green
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy                # strict on core/ and narration/
```

- Branch per change, conventional commits (`feat(core): …`, `fix(ui): …`).
- If your change alters the golden transcript intentionally, regenerate it
  with `GOLDEN_REGEN=1 uv run pytest tests/test_golden_run.py` and say so
  in the PR.
- Writing narration? Read `docs/NARRATION.md` first. Every pack entry must
  render cleanly against fixtures (the test suite enforces this).
- Adding content? See `docs/CONTENT.md` for schemas and conventions.

## Tone

Wyraj is Slavic folk horror: quiet dread, folklore played straight, no
camp. When writing prose or lore, prefer the way a village elder would
tell it — concrete, unhurried, and slightly too calm.
