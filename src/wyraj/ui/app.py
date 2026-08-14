"""The Textual application: three-pane layout, key handling, narration log."""

from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, RichLog

from wyraj.core.actions import Action, Move, Wait
from wyraj.core.game import Game
from wyraj.narration.context import ContextEnricher
from wyraj.narration.engine import NarrationEngine, NarrationLine
from wyraj.narration.forms import build_form_registry
from wyraj.narration.templates import TemplateNarrator, load_pack
from wyraj.ui.screens import DeathScreen
from wyraj.ui.widgets import CharacterPanel, MapView

MOVE_KEYS: dict[str, tuple[int, int]] = {
    "h": (-1, 0),
    "j": (0, 1),
    "k": (0, -1),
    "l": (1, 0),
    "y": (-1, -1),
    "u": (1, -1),
    "b": (-1, 1),
    "n": (1, 1),
    "left": (-1, 0),
    "down": (0, 1),
    "up": (0, -1),
    "right": (1, 0),
}

IMPORTANCE_STYLES = {"normal": "grey74", "high": "bold red3"}


class WyrajApp(App[None]):
    CSS_PATH = "wyraj.tcss"
    TITLE = "WYRAJ"
    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
        Binding("full_stop", "wait", "Wait", key_display="."),
    ]

    def __init__(self, seed: int, use_ascii: bool = False) -> None:
        super().__init__()
        self.game = Game(seed)
        self.use_ascii = use_ascii
        registry = build_form_registry(self.game.bestiary)
        narrator = TemplateNarrator(load_pack("en"), self.game.rng.narration, registry)
        enricher = ContextEnricher(self.game)
        self.narration = NarrationEngine(self.game.bus, narrator, enricher=enricher.enrich)
        self.narration.add_sink(self._on_narration)

    def compose(self) -> ComposeResult:
        with Horizontal(id="top"):
            yield MapView(self.game, use_ascii=self.use_ascii)
            yield CharacterPanel(self.game)
        yield RichLog(id="narrative", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write(
            Text(
                "The puszcza swallows the path behind you. "
                "Somewhere in the dark between the trees, something is already awake.",
                style="italic grey74",
            )
        )

    def _on_narration(self, line: NarrationLine) -> None:
        if self.is_running:
            style = IMPORTANCE_STYLES.get(line.importance, "grey74")
            self.query_one(RichLog).write(Text(line.text, style=style))

    def on_key(self, event: events.Key) -> None:
        if event.key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[event.key]
            self._play(Move(dx, dy))

    def action_wait(self) -> None:
        self._play(Wait())

    def _play(self, action: Action) -> None:
        if self.game.game_over:
            return
        self.game.step(action)
        self.query_one(MapView).refresh()
        self.query_one(CharacterPanel).refresh()
        if self.game.game_over:
            self.push_screen(DeathScreen(seed=self.game.seed, turn=self.game.turn))
