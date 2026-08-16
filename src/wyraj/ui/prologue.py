"""The prologue: paged, typewriter-revealed prose ("Próg" spec §3).

Any key completes the current page instantly; Enter advances; Esc skips the
whole prologue — always, no confirmation (open decision #12: respect the
player). Returns True if the player read to the end, False if skipped.
"""

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Center, Middle
from textual.widgets import Static

from wyraj.content.intro import load_prologue
from wyraj.ui.i18n import current_language, t

# Dusk falling, page by page: deep grey → moss green → cold blue.
PAGE_STYLES = ("grey74", "dark_sea_green4", "steel_blue", "grey58")
CHAR_INTERVAL = 0.015
COLUMN_WIDTH = 70


class PrologueApp(App[bool]):
    TITLE = "WYRAJ"
    CSS = """
    Screen { background: #0d0f0c; color: #b8b6a9; align: center middle; }
    #page { width: 76; }
    """

    def __init__(
        self,
        origin: str = "",
        text_speed: str = "normal",
        pages: list[str] | None = None,
        final_hint_key: str = "prologue_begin",
    ) -> None:
        super().__init__()
        if pages is None:
            prologue = load_prologue(current_language())
            final = prologue.origins.get(origin, prologue.fallback)
            pages = [*prologue.common, final]
        self.pages = pages or [""]
        self.final_hint_key = final_hint_key
        self.page_index = 0
        self.revealed = 0
        self.instant = text_speed == "instant"

    def compose(self) -> ComposeResult:
        with Middle(), Center():
            yield Static("", id="page")

    def on_mount(self) -> None:
        if self.instant:
            self.revealed = len(self._page_text())
        self._timer = self.set_interval(CHAR_INTERVAL, self._tick)
        self._update()

    def _page_text(self) -> str:
        return self.pages[self.page_index].strip()

    def _page_style(self) -> str:
        return PAGE_STYLES[min(self.page_index, len(PAGE_STYLES) - 1)]

    def _tick(self) -> None:
        if self.revealed < len(self._page_text()):
            self.revealed += 2  # two chars per tick keeps ~15ms/char feel
            self._update()

    def _page_done(self) -> bool:
        return self.revealed >= len(self._page_text())

    def _update(self) -> None:
        raw = self._page_text()
        text = Text(raw[: self.revealed], style=f"italic {self._page_style()}")
        if self._page_done():
            text.append("\n\n")
            hint = (
                t(self.final_hint_key)
                if self.page_index == len(self.pages) - 1
                else t("prologue_next")
            )
            text.append(hint, style="grey42")
        self.query_one("#page", Static).update(text)

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.exit(False)  # skipping must always work
            return
        if not self._page_done():
            self.revealed = len(self._page_text())
            self._update()
            return
        if event.key == "enter":
            if self.page_index >= len(self.pages) - 1:
                self.exit(True)
                return
            self.page_index += 1
            self.revealed = len(self._page_text()) if self.instant else 0
            self._update()
