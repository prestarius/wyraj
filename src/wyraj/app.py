"""Entrypoint for `uv run wyraj`."""

import argparse
import secrets
from typing import Any


def _load_config_safely() -> dict[str, Any]:
    try:
        from wyraj.persistence.config import load_config

        return load_config()
    except Exception:
        return {}  # a broken config file must never block the game


def main() -> None:
    parser = argparse.ArgumentParser(prog="wyraj", description="Wyraj — a narrated roguelike.")
    parser.add_argument("--seed", type=int, default=None, help="master seed for deterministic runs")
    parser.add_argument("--ascii", action="store_true", help="CP437-safe glyphs (no Unicode)")
    parser.add_argument(
        "--portrait",
        choices=["half", "box"],
        default="half",
        help="portrait art direction: halfblock pixels or box-drawing lines",
    )
    parser.add_argument(
        "--origin",
        choices=["wygnaniec", "zielarka", "najemnik"],
        default=None,
        help="skip character creation and start as this origin",
    )
    parser.add_argument("--history", action="store_true", help="show recent runs and exit")
    args = parser.parse_args()

    if args.history:
        from wyraj.persistence.history import recent_runs

        runs = recent_runs(limit=15)
        if not runs:
            print("No runs recorded yet. The forest is patient.")
            return
        for run in runs:
            depth_note = f"depth {run.max_depth}" if run.max_depth else "the wieś"
            print(
                f"{run.ts}  seed {run.seed:<12} {run.origin:<10} "
                f"{run.turns:>5} turns  reached {depth_note:<10} — {run.cause}"
            )
        return

    config = _load_config_safely()
    if config.get("ascii") and not args.ascii:
        args.ascii = True
    if args.portrait == "half" and config.get("portrait") in ("half", "box"):
        args.portrait = config["portrait"]
    if args.origin is None and config.get("origin"):
        args.origin = config["origin"]

    seed = args.seed if args.seed is not None else secrets.randbelow(2**31)

    from wyraj.persistence.save import has_save, load_game
    from wyraj.ui.app import WyrajApp

    # A saved run continues unless the player explicitly asks for a new seed.
    game = load_game() if args.seed is None and has_save() else None

    origin = args.origin
    if game is None and origin is None:
        from wyraj.content.origins import load_origins
        from wyraj.ui.origin_select import OriginApp

        origin = OriginApp(load_origins()).run() or "wygnaniec"

    WyrajApp(
        seed=seed,
        use_ascii=args.ascii,
        portrait_style=args.portrait,
        game=game,
        origin=origin or "wygnaniec",
    ).run()


if __name__ == "__main__":
    main()
