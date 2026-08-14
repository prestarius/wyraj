"""Secondary screens. M0: the death screen."""

from typing import ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Static


class DeathScreen(Screen[None]):
    BINDINGS: ClassVar = [("q", "quit_app", "Quit")]

    def __init__(self, seed: int, turn: int) -> None:
        super().__init__()
        self.seed = seed
        self.turn = turn

    def compose(self) -> ComposeResult:
        text = Text(justify="center")
        text.append("Your soul takes wing toward Wyraj.\n\n", style="bold red3")
        text.append(f"You lasted {self.turn} turns.\n", style="grey74")
        text.append(f"Seed: {self.seed}\n\n", style="grey58")
        text.append("Press q to quit.", style="grey42")
        with Middle(), Center():
            yield Static(text)

    def action_quit_app(self) -> None:
        self.app.exit()
