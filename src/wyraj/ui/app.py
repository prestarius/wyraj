"""The Textual application: three-pane layout, key handling, narration log."""

from datetime import datetime
from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, RichLog

from wyraj.content.audio import load_audio_catalog
from wyraj.content.intro import load_szept
from wyraj.core.actions import (
    Action,
    Ascend,
    ClearQuickslot,
    Descend,
    Get,
    Move,
    Rest,
    UseQuickslot,
    Wait,
)
from wyraj.core.components import Health
from wyraj.core.events import ShrineVisited, StashOpened, TalkedTo
from wyraj.core.game import Game
from wyraj.narration.context import ContextEnricher
from wyraj.narration.engine import NarrationEngine, NarrationLine
from wyraj.narration.forms import build_form_registry
from wyraj.narration.llm import DEFAULT_TIMEOUT, LLMNarrator, build_backend
from wyraj.narration.szept import SzeptSystem
from wyraj.narration.templates import TemplateNarrator, load_pack
from wyraj.persistence.history import record_run
from wyraj.persistence.morgue import write_morgue
from wyraj.persistence.save import delete_save, save_game
from wyraj.ui.audio import AudioBackend, AudioSystem, AudioUnavailable, PygameBackend
from wyraj.ui.i18n import t
from wyraj.ui.screens import (
    CodexScreen,
    ConfirmQuitScreen,
    DeathScreen,
    EquipScreen,
    ExamineScreen,
    HelpScreen,
    InventoryScreen,
    LegendScreen,
    ShrineScreen,
    StashScreen,
    TradeScreen,
)
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

# Paragraph tint per narration family; high importance overrides them all.
CATEGORY_STYLES = {
    "combat": "indian_red",
    "loot": "gold3",
    "lore": "medium_purple3",
    "ambient": "grey74",
}


class WyrajApp(App[str]):
    """Exits with an outcome: "quit" | "restart" (new run) | "title" (main screen)."""

    CSS_PATH = "wyraj.tcss"
    TITLE = "WYRAJ"
    BINDINGS: ClassVar = [
        Binding("q", "confirm_quit", "Quit"),
        Binding("full_stop", "wait", "Wait", key_display="."),
        Binding("g", "get", "Get"),
        Binding("i", "inventory", "Inventory"),
        Binding("x", "examine", "Examine"),
        Binding("e", "equip", "Equip"),
        Binding("c", "codex", "Codex"),
        Binding("L", "legend", "Legend"),
        Binding("1", "quickslot(0)", "Quick 1", show=False),
        Binding("2", "quickslot(1)", "Quick 2", show=False),
        Binding("3", "quickslot(2)", "Quick 3", show=False),
        Binding("4", "quickslot(3)", "Quick 4", show=False),
        Binding("exclamation_mark", "clear_quickslot(0)", "Clear 1", show=False),
        Binding("at", "clear_quickslot(1)", "Clear 2", show=False),
        Binding("number_sign", "clear_quickslot(2)", "Clear 3", show=False),
        Binding("dollar_sign", "clear_quickslot(3)", "Clear 4", show=False),
        Binding("s", "save_quit", "Save+Quit"),
        Binding("r", "rest", "Rest"),
        Binding("question_mark", "help", "Help", key_display="?"),
    ]

    def __init__(
        self,
        seed: int,
        use_ascii: bool = False,
        portrait_style: str = "box",
        game: Game | None = None,
        origin: str = "wygnaniec",
        lang: str = "en",
        narrator_mode: str = "template",
        llm_config: dict | None = None,
        hints: bool = True,
        quickslot_auto_refill: bool = True,
        glebiej: bool = False,
        audio_config: dict | None = None,
        mute: bool = False,
        pack_notes: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.game = game if game is not None else Game(seed, origin=origin, glebiej=glebiej)
        self.game.quickslot_auto_refill = quickslot_auto_refill
        self._quickslot_hinted = False
        self.use_ascii = use_ascii
        self.portrait_style = portrait_style
        self.lang = lang
        registry = build_form_registry(
            {**self.game.bestiary, **self.game.items_catalog, **self.game.hooks_catalog}, lang
        )
        fallback = load_pack("en") if lang != "en" else None
        template_narrator = TemplateNarrator(
            load_pack(lang), self.game.rng.narration, registry, fallback_pack=fallback
        )
        narrator: TemplateNarrator | LLMNarrator = template_narrator
        if narrator_mode == "llm":
            config = llm_config or {}
            narrator = LLMNarrator(
                template_narrator,
                build_backend(config),
                timeout=float(config.get("timeout", DEFAULT_TIMEOUT)),
            )
        enricher = ContextEnricher(self.game)
        self.narration = NarrationEngine(self.game.bus, narrator, enricher=enricher.enrich)
        self.narration.add_sink(self._on_narration)
        self.game.bus.subscribe(TalkedTo, self._on_talked_to)
        self.game.bus.subscribe(StashOpened, self._on_stash_opened)
        self.game.bus.subscribe(ShrineVisited, self._on_shrine_visited)
        self.szept = SzeptSystem(
            self.game,
            table=load_szept(lang),
            sink=self._on_szept,
            enabled=hints,
        )
        # M11 "Głosy": one more listener on the bus; absent or refused =
        # identically silent, one dim note aside.
        self.audio: AudioSystem | None = None
        self._audio_note = False
        self._pack_notes = list(pack_notes or [])
        cfg = audio_config or {}
        if bool(cfg.get("enabled", True)) and not mute:
            try:
                backend: AudioBackend = PygameBackend()
            except AudioUnavailable:
                self._audio_note = True  # noted once at launch, then never again
            else:
                self.audio = AudioSystem(
                    self.game,
                    load_audio_catalog(),
                    backend,
                    master=float(cfg.get("master", 0.8)),
                    ambient=float(cfg.get("ambient", 0.7)),
                    sfx=float(cfg.get("sfx", 0.8)),
                )

    def compose(self) -> ComposeResult:
        with Horizontal(id="top"):
            yield MapView(self.game, use_ascii=self.use_ascii)
            yield CharacterPanel(
                self.game, portrait_style=self.portrait_style, use_ascii=self.use_ascii
            )
        yield RichLog(id="narrative", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.border_title = t("panel_tale")
        intro = self.game.origin.intro_for(self.lang).strip().replace("\n", " ")
        log.write(Text(intro, style="italic grey74"))
        log.write(Text(t("intro_second"), style="italic grey58"))
        if self._audio_note:
            log.write(Text(t("audio_missing"), style="italic grey42"))
        for note in self._pack_notes:
            log.write(Text(t("pack_skipped", note=note), style="italic grey42"))

    def on_unmount(self) -> None:
        if self.audio is not None:
            self.audio.shutdown()

    def _on_szept(self, text: str) -> None:
        if self.is_running:
            log = self.query_one(RichLog)
            log.write(Text(""))
            log.write(Text(text, style="italic grey42"))

    def _on_narration(self, line: NarrationLine) -> None:
        if self.is_running:
            if line.importance == "high":
                style = "bold red3"
            else:
                style = CATEGORY_STYLES.get(line.category, "grey74")
            log = self.query_one(RichLog)
            log.write(Text(""))
            log.write(Text(line.text, style=style))

    def on_key(self, event: events.Key) -> None:
        if len(self.screen_stack) > 1:
            return  # a modal is open; it owns the keys
        if event.key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[event.key]
            self._play(Move(dx, dy))
        elif event.character == ">":
            self._play(Descend())
        elif event.character == "<":
            self._play(Ascend())

    def action_wait(self) -> None:
        self._play(Wait())

    def action_get(self) -> None:
        self._play(Get())

    def action_rest(self) -> None:
        self._play(Rest())

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_equip(self) -> None:
        def on_result(action: Action | None) -> None:
            if action is not None:
                self._play(action)

        self.push_screen(EquipScreen(self.game), on_result)

    def action_quickslot(self, index: int) -> None:
        if self.game.quickslot_entity(index) is None:
            if not self._quickslot_hinted:  # szept-style aside, first time only
                self._quickslot_hinted = True
                log = self.query_one(RichLog)
                log.write(Text(""))
                log.write(Text(t("quickslot_empty_hint"), style="italic grey50"))
            return  # no turn spent on an empty slot (spec §5.1)
        self._play(UseQuickslot(index))

    def action_clear_quickslot(self, index: int) -> None:
        self._play(ClearQuickslot(index))

    def _on_stash_opened(self, event: StashOpened) -> None:
        if not self.is_running:
            return

        def on_result(action: Action | None) -> None:
            if action is not None:
                self._play(action)
                # Re-open so multi-item stashing is one visit, not many bumps.
                self.call_after_refresh(self.push_screen, StashScreen(self.game), on_result)

        self.call_after_refresh(self.push_screen, StashScreen(self.game), on_result)

    def _on_shrine_visited(self, event: ShrineVisited) -> None:
        if not self.is_running:
            return

        def on_result(action: Action | None) -> None:
            if action is not None:
                self._play(action)

        self.call_after_refresh(self.push_screen, ShrineScreen(self.game, event.god), on_result)

    def _on_talked_to(self, event: TalkedTo) -> None:
        if event.role in ("trader", "dziad_wedrowny") and self.is_running:

            def on_result(action: Action | None) -> None:
                if action is not None:
                    self._play(action)

            self.call_after_refresh(
                self.push_screen, TradeScreen(self.game, event.villager.entity), on_result
            )

    def action_confirm_quit(self) -> None:
        if self.game.game_over:
            self.exit("quit")
            return

        def on_result(confirmed: bool | None) -> None:
            if confirmed:
                self.exit("quit")

        self.push_screen(ConfirmQuitScreen(), on_result)

    def action_save_quit(self) -> None:
        if not self.game.game_over:
            save_game(self.game)
        self.exit("quit")

    def action_examine(self) -> None:
        self.push_screen(ExamineScreen(self.game))

    def action_codex(self) -> None:
        self.push_screen(CodexScreen(self.game))

    def action_legend(self) -> None:
        self.push_screen(LegendScreen(self.game, self.use_ascii))

    def action_inventory(self) -> None:
        def on_result(action: Action | None) -> None:
            if action is not None:
                self._play(action)

        self.push_screen(InventoryScreen(self.game), on_result)

    def _play(self, action: Action) -> None:
        if self.game.game_over:
            return
        hp_before = self.game.world.expect(self.game.player, Health).hp
        self.game.step(action)
        health = self.game.world.get(self.game.player, Health)
        if health is not None and health.hp < hp_before and not self.game.game_over:
            self.query_one(MapView).flash_damage()
        self.query_one(MapView).refresh()
        self.query_one(CharacterPanel).refresh()
        if self.game.game_over:
            delete_save()  # the run is over, won or lost
            if isinstance(self.narration.narrator, LLMNarrator):
                self.query_one(RichLog).write(
                    Text(self.narration.narrator.stats.summary(), style="grey42")
                )
            if self.game.victory:
                now = datetime.now()
                self.game.apply_victory_to_meta()
                write_morgue(self.game, when=now, victory=True)
                record_run(
                    seed=self.game.seed,
                    origin=self.game.origin.key,
                    turns=self.game.turn,
                    max_depth=self.game.max_depth_reached,
                    cause="the lids stayed shut",
                    when=now,
                )
                self.exit(f"victory:{self.game.victory_epilogue}")
                return
            new_origins = self.game.apply_death_to_meta()
            now = datetime.now()
            morgue_path = write_morgue(self.game, when=now)
            record_run(
                seed=self.game.seed,
                origin=self.game.origin.key,
                turns=self.game.turn,
                max_depth=self.game.max_depth_reached,
                cause=self.game.death_cause or "lost to the forest",
                when=now,
            )
            unlock_names = [self.game.origins_catalog[k].name for k in new_origins]
            self.push_screen(
                DeathScreen(
                    seed=self.game.seed,
                    turn=self.game.turn,
                    cause=self.game.death_cause,
                    morgue_path=str(morgue_path),
                    unlocked=unlock_names,
                )
            )
