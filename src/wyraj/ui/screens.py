"""Secondary screens: death screen, inventory modal."""

import string
from typing import ClassVar

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import ModalScreen, Screen
from textual.widgets import Static

from wyraj.core.actions import (
    Action,
    BuyItem,
    DepositItem,
    MakeOffering,
    SellItem,
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
from wyraj.core.systems.movement import level_of
from wyraj.ui.i18n import t


class DeathScreen(Screen[None]):
    BINDINGS: ClassVar = [("q", "quit_app", "Quit")]

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
        text.append("\n" + t("death_quit"), style="grey42")
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
        for letter, entity, name, kind in self.entries:
            text.append(f" {letter}", style="bold gold3")
            text.append(f" — {name}")
            if entity == wielded:
                text.append(" " + t("mark_wielded"), style="grey58")
            elif entity == worn:
                text.append(" " + t("mark_worn"), style="grey58")
            elif verbs[kind]:
                text.append(f"  [{verbs[kind]}]", style="grey42")
            text.append("\n")
        text.append("\n" + t("esc_close"), style="grey42")
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
                elif kind == "armor":
                    self.dismiss(WearItem(entity))
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
            result.append((letter, entity, lore.name if lore else "something", key))
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
            text.append(f" {letter}", style="bold cyan" if affordable else "grey42")
            text.append(f" — {name} ", style="" if affordable else "grey42")
            text.append(f"({price})\n", style="gold3" if affordable else "grey42")
        text.append("\n" + t("trade_sell") + "\n", style="grey58")
        if not self.mine:
            text.append(" " + t("trade_nothing") + "\n", style="grey42")
        for letter, _entity, name, key in self.mine:
            text.append(f" {letter}", style="bold gold3")
            text.append(f" — {name} ")
            text.append(f"(+{game.sell_price_for(key)})\n", style="gold3")
        text.append("\n" + t("trade_esc"), style="grey42")
        with Middle(), Center():
            yield Static(text)

    def on_key(self, event: events.Key) -> None:
        event.stop()
        if event.key == "escape":
            return
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
        with Middle(), Center():
            yield Static(text)

    def on_key(self, event: events.Key) -> None:
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
        self.mine: list[tuple[str, int, str]] = []
        for letter, entity in zip(string.ascii_lowercase, player_inv.items, strict=False):
            lore = game.world.get(entity, Lore)
            self.mine.append((letter, entity, lore.name if lore else "something"))
        self.stashed: list[tuple[str, int, str]] = []
        for i, (letter, stashed) in enumerate(
            zip(string.ascii_uppercase, game.meta.stash.items, strict=False)
        ):
            definition = game.items_catalog.get(stashed.item_id)
            name = definition.name if definition else stashed.item_id
            label = f"{name} x{stashed.count}" if stashed.count > 1 else name
            self.stashed.append((letter, i, label))

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
        for letter, _i, label in self.stashed:
            text.append(f" {letter}", style="bold cyan")
            text.append(f" — {label}\n")
        text.append("\n" + t("stash_carrying") + "\n", style="grey58")
        if not self.mine:
            text.append(" " + t("pack_empty") + "\n", style="grey42")
        for letter, _entity, name in self.mine:
            text.append(f" {letter}", style="bold gold3")
            text.append(f" — {name}\n")
        upgrades = game.prices.stash_upgrades
        step = (meta.stash.slots_total - 4) // 2
        if step < len(upgrades) and meta.stash.slots_total < 10:
            text.append("\n" + t("stash_upgrade_offer", price=upgrades[step]) + "\n", style="gold3")
        text.append("\n" + t("esc_close"), style="grey42")
        with Middle(), Center():
            yield Static(text)

    def on_key(self, event: events.Key) -> None:
        event.stop()
        if event.key == "escape":
            return
        if event.key == "u":
            self.dismiss(UpgradeStash())
            return
        for letter, entity, _name in self.mine:
            if event.key == letter:
                self.dismiss(DepositItem(item=entity))
                return
        for letter, index, _label in self.stashed:
            if event.key == letter:
                self.dismiss(WithdrawStash(index=index))
                return

    def action_close(self) -> None:
        self.dismiss(None)


class ExamineScreen(ModalScreen[None]):
    """What the player currently sees, with lore."""

    BINDINGS: ClassVar = [("escape", "close", "Close"), ("x", "close", "Close")]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game

    def compose(self) -> ComposeResult:
        game = self.game
        text = Text()
        text.append(t("examine_title") + "\n\n", style="bold")
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
            text.append(" " + t("lies_here") + "\n", style="grey58")
        for entity, (_hook, lore, pos) in game.world.query(StoryHook, Lore, Position):
            if level_of(game.world, entity) != game.depth:
                continue
            if (pos.x, pos.y) not in game.map.visible:
                continue
            seen_something = True
            text.append(f" {lore.name}\n", style="bold medium_purple3")
            if lore.description:
                text.append(f"   {lore.description.strip()}\n\n", style="grey66")
        if not seen_something:
            text.append(t("examine_nothing") + "\n", style="grey58")
        text.append("\n" + t("esc_close"), style="grey42")
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

    def _trophy_line(self, key: str) -> str:
        game = self.game
        spec = game.drops.get(key)
        if spec is None:
            return ""
        parts = []
        if spec.denary is not None:
            parts.append(t("codex_carries_silver"))
        for trophy in spec.trophies:
            definition = game.items_catalog.get(trophy.item)
            if definition is not None:
                parts.append(f"{definition.name} ({game.sell_price_for(trophy.item)})")
        return ", ".join(parts)

    def compose(self) -> ComposeResult:
        game = self.game
        text = Text()
        text.append(t("codex_title") + "\n\n", style="bold")
        for key in sorted(game.bestiary):
            definition = game.bestiary[key]
            tier = game.codex_tier(key)
            if tier == "unknown":
                text.append(" " + t("codex_unseen") + "\n\n", style="grey30")
                continue
            text.append(f" {definition.name}", style="bold")
            text.append(f"  [{t('codex_tier_' + tier)}]", style="grey42")
            if definition.epithets:
                text.append(f" — {', '.join(definition.epithets)}", style="italic grey58")
            text.append("\n")
            if tier in ("partial", "full"):
                trophies = self._trophy_line(key)
                if trophies:
                    text.append(f"   {t('codex_trophies')}: {trophies}\n", style="gold3")
            if tier == "full":
                if definition.weakness:
                    text.append(
                        f"   {t('codex_weakness')}: {definition.weakness}\n",
                        style="medium_purple3",
                    )
                text.append(f"   {definition.description.strip()}\n", style="grey66")
            text.append("\n")
        text.append(t("esc_close"), style="grey42")
        with Middle(), Center():
            yield Static(text)

    def action_close(self) -> None:
        self.dismiss(None)
