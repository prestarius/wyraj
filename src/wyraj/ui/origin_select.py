"""Character creation: a small pre-game app that picks an origin."""

from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Center, Middle
from textual.widgets import Static

from wyraj.content.origins import OriginDef
from wyraj.ui.i18n import current_language, t


class OriginApp(App[str]):
    """Returns the chosen origin key; Enter accepts the highlighted one."""

    TITLE = "WYRAJ — who walks into the puszcza?"
    BINDINGS: ClassVar = [("enter", "accept", "Accept")]

    CSS = """
    Screen { background: #0d0f0c; color: #b8b6a9; }
    """

    def __init__(
        self,
        origins: dict[str, OriginDef],
        unlocked: list[str] | None = None,
        victorious: set[str] | None = None,
    ) -> None:
        super().__init__()
        allowed = set(unlocked or [])
        self.origins = [
            origins[k] for k in sorted(origins) if origins[k].unlock is None or k in allowed
        ]
        self.victorious = victorious or set()  # M8 §3: origins that sealed the lids
        self.index = 0

    def compose(self) -> ComposeResult:
        with Middle(), Center():
            yield Static(self._render_menu(), id="origin-menu")

    def _render_menu(self) -> Text:
        text = Text()
        lang = current_language()
        text.append(t("origin_title") + "\n", style="bold red3")
        text.append(t("origin_prompt") + "\n\n", style="grey74")
        for i, origin in enumerate(self.origins):
            marker = "▶ " if i == self.index else "  "
            style = "bold gold3" if i == self.index else "grey62"
            text.append(f"{marker}{i + 1}. {origin.name}, {origin.title_for(lang)}", style=style)
            if origin.key in self.victorious:
                text.append(" ⁂", style="light_goldenrod2")  # the birds returned for this one
            text.append("\n", style=style)
        chosen = self.origins[self.index]
        text.append(f"\n{chosen.description_for(lang).strip()}\n", style="grey66")
        text.append("\n" + t("origin_hint"), style="grey42")
        return text

    def _refresh_menu(self) -> None:
        self.query_one("#origin-menu", Static).update(self._render_menu())

    def on_key(self, event: events.Key) -> None:
        if event.key in ("up", "k"):
            self.index = (self.index - 1) % len(self.origins)
            self._refresh_menu()
        elif event.key in ("down", "j"):
            self.index = (self.index + 1) % len(self.origins)
            self._refresh_menu()
        elif event.character and event.character.isdigit():
            digit = int(event.character)
            if 1 <= digit <= len(self.origins):
                self.index = digit - 1
                self._refresh_menu()

    def action_accept(self) -> None:
        self.exit(self.origins[self.index].key)
