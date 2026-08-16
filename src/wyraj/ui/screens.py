"""Secondary screens: death screen, inventory modal."""

import string
from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static

from wyraj.core.actions import (
    Action,
    BindQuickslot,
    BuyItem,
    DepositItem,
    MakeOffering,
    SellItem,
    UnequipSlot,
    UpgradeStash,
    UseItem,
    WearItem,
    WieldItem,
    WithdrawStash,
)
from wyraj.core.components import (
    AI,
    Health,
    Inventory,
    Item,
    Lore,
    Position,
    StoryHook,
    Wearing,
    Wielding,
)
from wyraj.core.game import Game
from wyraj.core.map import Tile
from wyraj.core.systems.movement import level_of
from wyraj.ui.codex_view import build_codex_text, build_errands_text
from wyraj.ui.i18n import t
from wyraj.ui.item_info import display_name, stat_suffix
from wyraj.ui.legend_view import build_legend_text
from wyraj.ui.paper_doll import doll_slots_for


class ConfirmQuitScreen(ModalScreen[bool]):
    """`q` mid-run: abandoning without saving deserves a second thought."""

    BINDINGS: ClassVar = [("escape", "stay", "Stay")]

    def compose(self) -> ComposeResult:
        text = Text()
        text.append(t("quit_confirm") + "\n\n", style="bold")
        text.append(t("quit_confirm_hint"), style="grey58")
        yield Static(text, classes="dialog")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            return  # let it bubble so the Escape binding closes the modal
        event.stop()
        if event.key in ("y", "t"):  # EN yes / PL tak
            self.dismiss(True)
        elif event.key == "n":
            self.dismiss(False)

    def action_stay(self) -> None:
        self.dismiss(False)


class DeathScreen(ModalScreen[None]):
    """Permadeath epilogue: set out again, return to the title, or leave."""

    BINDINGS: ClassVar = [
        ("n", "new_run", "New run"),
        ("m", "main_screen", "Main screen"),
        ("q", "quit_app", "Quit"),
    ]

    def __init__(
        self,
        seed: int,
        turn: int,
        cause: str | None = None,
        morgue_path: str | None = None,
        unlocked: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.seed = seed
        self.turn = turn
        self.cause = cause
        self.morgue_path = morgue_path
        self.unlocked = unlocked or []

    def compose(self) -> ComposeResult:
        text = Text(justify="center")
        text.append(t("death_title") + "\n\n", style="bold red3")
        if self.cause:
            text.append(f"{self.cause.capitalize()}.\n", style="grey74")
        text.append(t("death_lasted", n=self.turn) + "\n", style="grey74")
        text.append(t("death_seed", seed=self.seed) + "\n", style="grey58")
        if self.morgue_path:
            text.append(t("death_morgue", path=self.morgue_path) + "\n", style="grey42")
        for name in self.unlocked:
            text.append("\n" + t("death_unlock", name=name) + "\n", style="bold gold3")
        text.append("\n" + t("death_options"), style="grey42")
        yield Static(text, classes="dialog")

    def action_new_run(self) -> None:
        self.app.exit("restart")

    def action_main_screen(self) -> None:
        self.app.exit("title")

    def action_quit_app(self) -> None:
        self.app.exit("quit")


class InventoryScreen(ModalScreen[Action | None]):
    """List carried items; a letter uses/wields/wears, `1-4` then a letter binds."""

    BINDINGS: ClassVar = [("escape", "close", "Close")]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        self.bind_slot: int | None = None
        inventory = game.world.get(game.player, Inventory) or Inventory()
        self.entries: list[tuple[str, int, str, str, str, str | None]] = []
        for letter, entity in zip(string.ascii_lowercase, inventory.items, strict=False):
            lore = game.world.get(entity, Lore)
            item = game.world.get(entity, Item)
            definition = game.items_catalog.get(item.key) if item else None
            name = display_name(definition, fallback=lore.name if lore else "something")
            kind = item.kind if item else "trinket"
            slot = definition.slot if definition else None
            self.entries.append((letter, entity, name, kind, stat_suffix(definition), slot))

    def _text(self) -> Text:
        text = Text()
        text.append(t("pack_title") + "\n\n", style="bold")
        if not self.entries:
            text.append(t("pack_empty") + "\n", style="grey58")
        wielding = self.game.world.get(self.game.player, Wielding)
        wielded = wielding.item if wielding else None
        wearing = self.game.world.get(self.game.player, Wearing)
        worn = wearing.item if wearing else None
        verbs = {
            "consumable": t("verb_use"),
            "weapon": t("verb_wield"),
            "armor": t("verb_wear"),
            "trinket": "",
        }
        for letter, entity, name, kind, suffix, slot in self.entries:
            verb = t("verb_wear") if kind == "trinket" and slot else verbs.get(kind, "")
            text.append(f" {letter}", style="bold gold3")
            text.append(f" — {name}")
            if suffix:
                text.append(f" {suffix}", style="grey58")
            if entity == wielded:
                text.append(" " + t("mark_wielded"), style="grey58")
            elif entity == worn:
                text.append(" " + t("mark_worn"), style="grey58")
            elif verb:
                text.append(f"  [{verb}]", style="grey42")
            text.append("\n")
        if self.bind_slot is not None:
            text.append("\n" + t("pack_bind_prompt", n=self.bind_slot + 1), style="gold3")
        else:
            text.append("\n" + t("pack_bind_hint"), style="grey42")
        text.append("\n" + t("esc_close"), style="grey42")
        return text

    def compose(self) -> ComposeResult:
        yield Static(self._text(), classes="dialog")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            return  # let it bubble so the Escape binding closes the modal
        event.stop()
        if event.key in ("1", "2", "3", "4"):
            self.bind_slot = int(event.key) - 1
            self.query_one(Static).update(self._text())
            return
        for letter, entity, _name, kind, _suffix, slot in self.entries:
            if event.key != letter:
                continue
            if self.bind_slot is not None:
                if kind == "consumable":
                    self.dismiss(BindQuickslot(index=self.bind_slot, item=entity))
                return
            if kind == "consumable":
                self.dismiss(UseItem(entity))
            elif kind == "weapon":
                self.dismiss(WieldItem(entity))
            elif kind == "armor" or (kind == "trinket" and slot):
                self.dismiss(WearItem(entity))
            # slotless trinkets/trophies have no verb — stay open instead of closing
            return

    def action_close(self) -> None:
        self.dismiss(None)


class EquipScreen(ModalScreen[Action | None]):
    """`e` — the paper-doll; a slot's letter frees it back into the pack."""

    BINDINGS: ClassVar = [("escape", "close", "Close")]

    SLOT_LETTERS = "abcdef"

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        self.slots = doll_slots_for(game)

    def compose(self) -> ComposeResult:
        text = Text()
        text.append(t("equip_title") + "\n\n", style="bold")
        for letter, entry in zip(self.SLOT_LETTERS, self.slots, strict=False):
            removable = entry.name is not None and entry.slot != "off"
            text.append(f" {letter}", style="bold gold3" if removable else "grey42")
            text.append(f" — {t('doll_' + entry.slot):<7}", style="grey58")
            if entry.name is None:
                text.append("—\n", style="grey42")
            else:
                text.append(entry.name)
                if entry.epithet:
                    text.append(f" „{entry.epithet}”", style="italic gold3")
                if entry.detail:
                    text.append(f" {entry.detail}", style="grey58")
                text.append("\n")
        text.append("\n" + t("equip_hint"), style="grey42")
        text.append("\n" + t("esc_close"), style="grey42")
        yield Static(text, classes="dialog")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            return  # let it bubble so the Escape binding closes the modal
        event.stop()
        for letter, entry in zip(self.SLOT_LETTERS, self.slots, strict=False):
            if event.key == letter and entry.name is not None and entry.slot != "off":
                self.dismiss(UnequipSlot(slot=entry.slot))
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


class TradeScreen(ModalScreen[Action | None]):
    """Coin trade (M6): A-Z buys from the stock, a-z sells from your pack."""

    BINDINGS: ClassVar = [("escape", "close", "Close")]

    def __init__(self, game: Game, trader: int) -> None:
        super().__init__()
        self.game = game
        self.trader = trader
        player_inv = game.world.get(game.player, Inventory) or Inventory()
        trader_inv = game.world.get(trader, Inventory) or Inventory()
        self.mine = self._entries(player_inv, string.ascii_lowercase)
        self.theirs = self._entries(trader_inv, string.ascii_uppercase)

    def _entries(self, inventory: Inventory, letters: str) -> list[tuple[str, int, str, str]]:
        result = []
        for letter, entity in zip(letters, inventory.items, strict=False):
            lore = self.game.world.get(entity, Lore)
            item = self.game.world.get(entity, Item)
            key = item.key if item else ""
            name = display_name(
                self.game.items_catalog.get(key), fallback=lore.name if lore else "something"
            )
            result.append((letter, entity, name, key))
        return result

    def compose(self) -> ComposeResult:
        game = self.game
        text = Text()
        text.append(t("trade_title") + "\n", style="bold")
        text.append(t("trade_wallet", n=game._wallet_total()) + "\n\n", style="gold3")
        text.append(t("trade_stock") + "\n", style="grey58")
        if not self.theirs:
            text.append(" —\n", style="grey42")
        for letter, _entity, name, key in self.theirs:
            price = game.price_for(key, self.trader)
            affordable = game._wallet_total() >= price
            suffix = stat_suffix(game.items_catalog.get(key))
            text.append(f" {letter}", style="bold cyan" if affordable else "grey42")
            text.append(f" — {name} ", style="" if affordable else "grey42")
            if suffix:
                text.append(f"{suffix} ", style="grey58" if affordable else "grey42")
            text.append(f"({price})\n", style="gold3" if affordable else "grey42")
        text.append("\n" + t("trade_sell") + "\n", style="grey58")
        if not self.mine:
            text.append(" " + t("trade_nothing") + "\n", style="grey42")
        for letter, _entity, name, key in self.mine:
            suffix = stat_suffix(game.items_catalog.get(key))
            text.append(f" {letter}", style="bold gold3")
            text.append(f" — {name} ")
            if suffix:
                text.append(f"{suffix} ", style="grey58")
            text.append(f"(+{game.sell_price_for(key)})\n", style="gold3")
        text.append("\n" + t("trade_esc"), style="grey42")
        yield Static(text, classes="dialog")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            return  # let it bubble so the Escape binding closes the modal
        event.stop()
        for letter, entity, _name, _key in self.theirs:
            if event.key == letter:
                self.dismiss(BuyItem(trader=self.trader, item=entity))
                return
        for letter, entity, _name, _key in self.mine:
            if event.key == letter:
                self.dismiss(SellItem(trader=self.trader, item=entity))
                return

    def action_close(self) -> None:
        self.dismiss(None)


class HelpScreen(ModalScreen[None]):
    """`?` — the complete reference, in-voice ("Próg" spec §6)."""

    BINDINGS: ClassVar = [("escape", "close", "Close"), ("question_mark", "close", "Close")]

    def compose(self) -> ComposeResult:
        from wyraj.content.intro import load_help
        from wyraj.ui.i18n import current_language

        help_text = load_help(current_language())
        text = Text()
        text.append(help_text.title + "\n\n", style="bold")
        for line in help_text.keys:
            text.append(f" {line}\n", style="grey74")
        text.append("\n")
        for paragraph in help_text.world:
            text.append(paragraph.strip().replace("\n", " ") + "\n\n", style="italic grey62")
        text.append(t("esc_close"), style="grey42")
        yield Static(text, classes="dialog")

    def action_close(self) -> None:
        self.dismiss(None)


class ShrineScreen(ModalScreen[Action | None]):
    """Offer denary for a run-scoped favor; escape leaves the god waiting."""

    BINDINGS: ClassVar = [("escape", "close", "Close")]

    def __init__(self, game: Game, god: str) -> None:
        super().__init__()
        self.game = game
        self.god = god

    def compose(self) -> ComposeResult:
        game = self.game
        spec = game.offerings.get(self.god)
        text = Text()
        text.append(t(f"shrine_title_{self.god}") + "\n\n", style="bold")
        if spec is not None:
            if game.meta.currency.denary >= spec.cost:
                text.append(t("shrine_offer", cost=spec.cost) + "\n", style="gold3")
            else:
                text.append(t("shrine_broke") + "\n", style="grey42")
        text.append("\n" + t("esc_close"), style="grey42")
        yield Static(text, classes="dialog")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            return  # let it bubble so the Escape binding closes the modal
        event.stop()
        if event.key == "o":
            self.dismiss(MakeOffering(god=self.god))

    def action_close(self) -> None:
        self.dismiss(None)


class StashScreen(ModalScreen[Action | None]):
    """The skrzynia: a-z deposits from your pack, A-Z withdraws, 'u' upgrades."""

    BINDINGS: ClassVar = [("escape", "close", "Close")]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        player_inv = game.world.get(game.player, Inventory) or Inventory()
        self.mine: list[tuple[str, int, str, str]] = []
        for letter, entity in zip(string.ascii_lowercase, player_inv.items, strict=False):
            lore = game.world.get(entity, Lore)
            item = game.world.get(entity, Item)
            definition = game.items_catalog.get(item.key) if item else None
            name = display_name(definition, fallback=lore.name if lore else "something")
            self.mine.append((letter, entity, name, stat_suffix(definition)))
        self.stashed: list[tuple[str, int, str, str]] = []
        for i, (letter, stashed) in enumerate(
            zip(string.ascii_uppercase, game.meta.stash.items, strict=False)
        ):
            definition = game.items_catalog.get(stashed.item_id)
            name = display_name(definition, fallback=stashed.item_id)
            label = f"{name} x{stashed.count}" if stashed.count > 1 else name
            self.stashed.append((letter, i, label, stat_suffix(definition)))

    def compose(self) -> ComposeResult:
        game = self.game
        meta = game.meta
        text = Text()
        text.append(t("stash_title") + "\n", style="bold")
        text.append(
            t("stash_slots", used=len(meta.stash.items), total=meta.stash.slots_total) + "\n\n",
            style="grey58",
        )
        text.append(t("stash_stored") + "\n", style="grey58")
        if not self.stashed:
            text.append(" " + t("stash_empty") + "\n", style="grey42")
        for letter, _i, label, suffix in self.stashed:
            text.append(f" {letter}", style="bold cyan")
            text.append(f" — {label}")
            if suffix:
                text.append(f" {suffix}", style="grey58")
            text.append("\n")
        text.append("\n" + t("stash_carrying") + "\n", style="grey58")
        if not self.mine:
            text.append(" " + t("pack_empty") + "\n", style="grey42")
        for letter, _entity, name, suffix in self.mine:
            text.append(f" {letter}", style="bold gold3")
            text.append(f" — {name}")
            if suffix:
                text.append(f" {suffix}", style="grey58")
            text.append("\n")
        upgrades = game.prices.stash_upgrades
        step = (meta.stash.slots_total - 4) // 2
        if step < len(upgrades) and meta.stash.slots_total < 10:
            text.append("\n" + t("stash_upgrade_offer", price=upgrades[step]) + "\n", style="gold3")
        text.append("\n" + t("esc_close"), style="grey42")
        yield Static(text, classes="dialog")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            return  # let it bubble so the Escape binding closes the modal
        event.stop()
        if event.key == "u":
            self.dismiss(UpgradeStash())
            return
        for letter, entity, _name, _suffix in self.mine:
            if event.key == letter:
                self.dismiss(DepositItem(item=entity))
                return
        for letter, index, _label, _suffix in self.stashed:
            if event.key == letter:
                self.dismiss(WithdrawStash(index=index))
                return

    def action_close(self) -> None:
        self.dismiss(None)


_EXAMINE_TILES = (
    (Tile.STAIRS_DOWN, "examine_stairs_down"),
    (Tile.STAIRS_UP, "examine_stairs_up"),
    (Tile.SHAFT, "examine_shaft"),
    (Tile.WATER, "examine_water"),
)


def build_examine_text(game: Game) -> Text:
    """Everything in sight, with lore: creatures, items, hooks, features, terrain."""
    text = Text()
    text.append(t("examine_title") + "\n\n", style="bold")
    seen_something = False
    shown: set[int] = set()

    def visible(entity: int, pos: Position) -> bool:
        return level_of(game.world, entity) == game.depth and (pos.x, pos.y) in game.map.visible

    for entity, (_ai, lore, pos, health) in game.world.query(AI, Lore, Position, Health):
        if not visible(entity, pos):
            continue
        seen_something = True
        shown.add(entity)
        text.append(f" {lore.name}", style="bold red3")
        if lore.epithets:
            text.append(f" — {lore.epithets[0]}", style="italic grey58")
        text.append(f" ({_hp_word(health)})\n", style="grey58")
        if lore.description:
            text.append(f"   {lore.description.strip()}\n\n", style="grey66")
    for entity, (item, lore, pos) in game.world.query(Item, Lore, Position):
        if not visible(entity, pos):
            continue
        seen_something = True
        shown.add(entity)
        definition = game.items_catalog.get(item.key)
        text.append(f" {display_name(definition, fallback=lore.name)}", style="gold3")
        suffix = stat_suffix(definition)
        if suffix:
            text.append(f" {suffix}", style="grey58")
        text.append(" " + t("lies_here") + "\n", style="grey58")
    for entity, (_hook, lore, pos) in game.world.query(StoryHook, Lore, Position):
        if not visible(entity, pos):
            continue
        seen_something = True
        shown.add(entity)
        text.append(f" {lore.name}\n", style="bold medium_purple3")
        if lore.description:
            text.append(f"   {lore.description.strip()}\n\n", style="grey66")
    # Features and folk: anything else that carries lore — shrines, the
    # skrzynia, the żerdź, the znamię, villagers, the dziad's cart.
    for entity, (lore, pos) in game.world.query(Lore, Position):
        if entity in shown or entity == game.player or not visible(entity, pos):
            continue
        seen_something = True
        text.append(f" {lore.name}\n", style="bold light_goldenrod2")
        if lore.description:
            text.append(f"   {lore.description.strip()}\n\n", style="grey66")
    # Notable terrain in sight: ways down and up, sky shafts, water.
    in_sight = {game.map.tiles[y][x] for x, y in game.map.visible}
    for tile, key in _EXAMINE_TILES:
        if tile in in_sight:
            seen_something = True
            text.append(" " + t(key) + "\n", style="grey66")
    if not seen_something:
        text.append(t("examine_nothing") + "\n", style="grey58")
    text.append("\n" + t("esc_close"), style="grey42")
    return text


class ExamineScreen(ModalScreen[None]):
    """What the player currently sees, with lore."""

    BINDINGS: ClassVar = [("escape", "close", "Close"), ("x", "close", "Close")]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game

    def compose(self) -> ComposeResult:
        yield Static(build_examine_text(self.game), classes="dialog")

    def action_close(self) -> None:
        self.dismiss(None)


class LegendScreen(ModalScreen[None]):
    """What every mark on the map means; creatures appear as the codex learns them."""

    BINDINGS: ClassVar = [("escape", "close", "Close"), ("L", "close", "Close")]

    def __init__(self, game: Game, use_ascii: bool = False) -> None:
        super().__init__()
        self.game = game
        self.use_ascii = use_ascii

    def compose(self) -> ComposeResult:
        text = build_legend_text(
            items_catalog=self.game.items_catalog,
            bestiary=self.game.bestiary,
            tier_of=self.game.codex_tier,
            use_ascii=self.use_ascii,
        )
        yield Static(text, classes="dialog")

    def action_close(self) -> None:
        self.dismiss(None)


class CodexScreen(ModalScreen[None]):
    """Codex: bestiary folklore plus the Zlecenia ledger (Tab cycles)."""

    BINDINGS: ClassVar = [
        ("escape", "close", "Close"),
        ("c", "close", "Close"),
        ("tab", "toggle_tab", "Zlecenia"),
    ]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        self.show_errands = False

    def _text(self) -> Text:
        game = self.game
        if self.show_errands:
            return build_errands_text(
                catalog=game.errands_catalog,
                run_errands=game.errands,
                meta=game.meta,
                bestiary=game.bestiary,
                items_catalog=game.items_catalog,
            )
        return build_codex_text(
            bestiary=game.bestiary,
            items_catalog=game.items_catalog,
            drops=game.drops,
            sell_price_for=game.sell_price_for,
            tier_of=game.codex_tier,
        )

    def compose(self) -> ComposeResult:
        yield Static(self._text(), classes="dialog")

    def action_toggle_tab(self) -> None:
        self.show_errands = not self.show_errands
        self.query_one(Static).update(self._text())

    def action_close(self) -> None:
        self.dismiss(None)
