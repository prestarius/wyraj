"""M6 definition-of-done sim: 50 sequential runs sharing one meta-state.

Not a smart bot — a deterministic economic loop that exercises the real
transaction paths (scavenge → bank → sell → buy → upgrade → deposit → die)
and asserts the doctrine: heirlooms not a savings account, currency that
plateaus instead of piling up, and a meta file that stays valid and honest
through every cycle.
"""

import random
import statistics
from pathlib import Path

from wyraj.core.components import (
    AI,
    CoinPile,
    Health,
    Inventory,
    Item,
    Melee,
    OnLevel,
    Position,
    Purse,
    Villager,
)
from wyraj.core.game import Game
from wyraj.core.systems.combat import attack
from wyraj.core.systems.movement import level_of
from wyraj.persistence.meta import MetaState, load_meta, save_meta

RUNS = 50


def scavenge(game: Game, depths: tuple[int, ...]) -> None:
    total = 0
    for entity, (pile,) in list(game.world.query(CoinPile)):
        if level_of(game.world, entity) in depths:
            total += pile.amount
            game.world.destroy(entity)
    purse = game.world.get(game.player, Purse) or Purse()
    game.world.add(game.player, Purse(denary=purse.denary + total))


def hunt(game: Game, depth: int, count: int) -> None:
    rng = random.Random(game.seed)
    monsters = [e for e in game.world.entities_with(AI) if level_of(game.world, e) == depth]
    game.world.add(game.player, Melee(damage=99, to_hit=100))
    for monster in monsters[:count]:
        game.world.add(monster, Health(1, 1))
        attack(game.world, game.bus, rng, game.player, monster)
    # Collect what the bodies left behind.
    scavenge(game, (depth,))
    for entity, (item, _pos) in list(game.world.query(Item, Position)):
        if level_of(game.world, entity) == depth and item.kind == "trophy":
            game.world.remove(entity, Position)
            game.world.remove(entity, OnLevel)
            inv = game.world.get(game.player, Inventory) or Inventory()
            game.world.add(game.player, Inventory(items=(*inv.items, entity)))


def village_trader(game: Game) -> int:
    for entity, (villager,) in game.world.query(Villager):
        if villager.role == "trader":
            return entity
    raise AssertionError("no trader")


def one_run(seed: int, meta: MetaState, meta_file: Path) -> None:
    game = Game(seed=seed, meta=meta, meta_autosave=False)
    for depth in (1, 2, 3):
        game._ensure_level(depth)
    game.world.add(game.player, OnLevel(3))
    game.depth = 3
    scavenge(game, (1, 2, 3))
    hunt(game, 3, count=4)

    # Walk home with the purse (banking is the transaction under test).
    game.depth = 0
    game.world.add(game.player, OnLevel(0))
    game._bank_purse()

    trader = village_trader(game)
    inv = game.world.get(game.player, Inventory) or Inventory()
    for entity in list(inv.items):
        if game.world.expect(entity, Item).kind == "trophy":
            game._sell(trader, entity)

    stock = game.world.expect(trader, Inventory).items
    if stock:
        cheapest = min(stock, key=lambda e: game.price_for(game.world.expect(e, Item).key, trader))
        game._buy(trader, cheapest)

    if game.meta.stash.slots_total < 10:
        step = (game.meta.stash.slots_total - 4) // 2
        cost = game.prices.stash_upgrades[step]
        if game.meta.currency.denary > cost * 2:
            game._upgrade_stash()

    carried = game.world.get(game.player, Inventory) or Inventory()
    if carried.items and not game.stash_is_full():
        game._deposit(carried.items[0])

    # The forest wins, as it does.
    game.death_by_key = "strzyga" if seed % 3 == 0 else "bies"
    game.death_cause = f"slain by {game.death_by_key}"
    game.apply_death_to_meta()

    # Full file roundtrip every run: stability + honesty.
    save_meta(meta, meta_file)
    reloaded = load_meta(meta_file)
    assert not reloaded.edited
    save_meta(reloaded, meta_file)


def test_fifty_runs_shared_meta(tmp_path: Path) -> None:
    meta_file = tmp_path / "meta.yml"
    meta = MetaState()
    wallets: list[int] = []
    stash_sizes: list[int] = []
    for i in range(RUNS):
        one_run(seed=1000 + i, meta=meta, meta_file=meta_file)
        meta = load_meta(meta_file)
        wallets.append(meta.currency.denary)
        stash_sizes.append(sum(item.count for item in meta.stash.items))

    # (a) Heirlooms, not a savings account: the stash respects its slots
    # and stops growing once they're spoken for.
    assert meta.stash.slots_total <= 10
    assert len(meta.stash.items) <= meta.stash.slots_total
    assert stash_sizes[-1] == stash_sizes[-10], "stash should have plateaued"

    # (b) Currency does not run away: the last stretch is flat-ish, not a curve
    # to the moon, and sinks visibly bit (upgrades happened).
    late = wallets[-15:]
    assert max(late) - min(late) <= max(60, round(statistics.median(late) * 0.5)), (
        f"wallet still swinging late: {late}"
    )
    assert meta.stash.slots_total > 4, "upgrades are the sink that should have fired"

    # (c) Meta survived 50 cycles honestly.
    assert not meta.edited
    assert meta.achievements["runs"] == RUNS
    assert meta.achievements["strzyga_deaths"] >= 3
    assert "strzygobojca" in meta.unlocks.origins  # failure became progress
    assert meta.codex.known, "fifty runs of killing must teach something"


def test_golden_uses_default_meta_fixture() -> None:
    from tests.test_golden_run import produce_transcript

    # Two productions with fresh default meta are byte-identical — the meta
    # layer is an input, not noise.
    assert produce_transcript() == produce_transcript()
