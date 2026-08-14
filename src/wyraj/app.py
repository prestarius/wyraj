"""Entrypoint for `uv run wyraj`."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="wyraj", description="Wyraj — a narrated roguelike.")
    parser.add_argument("--seed", type=int, default=None, help="master seed for deterministic runs")
    parser.add_argument("--ascii", action="store_true", help="CP437-safe glyphs (no Unicode)")
    args = parser.parse_args()

    print(f"Wyraj pre-alpha — nothing to play yet (seed={args.seed}).")


if __name__ == "__main__":
    main()
