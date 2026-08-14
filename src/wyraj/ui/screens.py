"""Secondary screens: death screen, inventory modal."""

import string
from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import ModalScreen, Screen
from textual.widgets import Static

from wyraj.core.actions import Action, UseItem, WieldItem
from wyraj.core.components import AI, Health, Inventory, Item, Lore, Position, Wielding
from wyraj.core.game import Game
from wyraj.core.systems.movement import level_of


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


class InventoryScreen(ModalScreen[Action | None]):
    """List carried items; a letter uses/wields, escape closes."""

    BINDINGS: ClassVar = [("escape", "close", "Close")]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        inventory = game.world.get(game.player, Inventory) or Inventory()
        self.entries: list[tuple[str, int, str, str]] = []
        for letter, entity in zip(string.ascii_lowercase, inventory.items, strict=False):
            lore = game.world.get(entity, Lore)
            item = game.world.get(entity, Item)
            name = lore.name if lore else "something"
            kind = item.kind if item else "trinket"
            self.entries.append((letter, entity, name, kind))

    def compose(self) -> ComposeResult:
        text = Text()
        text.append("— Your pack —\n\n", style="bold")
        if not self.entries:
            text.append("Nothing but lint and resolve.\n", style="grey58")
        wielding = self.game.world.get(self.game.player, Wielding)
        wielded = wielding.item if wielding else None
        verbs = {"consumable": "use", "weapon": "wield", "trinket": ""}
        for letter, entity, name, kind in self.entries:
            text.append(f" {letter}", style="bold gold3")
            text.append(f" — {name}")
            if entity == wielded:
                text.append(" (wielded)", style="grey58")
            elif verbs[kind]:
                text.append(f"  [{verbs[kind]}]", style="grey42")
            text.append("\n")
        text.append("\nEsc to close.", style="grey42")
        with Middle(), Center():
            yield Static(text)

    def on_key(self, event: events.Key) -> None:
        event.stop()
        if event.key == "escape":
            return
        for letter, entity, _name, kind in self.entries:
            if event.key == letter:
                if kind == "consumable":
                    self.dismiss(UseItem(entity))
                elif kind == "weapon":
                    self.dismiss(WieldItem(entity))
                else:
                    self.dismiss(None)
                return

    def action_close(self) -> None:
        self.dismiss(None)


def _hp_word(health: Health) -> str:
    if health.fraction > 0.75:
        return "unhurt"
    if health.fraction > 0.5:
        return "scratched"
    if health.fraction > 0.25:
        return "bloodied"
    return "near death"


class ExamineScreen(ModalScreen[None]):
    """What the player currently sees, with lore."""

    BINDINGS: ClassVar = [("escape", "close", "Close"), ("x", "close", "Close")]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game

    def compose(self) -> ComposeResult:
        game = self.game
        text = Text()
        text.append("— What you see —\n\n", style="bold")
        seen_something = False
        for entity, (_ai, lore, pos, health) in game.world.query(AI, Lore, Position, Health):
            if level_of(game.world, entity) != game.depth:
                continue
            if (pos.x, pos.y) not in game.map.visible:
                continue
            seen_something = True
            text.append(f" {lore.name}", style="bold red3")
            if lore.epithets:
                text.append(f" — {lore.epithets[0]}", style="italic grey58")
            text.append(f" ({_hp_word(health)})\n", style="grey58")
            if lore.description:
                text.append(f"   {lore.description.strip()}\n\n", style="grey66")
        for entity, (_item, lore, pos) in game.world.query(Item, Lore, Position):
            if level_of(game.world, entity) != game.depth:
                continue
            if (pos.x, pos.y) not in game.map.visible:
                continue
            seen_something = True
            text.append(f" {lore.name}", style="gold3")
            text.append(" lies here.\n", style="grey58")
        if not seen_something:
            text.append("Only trees, and the spaces between them.\n", style="grey58")
        text.append("\nEsc to close.", style="grey42")
        with Middle(), Center():
            yield Static(text)

    def action_close(self) -> None:
        self.dismiss(None)


class CodexScreen(ModalScreen[None]):
    """Bestiary codex: folklore entries unlocked by seeing the creature."""

    BINDINGS: ClassVar = [("escape", "close", "Close"), ("c", "close", "Close")]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game

    def compose(self) -> ComposeResult:
        game = self.game
        text = Text()
        text.append("— Codex of the Puszcza —\n\n", style="bold")
        for key in sorted(game.bestiary):
            definition = game.bestiary[key]
            if key in game.codex_seen:
                text.append(f" {definition.name}", style="bold")
                if definition.epithets:
                    text.append(f" — {', '.join(definition.epithets)}", style="italic grey58")
                text.append("\n")
                text.append(f"   {definition.description.strip()}\n\n", style="grey66")
            else:
                text.append(" — a shape not yet seen —\n\n", style="grey30")
        text.append("Esc to close.", style="grey42")
        with Middle(), Center():
            yield Static(text)

    def action_close(self) -> None:
        self.dismiss(None)
