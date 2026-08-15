"""The title screen ("Próg" spec §2).

Returns to the launcher: "new", "new:<seed>", "continue", or None (quit).
Cranes drift over the letters; the lore starts before the game does.
"""

import random
from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Center, Middle
from textual.screen import ModalScreen
from textual.widgets import Static

from wyraj.content.bestiary import load_bestiary
from wyraj.content.economy import load_drops, load_prices
from wyraj.content.intro import load_title_lines
from wyraj.content.items import load_items
from wyraj.persistence.config import load_config, save_config
from wyraj.persistence.history import recent_runs
from wyraj.persistence.meta import MetaState
from wyraj.ui.codex_view import build_codex_text
from wyraj.ui.i18n import current_language, t

BANNER = """\
██╗    ██╗██╗   ██╗██████╗  █████╗      ██╗
██║    ██║╚██╗ ██╔╝██╔══██╗██╔══██╗     ██║
██║ █╗ ██║ ╚████╔╝ ██████╔╝███████║     ██║
██║███╗██║  ╚██╔╝  ██╔══██╗██╔══██║██   ██║
╚███╔███╔╝   ██║   ██║  ██║██║  ██║╚█████╔╝
 ╚══╝╚══╝    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝"""

BIRD_GLYPHS = ("ˇ", "v", "w")
SKY_WIDTH = 64
SKY_ROWS = 3


class _Bird:
    def __init__(self, rng: random.Random) -> None:
        self.x = float(-rng.randint(1, 12))
        self.row = rng.randrange(SKY_ROWS)
        self.glyph = rng.choice(BIRD_GLYPHS)
        self.speed = rng.uniform(0.6, 1.4)


class CodexMenuScreen(ModalScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Close"), ("c", "close", "Close")]

    def __init__(self, meta: MetaState) -> None:
        super().__init__()
        self.meta = meta

    def compose(self) -> ComposeResult:
        prices = load_prices()

        def sell_price(key: str) -> int:
            return max(1, round(prices.buy.get(key, 10) * prices.sell_ratio))

        text = build_codex_text(
            bestiary=load_bestiary(),
            items_catalog=load_items(),
            drops=load_drops(),
            sell_price_for=sell_price,
            tier_of=lambda key: self.meta.codex.known.get(key, "unknown"),
        )
        with Middle(), Center():
            yield Static(text)

    def action_close(self) -> None:
        self.dismiss(None)


class MorgueMenuScreen(ModalScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Close"), ("m", "close", "Close")]

    def compose(self) -> ComposeResult:
        text = Text()
        text.append(t("morgue_title") + "\n\n", style="bold")
        runs = recent_runs(limit=12)
        if not runs:
            text.append(t("morgue_empty") + "\n", style="grey58")
        for run in runs:
            text.append(f" {run.ts[:10]}  ", style="grey42")
            text.append(f"{run.origin:<14}", style="grey74")
            text.append(t("morgue_row", turns=run.turns, depth=run.max_depth), style="grey58")
            text.append(f"  — {run.cause}\n", style="grey66")
        text.append("\n" + t("esc_close"), style="grey42")
        with Middle(), Center():
            yield Static(text)

    def action_close(self) -> None:
        self.dismiss(None)


class OptionsScreen(ModalScreen[str | None]):
    """Toggles write config.yml; 'n' starts a seeded journey (typed digits)."""

    BINDINGS: ClassVar = [("escape", "close", "Close")]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.seed_buffer: str | None = None

    def _current(self, key: str, default: str) -> str:
        value = self.config.get(key, default)
        return str(value)

    def compose(self) -> ComposeResult:
        yield Static(self._render_options(), id="options-body")

    def _render_options(self) -> Text:
        text = Text()
        text.append(t("options_title") + "\n\n", style="bold")
        hints = "on" if self.config.get("hints", True) else "off"
        text.append(f" h — {t('options_hints')}: {hints}\n")
        text.append(f" s — {t('options_speed')}: {self._current('text_speed', 'normal')}\n")
        text.append(f" p — {t('options_portrait')}: {self._current('portrait', 'box')}\n")
        text.append(f" l — {t('options_lang')}: {self._current('lang', 'en')}\n")
        text.append("\n")
        if self.seed_buffer is None:
            text.append(f" n — {t('options_seeded')}\n", style="gold3")
        else:
            text.append(f" {t('options_seed_prompt')}: {self.seed_buffer}_\n", style="bold gold3")
        text.append("\n" + t("esc_close"), style="grey42")
        return text

    def _refresh(self) -> None:
        self.query_one("#options-body", Static).update(self._render_options())

    def on_key(self, event: events.Key) -> None:
        event.stop()
        if self.seed_buffer is not None:
            if event.character and event.character.isdigit() and len(self.seed_buffer) < 9:
                self.seed_buffer += event.character
            elif event.key == "backspace":
                self.seed_buffer = self.seed_buffer[:-1]
            elif event.key == "enter" and self.seed_buffer:
                self.dismiss(f"new:{int(self.seed_buffer)}")
                return
            elif event.key == "escape":
                self.seed_buffer = None
            self._refresh()
            return
        if event.key == "escape":
            self.dismiss(None)
            return
        if event.key == "h":
            self.config["hints"] = not self.config.get("hints", True)
            save_config({"hints": self.config["hints"]})
        elif event.key == "s":
            new = "instant" if self._current("text_speed", "normal") == "normal" else "normal"
            self.config["text_speed"] = new
            save_config({"text_speed": new})
        elif event.key == "p":
            new = "half" if self._current("portrait", "box") == "box" else "box"
            self.config["portrait"] = new
            save_config({"portrait": new})
        elif event.key == "l":
            new = "pl" if self._current("lang", "en") == "en" else "en"
            self.config["lang"] = new
            save_config({"lang": new})
        elif event.key == "n":
            self.seed_buffer = ""
        self._refresh()


class TitleApp(App[str]):
    TITLE = "WYRAJ"
    CSS = """
    Screen { background: #0d0f0c; color: #b8b6a9; align: center middle; }
    #sky { height: 3; width: 100%; }
    #body { width: auto; }
    """

    def __init__(self, meta: MetaState, has_save: bool, rng_seed: int | None = None) -> None:
        super().__init__()
        self.meta = meta
        self.has_save = has_save
        self.rng = random.Random(rng_seed)
        lines = load_title_lines(current_language())
        self.tagline = self.rng.choice(lines) if lines else ""
        self.birds: list[_Bird] = []
        self.index = 0

    def _menu_entries(self) -> list[tuple[str, str]]:
        entries = [("new", t("title_new"))]
        if self.has_save:
            entries.append(("continue", t("title_continue")))
        entries += [
            ("codex", t("title_codex")),
            ("morgue", t("title_morgue")),
            ("options", t("title_options")),
            ("quit", t("title_quit")),
        ]
        return entries

    def compose(self) -> ComposeResult:
        yield Static("", id="sky")
        with Middle(), Center():
            yield Static(self._render_body(), id="body")

    def on_mount(self) -> None:
        self.set_interval(0.35, self._drift_birds)

    def _drift_birds(self) -> None:
        if self.rng.random() < 0.18 and len(self.birds) < 5:
            self.birds.append(_Bird(self.rng))
        for bird in self.birds:
            bird.x += bird.speed
        self.birds = [b for b in self.birds if b.x < SKY_WIDTH + 4]
        rows = [[" "] * SKY_WIDTH for _ in range(SKY_ROWS)]
        for bird in self.birds:
            x = int(bird.x)
            if 0 <= x < SKY_WIDTH:
                rows[bird.row][x] = bird.glyph
        sky = Text("\n".join("".join(row) for row in rows), style="grey42")
        self.query_one("#sky", Static).update(sky)

    def _render_body(self) -> Text:
        text = Text()
        text.append(BANNER + "\n", style="bold red3")
        if self.tagline:
            text.append(f"\n{self.tagline}\n\n", style="italic grey62")
        for i, (_key, label) in enumerate(self._menu_entries()):
            marker = "▶ " if i == self.index else "  "
            style = "bold gold3" if i == self.index else "grey62"
            text.append(f"   {marker}{label}\n", style=style)
        return text

    def _refresh_body(self) -> None:
        self.query_one("#body", Static).update(self._render_body())

    def on_key(self, event: events.Key) -> None:
        if len(self.screen_stack) > 1:
            return
        entries = self._menu_entries()
        if event.key in ("up", "k"):
            self.index = (self.index - 1) % len(entries)
        elif event.key in ("down", "j"):
            self.index = (self.index + 1) % len(entries)
        elif event.key == "enter":
            self._choose(entries[self.index][0])
        elif event.key in ("q", "escape"):
            self.exit(None)
        self._refresh_body()

    def _choose(self, key: str) -> None:
        if key in ("new", "continue"):
            self.exit(key)
        elif key == "quit":
            self.exit(None)
        elif key == "codex":
            self.push_screen(CodexMenuScreen(self.meta))
        elif key == "morgue":
            self.push_screen(MorgueMenuScreen())
        elif key == "options":

            def on_result(result: str | None) -> None:
                if result is not None:
                    self.exit(result)

            self.push_screen(OptionsScreen(), on_result)
