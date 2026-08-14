"""Entrypoint for `uv run wyraj`."""

import argparse
import secrets


def main() -> None:
    parser = argparse.ArgumentParser(prog="wyraj", description="Wyraj — a narrated roguelike.")
    parser.add_argument("--seed", type=int, default=None, help="master seed for deterministic runs")
    parser.add_argument("--ascii", action="store_true", help="CP437-safe glyphs (no Unicode)")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else secrets.randbelow(2**31)

    from wyraj.ui.app import WyrajApp

    WyrajApp(seed=seed, use_ascii=args.ascii).run()


if __name__ == "__main__":
    main()
