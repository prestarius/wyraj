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
        default=None,
        help="portrait art direction: box-drawing lines (default) or halfblock pixels",
    )
    parser.add_argument(
        "--origin",
        default=None,
        help="skip character creation and start as this origin (must be unlocked)",
    )
    parser.add_argument(
        "--lang", choices=["en", "pl"], default=None, help="game language (default: en)"
    )
    parser.add_argument(
        "--narrator",
        choices=["template", "llm"],
        default=None,
        help="narration mode: deterministic templates (default) or LLM garnish",
    )
    parser.add_argument("--history", action="store_true", help="show recent runs and exit")
    parser.add_argument(
        "--reset-intro",
        action="store_true",
        help="forget the prologue and the szept whispers, then exit (progress is kept)",
    )
    args = parser.parse_args()

    if args.reset_intro:
        from wyraj.persistence.meta import load_meta as _load_meta
        from wyraj.persistence.meta import save_meta as _save_meta

        meta = _load_meta()
        meta.prologue_seen = False
        meta.szept_seen = []
        _save_meta(meta)
        print("The threshold forgets you. Prologue and whispers will play again.")
        return

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
    if args.portrait is None:
        args.portrait = (
            config.get("portrait") if config.get("portrait") in ("half", "box") else "box"
        )
    if args.origin is None and config.get("origin"):
        args.origin = config["origin"]
    if args.lang is None:
        args.lang = config.get("lang") if config.get("lang") in ("en", "pl") else "en"
    if args.narrator is None:
        args.narrator = (
            config.get("narrator") if config.get("narrator") in ("template", "llm") else "template"
        )
    llm_config = config.get("llm") if isinstance(config.get("llm"), dict) else {}

    from wyraj.ui.i18n import set_language

    set_language(args.lang)

    from wyraj.content.origins import load_origins
    from wyraj.persistence.meta import load_meta, save_meta
    from wyraj.persistence.save import has_save, load_game
    from wyraj.ui.app import WyrajApp

    origins = load_origins()
    meta = load_meta()
    quickslots_cfg: dict[str, Any] = (
        config["quickslots"] if isinstance(config.get("quickslots"), dict) else {}
    )
    auto_refill = bool(quickslots_cfg.get("auto_refill", True))

    def launch(game: object | None, origin: str, seed: int) -> str | None:
        return WyrajApp(
            seed=seed,
            use_ascii=args.ascii,
            portrait_style=args.portrait,
            game=game,  # type: ignore[arg-type]
            origin=origin,
            lang=args.lang,
            narrator_mode=args.narrator,
            llm_config=llm_config,
            hints=bool(config.get("hints", True)),
            quickslot_auto_refill=auto_refill,
        ).run()

    def play_run(game: object | None, origin: str, seed: int) -> str | None:
        """Run the app; the death screen's "set out again" starts fresh runs
        (same origin, new seed) until the player quits or asks for the title."""
        outcome = launch(game, origin, seed)
        while outcome == "restart":
            outcome = launch(None, origin, secrets.randbelow(2**31))
        return outcome

    if args.seed is not None:
        # Fast path for testers and scripts: straight into a seeded run,
        # no title, no prologue ("Próg" spec §2 — seeds stay hidden).
        origin = args.origin
        if origin is not None:
            definition = origins.get(origin)
            if definition is None or (
                definition.unlock is not None and origin not in meta.unlocks.origins
            ):
                print(f"Origin '{origin}' is not unlocked yet. Something of you must remain first.")
                return
        if origin is None:
            from wyraj.ui.origin_select import OriginApp

            origin = OriginApp(origins, unlocked=meta.unlocks.origins).run() or "wygnaniec"
        outcome: str | None = "restart"
        while outcome == "restart":
            outcome = launch(None, origin, args.seed)  # a pinned seed stays pinned
        if outcome != "title":
            return
        meta = load_meta()  # death mutated it on disk

    from wyraj.ui.title import TitleApp

    while True:
        choice = TitleApp(meta, has_save=has_save()).run()
        if choice is None:
            return

        if choice == "continue":
            game = load_game()
            if game is not None:
                if play_run(game, game.origin.key, game.seed) != "title":
                    return
                meta = load_meta()
                continue
            choice = "new"  # save vanished under us: fall through to a new journey

        if choice.startswith("new:"):
            seed = int(choice.split(":", 1)[1])
        else:
            seed = secrets.randbelow(2**31)

        origin = args.origin
        if origin is None:
            from wyraj.ui.origin_select import OriginApp

            origin = OriginApp(origins, unlocked=meta.unlocks.origins).run() or "wygnaniec"

        if not meta.prologue_seen:
            from wyraj.ui.prologue import PrologueApp

            PrologueApp(origin, text_speed=str(config.get("text_speed", "normal"))).run()
            meta.prologue_seen = True
            save_meta(meta)

        if play_run(None, origin, seed) != "title":
            return
        meta = load_meta()  # back to the threshold with fresh unlocks


if __name__ == "__main__":
    main()
