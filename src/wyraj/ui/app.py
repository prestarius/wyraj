"""The Textual application: three-pane layout, key handling, narration log."""

from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, RichLog

from wyraj.core.actions import Action, Get, Move, Wait
from wyraj.core.game import Game
from wyraj.narration.context import ContextEnricher
from wyraj.narration.engine import NarrationEngine, NarrationLine
from wyraj.narration.forms import build_form_registry
from wyraj.narration.templates import TemplateNarrator, load_pack
from wyraj.ui.screens import CodexScreen, DeathScreen, ExamineScreen, InventoryScreen
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
        Binding("g", "get", "Get"),
        Binding("i", "inventory", "Inventory"),
        Binding("x", "examine", "Examine"),
        Binding("c", "codex", "Codex"),
    ]

    def __init__(self, seed: int, use_ascii: bool = False, portrait_style: str = "half") -> None:
        super().__init__()
        self.game = Game(seed)
        self.use_ascii = use_ascii
        self.portrait_style = portrait_style
        registry = build_form_registry({**self.game.bestiary, **self.game.items_catalog})
        narrator = TemplateNarrator(load_pack("en"), self.game.rng.narration, registry)
        enricher = ContextEnricher(self.game)
        self.narration = NarrationEngine(self.game.bus, narrator, enricher=enricher.enrich)
        self.narration.add_sink(self._on_narration)

    def compose(self) -> ComposeResult:
        with Horizontal(id="top"):
            yield MapView(self.game, use_ascii=self.use_ascii)
            yield CharacterPanel(self.game, portrait_style=self.portrait_style)
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
        if len(self.screen_stack) > 1:
            return  # a modal is open; it owns the keys
        if event.key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[event.key]
            self._play(Move(dx, dy))

    def action_wait(self) -> None:
        self._play(Wait())

    def action_get(self) -> None:
        self._play(Get())

    def action_examine(self) -> None:
        self.push_screen(ExamineScreen(self.game))

    def action_codex(self) -> None:
        self.push_screen(CodexScreen(self.game))

    def action_inventory(self) -> None:
        def on_result(action: Action | None) -> None:
            if action is not None:
                self._play(action)

        self.push_screen(InventoryScreen(self.game), on_result)

    def _play(self, action: Action) -> None:
        if self.game.game_over:
            return
        self.game.step(action)
        self.query_one(MapView).refresh()
        self.query_one(CharacterPanel).refresh()
        if self.game.game_over:
            self.push_screen(DeathScreen(seed=self.game.seed, turn=self.game.turn))
