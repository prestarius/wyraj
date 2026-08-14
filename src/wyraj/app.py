"""Entrypoint for `uv run wyraj`."""

import argparse
import secrets


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
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else secrets.randbelow(2**31)

    from wyraj.persistence.save import has_save, load_game
    from wyraj.ui.app import WyrajApp

    # A saved run continues unless the player explicitly asks for a new seed.
    game = load_game() if args.seed is None and has_save() else None

    WyrajApp(seed=seed, use_ascii=args.ascii, portrait_style=args.portrait, game=game).run()


if __name__ == "__main__":
    main()
