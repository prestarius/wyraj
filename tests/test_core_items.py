from wyraj.core.actions import Get, UseItem, WieldItem
from wyraj.core.components import (
    Health,
    Hunger,
    Inventory,
    Position,
    Wielding,
)
from wyraj.core.events import AttackResolved, ItemPickedUp, ItemUsed, ItemWielded
from wyraj.core.game import Game


def make_game() -> Game:
    return Game(seed=42)


def give_item(game: Game, key: str) -> int:
    definition = game.items_catalog[key]
    ppos = game.world.expect(game.player, Position)
    entity = game.spawn_item(definition, ppos.x, ppos.y)
    game.step(Get())
    return entity


def test_pickup_moves_item_to_inventory() -> None:
    game = make_game()
    events: list[ItemPickedUp] = []
    game.bus.subscribe(ItemPickedUp, events.append)
    entity = give_item(game, "odwar")
    inventory = game.world.expect(game.player, Inventory)
    assert entity in inventory.items
    assert game.world.get(entity, Position) is None
    assert events[0].item.key == "odwar"


def test_heal_consumable() -> None:
    game = make_game()
    game.world.add(game.player, Health(5, 20))
    entity = give_item(game, "odwar")
    used: list[ItemUsed] = []
    game.bus.subscribe(ItemUsed, used.append)
    game.step(UseItem(entity))
    assert game.world.expect(game.player, Health).hp == 13
    assert used[0].effect == "heal"
    assert not game.world.is_alive(entity)
    assert entity not in game.world.expect(game.player, Inventory).items


def test_feed_consumable_restores_satiation() -> None:
    game = make_game()
    game.world.add(game.player, Hunger(50, 600))
    entity = give_item(game, "chleb")
    game.step(UseItem(entity))
    hunger = game.world.expect(game.player, Hunger)
    assert hunger.satiation > 250  # 50 + 250 minus a couple of turn ticks


def test_wield_changes_attack_damage_and_event_weapon() -> None:
    game = make_game()
    entity = give_item(game, "ciupaga")
    wields: list[ItemWielded] = []
    game.bus.subscribe(ItemWielded, wields.append)
    game.step(WieldItem(entity))
    assert game.world.expect(game.player, Wielding).item == entity
    assert wields[0].item.key == "ciupaga"

    # A monster adjacent to the player: attack should carry weapon data.
    from wyraj.core.systems.combat import attack

    monster = game.spawn_monster(game.bestiary["bies"], 1, 1)
    hits: list[AttackResolved] = []
    game.bus.subscribe(AttackResolved, hits.append)
    while not hits:
        attack(game.world, game.bus, game.rng.combat, game.player, monster)
    landed = [e for e in hits if e.damage > 0]
    missed = [e for e in hits if e.damage == 0]
    for event in hits:
        assert event.weapon is not None and event.weapon.key == "ciupaga"
    for event in landed:
        assert event.damage == 6  # ciupaga damage, not bare-hands 4
    assert landed or missed


def test_item_catalog_loads() -> None:
    game = make_game()
    assert len(game.items_catalog) == 18  # 12 + crane feather + 5 trophies
    kinds = {d.kind for d in game.items_catalog.values()}
    assert kinds == {"weapon", "armor", "consumable", "trinket", "trophy"}


def test_bestiary_roster() -> None:
    game = make_game()
    assert set(game.bestiary) == {"bies", "wilk", "utopiec", "strzyga", "martwiak", "licho"}
