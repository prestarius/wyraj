from wyraj.core.actions import DepositItem, Move, UpgradeStash, WieldItem, WithdrawStash
from wyraj.core.components import Inventory, Item, ItemMemory, Position, StashChest
from wyraj.core.events import (
    HeirloomWielded,
    StashDeposited,
    StashOpened,
    StashUpgraded,
    StashWithdrawn,
)
from wyraj.core.game import Game
from wyraj.persistence.meta import MetaState


def new_game(meta: MetaState | None = None) -> Game:
    return Game(seed=42, meta=meta or MetaState(), meta_autosave=False)


def give(game: Game, key: str) -> int:
    entity = game.spawn_stock_item(key)
    inv = game.world.get(game.player, Inventory) or Inventory()
    game.world.add(game.player, Inventory(items=(*inv.items, entity)))
    return entity


def test_bump_chest_opens_stash() -> None:
    game = new_game()
    chest = game.world.entities_with(StashChest)[0]
    cpos = game.world.expect(chest, Position)
    game.world.add(game.player, Position(cpos.x - 1, cpos.y))
    opened: list[StashOpened] = []
    game.bus.subscribe(StashOpened, opened.append)
    game.step(Move(1, 0))
    assert opened
    assert game.world.expect(game.player, Position) == Position(cpos.x - 1, cpos.y)


def test_deposit_and_withdraw_roundtrip() -> None:
    game = new_game()
    axe = give(game, "toporek")
    deposited: list[StashDeposited] = []
    game.bus.subscribe(StashDeposited, deposited.append)
    game.step(DepositItem(item=axe))
    assert deposited[0].item.key == "toporek"
    assert not game.world.is_alive(axe)
    assert game.meta.stash.items[0].item_id == "toporek"
    assert game.meta.stash.items[0].instance["memory_tag"] == game.run_tag

    withdrawn: list[StashWithdrawn] = []
    game.bus.subscribe(StashWithdrawn, withdrawn.append)
    game.step(WithdrawStash(index=0))
    assert game.meta.stash.items == []
    assert not withdrawn[0].heirloom  # same run — no heirloom aura
    inv = game.world.expect(game.player, Inventory).items
    assert any(game.world.expect(e, Item).key == "toporek" for e in inv)


def test_consumables_stack_and_capacity_holds() -> None:
    game = new_game()
    for _ in range(2):
        game.step(DepositItem(item=give(game, "odwar")))
    assert len(game.meta.stash.items) == 1
    assert game.meta.stash.items[0].count == 2

    # Fill remaining slots with equipment; the chest refuses the overflow.
    for key in ("toporek", "noz", "ciupaga", "kaftan"):
        game.step(DepositItem(item=give(game, key)))
    assert len(game.meta.stash.items) == 4  # capacity
    overflow = give(game, "wilcza_skora")
    game.step(DepositItem(item=overflow))
    assert game.world.is_alive(overflow), "full chest must refuse"


def test_heirloom_survives_death_and_remembers() -> None:
    meta = MetaState()
    first = Game(seed=1, meta=meta, meta_autosave=False)
    blade = first.spawn_stock_item("ciupaga")
    inv = first.world.get(first.player, Inventory) or Inventory()
    first.world.add(first.player, Inventory(items=(*inv.items, blade)))
    first.step(DepositItem(item=blade))
    assert meta.stash.items[0].instance["memory_tag"] == "run-1"

    # A later soul, a different run, the same chest.
    second = Game(seed=2, meta=meta, meta_autosave=False)
    withdrawn: list[StashWithdrawn] = []
    second.bus.subscribe(StashWithdrawn, withdrawn.append)
    second.step(WithdrawStash(index=0))
    assert withdrawn[0].heirloom
    item = next(
        e
        for e in second.world.expect(second.player, Inventory).items
        if second.world.expect(e, Item).key == "ciupaga"
    )
    assert second.world.get(item, ItemMemory) is not None

    heirloom: list[HeirloomWielded] = []
    second.bus.subscribe(HeirloomWielded, heirloom.append)
    second.step(WieldItem(item=item))
    assert heirloom and heirloom[0].item.key == "ciupaga"
    assert second.world.get(item, ItemMemory) is None  # remembers once


def test_stash_upgrade_costs_and_caps() -> None:
    game = new_game()
    game.meta.currency.denary = 10_000
    for expected_slots in (6, 8, 10):
        upgraded: list[StashUpgraded] = []
        game.bus.subscribe(StashUpgraded, upgraded.append)
        game.step(UpgradeStash())
        assert game.meta.stash.slots_total == expected_slots
        assert upgraded
    before = game.meta.currency.denary
    game.step(UpgradeStash())  # hard cap 10
    assert game.meta.stash.slots_total == 10
    assert game.meta.currency.denary == before


def test_upgrade_refused_when_broke() -> None:
    game = new_game()
    game.meta.currency.denary = 5
    game.step(UpgradeStash())
    assert game.meta.stash.slots_total == 4
