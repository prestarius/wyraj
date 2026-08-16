"""M7 "Sylwetka" core: paper-doll slots, quickslots, blizny, epithets."""

from dataclasses import replace

from wyraj.core.actions import (
    BindQuickslot,
    ClearQuickslot,
    Get,
    UnequipSlot,
    UseQuickslot,
    Wait,
    WearItem,
    WieldItem,
)
from wyraj.core.components import (
    Epithet,
    Health,
    Inventory,
    Position,
    Quickslots,
    Wearing,
    WornExtras,
)
from wyraj.core.events import (
    AttackResolved,
    BliznaEarned,
    ItemUnequipped,
    Outcome,
    QuickslotBound,
    QuickslotCleared,
    QuickslotRefilled,
    QuickslotUsed,
    WeaponNamed,
    WeaponRecognized,
)
from wyraj.core.game import EPITHET_KILLS, Game
from wyraj.core.refs import ref_for
from wyraj.core.systems.items import protection_of
from wyraj.core.systems.quickslots import bound_entity, count_of


def make_game() -> Game:
    return Game(seed=42)


def give_item(game: Game, key: str) -> int:
    definition = game.items_catalog[key]
    ppos = game.world.expect(game.player, Position)
    entity = game.spawn_item(definition, ppos.x, ppos.y)
    game.step(Get())
    return entity


# ---- US 10.2: paper-doll slots -------------------------------------------


def test_wear_head_and_feet_stack_protection() -> None:
    game = make_game()
    kaftan = give_item(game, "kaftan")
    cap = give_item(game, "baranica")
    shoes = give_item(game, "lapcie")
    for entity in (kaftan, cap, shoes):
        game.step(WearItem(entity))
    extras = game.world.expect(game.player, WornExtras)
    assert extras.head == cap and extras.feet == shoes
    assert game.world.expect(game.player, Wearing).item == kaftan
    assert protection_of(game.world, game.player) == 2 + 1 + 1


def test_amulet_trinket_goes_to_amulet_slot() -> None:
    game = make_game()
    amulet = give_item(game, "szkaplerz")
    game.step(WearItem(amulet))
    assert game.world.expect(game.player, WornExtras).amulet == amulet


def test_unequip_frees_slot_and_publishes() -> None:
    game = make_game()
    events: list[ItemUnequipped] = []
    game.bus.subscribe(ItemUnequipped, events.append)
    cap = give_item(game, "baranica")
    game.step(WearItem(cap))
    game.step(UnequipSlot(slot="head"))
    assert game.world.expect(game.player, WornExtras).head is None
    assert cap in game.world.expect(game.player, Inventory).items
    assert events and events[0].item.key == "baranica"
    # Unequipping an empty slot is a quiet no-op.
    game.step(UnequipSlot(slot="head"))
    assert len(events) == 1


# ---- US 10.4: quickslots --------------------------------------------------


def test_quickslot_bind_use_clear_cycle() -> None:
    game = make_game()
    bound: list[QuickslotBound] = []
    used: list[QuickslotUsed] = []
    cleared: list[QuickslotCleared] = []
    game.bus.subscribe(QuickslotBound, bound.append)
    game.bus.subscribe(QuickslotUsed, used.append)
    game.bus.subscribe(QuickslotCleared, cleared.append)
    odwar = give_item(game, "odwar")
    game.step(BindQuickslot(index=0, item=odwar))
    assert game.world.expect(game.player, Quickslots).slot1 == "odwar"
    assert bound[0].index == 0

    game.world.add(game.player, Health(5, 20))
    game.step(UseQuickslot(index=0))
    assert used and used[0].item.key == "odwar"
    assert game.world.expect(game.player, Health).hp > 5
    # Stack empty but binding survives (auto-refill on by default).
    assert game.world.expect(game.player, Quickslots).slot1 == "odwar"
    assert bound_entity(game.world, game.player, 0) is None

    game.step(ClearQuickslot(index=0))
    assert game.world.expect(game.player, Quickslots).slot1 is None
    assert cleared and cleared[0].index == 0


def test_quickslot_refills_on_pickup() -> None:
    game = make_game()
    refilled: list[QuickslotRefilled] = []
    game.bus.subscribe(QuickslotRefilled, refilled.append)
    odwar = give_item(game, "odwar")
    game.step(BindQuickslot(index=1, item=odwar))
    game.step(UseQuickslot(index=1))
    assert count_of(game.world, game.player, "odwar") == 0
    fresh = give_item(game, "odwar")  # walks over a new one and picks it up
    assert refilled and refilled[0].index == 1
    assert bound_entity(game.world, game.player, 1) == fresh


def test_quickslot_hardcore_knob_unbinds_empty_slot() -> None:
    game = make_game()
    game.quickslot_auto_refill = False
    odwar = give_item(game, "odwar")
    game.step(BindQuickslot(index=0, item=odwar))
    game.step(UseQuickslot(index=0))
    assert game.world.expect(game.player, Quickslots).slot1 is None


def test_quickslot_rejects_non_consumables() -> None:
    game = make_game()
    axe = give_item(game, "toporek")
    game.step(BindQuickslot(index=0, item=axe))
    assert (game.world.get(game.player, Quickslots) or Quickslots()).slot1 is None


# ---- US 10.5: blizny and epithets -----------------------------------------


def test_surviving_dying_earns_blizna_once_per_dip() -> None:
    game = make_game()
    earned: list[BliznaEarned] = []
    game.bus.subscribe(BliznaEarned, earned.append)
    health = game.world.expect(game.player, Health)
    game.world.add(game.player, replace(health, hp=1))  # < 10%
    game.step(Wait())
    assert game.blizny == 0  # still dying, no scar yet
    game.world.add(game.player, replace(health, hp=health.max_hp))
    game.step(Wait())
    assert game.blizny == 1
    assert earned and earned[0].count == 1
    game.step(Wait())
    assert game.blizny == 1  # staying healthy earns nothing more


def test_seven_kills_name_a_weapon_and_dziad_greets_it() -> None:
    game = make_game()
    named: list[WeaponNamed] = []
    game.bus.subscribe(WeaponNamed, named.append)
    axe = give_item(game, "toporek")
    game.step(WieldItem(axe))
    weapon_ref = ref_for(game.world, axe)
    player_ref = ref_for(game.world, game.player)
    wilk_ref = ref_for(game.world, game.player)  # entity id irrelevant to the tally
    wilk_ref = replace(wilk_ref, key="wilk", name="wilk", is_player=False)
    for _ in range(EPITHET_KILLS):
        game.bus.publish(
            AttackResolved(
                attacker=player_ref,
                defender=wilk_ref,
                weapon=weapon_ref,
                damage=5,
                outcome=Outcome.KILL,
                defender_hp_frac=0.0,
            )
        )
    assert named and named[0].species == "wilk"
    assert game.world.expect(axe, Epithet).species == "wilk"

    greeted: list[WeaponRecognized] = []
    game.bus.subscribe(WeaponRecognized, greeted.append)
    game._dziad_greets_weapon()
    game._dziad_greets_weapon()  # once per run
    assert len(greeted) == 1
    assert greeted[0].species == "wilk"


def test_named_weapon_keeps_epithet_through_stash() -> None:
    game = make_game()
    axe = give_item(game, "toporek")
    game.world.add(axe, Epithet(species="wilk"))
    game._deposit(axe)
    game._withdraw(len(game.meta.stash.items) - 1)
    inventory = game.world.expect(game.player, Inventory)
    restored = inventory.items[-1]
    assert game.world.expect(restored, Epithet).species == "wilk"


def test_save_roundtrip_keeps_sylwetka_state(tmp_path) -> None:
    from wyraj.persistence.save import load_game, save_game

    game = make_game()
    odwar = give_item(game, "odwar")
    game.step(BindQuickslot(index=2, item=odwar))
    game.blizny = 2
    game.weapon_kills["9:wilk"] = 3
    path = tmp_path / "save.json.gz"
    save_game(game, path)
    loaded = load_game(path)
    assert loaded is not None
    assert loaded.blizny == 2
    assert loaded.weapon_kills == {"9:wilk": 3}
    assert loaded.world.expect(loaded.player, Quickslots).slot3 == "odwar"
