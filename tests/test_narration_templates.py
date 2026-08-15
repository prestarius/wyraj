import random

import pytest

from wyraj.content.bestiary import load_bestiary
from wyraj.content.items import load_items
from wyraj.core.events import (
    AttackResolved,
    CoinsBanked,
    CoinsPicked,
    DziadRecognized,
    EntityDied,
    EntityRef,
    EventBus,
    GameEvent,
    HeirloomWielded,
    HungerChanged,
    ItemBought,
    ItemPickedUp,
    ItemSold,
    ItemUsed,
    ItemWielded,
    ItemWorn,
    LevelChanged,
    LightExtinguished,
    LoreDiscovered,
    MoveBlocked,
    Outcome,
    Rested,
    StarvationHit,
    StashDeposited,
    StashUpgraded,
    StashWithdrawn,
    StatusApplied,
    StatusExpired,
    StatusTick,
    TalkedTo,
)
from wyraj.narration.engine import NarrationEngine, NarrationLine
from wyraj.narration.forms import build_form_registry
from wyraj.narration.templates import TemplateNarrator, load_pack, render, rule_key

PLAYER = EntityRef(entity=1, key="player", name="you", is_player=True)
BIES = EntityRef(entity=2, key="bies", name="bies")
ODWAR = EntityRef(entity=3, key="odwar", name="odwar of yarrow")
CIUPAGA = EntityRef(entity=4, key="ciupaga", name="shepherd's ciupaga")
REGISTRY = build_form_registry({**load_bestiary(), **load_items()})


def fixture_event(event_key: str, subkey: str | None) -> GameEvent:
    """Build an event that maps to the given pack rule."""
    if event_key == "attack_resolved":
        assert subkey is not None
        side, _, outcome = subkey.partition("_")
        attacker, defender = (PLAYER, BIES) if side == "player" else (BIES, PLAYER)
        return AttackResolved(
            attacker=attacker,
            defender=defender,
            weapon=None,
            damage=3,
            outcome=Outcome(outcome),
            defender_hp_frac=0.5,
        )
    if event_key == "entity_died":
        return EntityDied(entity=PLAYER if subkey == "player" else BIES)
    if event_key == "move_blocked":
        return MoveBlocked(actor=PLAYER if subkey == "player" else BIES, to_pos=(0, 0))
    if event_key == "item_picked_up":
        return ItemPickedUp(actor=PLAYER, item=ODWAR)
    if event_key == "item_used":
        assert subkey is not None
        return ItemUsed(actor=PLAYER, item=ODWAR, effect=subkey, power=8)
    if event_key == "item_wielded":
        return ItemWielded(actor=PLAYER, item=CIUPAGA)
    if event_key == "item_worn":
        return ItemWorn(actor=PLAYER, item=EntityRef(entity=5, key="kaftan", name="quilted kaftan"))
    if event_key == "hunger_changed":
        assert subkey is not None
        return HungerChanged(actor=PLAYER, band=subkey)
    if event_key == "starvation_hit":
        return StarvationHit(actor=PLAYER, damage=1, hp_frac=0.4)
    if event_key == "lore_discovered":
        assert subkey is not None
        return LoreDiscovered(entity=EntityRef(entity=9, key=subkey, name=subkey))
    if event_key == "level_changed":
        assert subkey is not None
        return LevelChanged(depth=1, direction=subkey)
    if event_key == "status_applied":
        assert subkey is not None
        return StatusApplied(actor=PLAYER, kind=subkey, duration=4)
    if event_key == "status_tick":
        assert subkey is not None
        return StatusTick(actor=PLAYER, kind=subkey, damage=1, hp_frac=0.4)
    if event_key == "status_expired":
        assert subkey is not None
        return StatusExpired(actor=PLAYER, kind=subkey)
    if event_key == "light_extinguished":
        return LightExtinguished(actor=PLAYER)
    if event_key == "talked_to":
        assert subkey is not None
        villager = EntityRef(entity=7, key="dziad", name="old Świętosław")
        return TalkedTo(villager=villager, role=subkey)
    if event_key == "rested":
        return Rested(actor=PLAYER)
    if event_key == "item_bought":
        return ItemBought(actor=PLAYER, item=ODWAR, price=18)
    if event_key == "item_sold":
        return ItemSold(actor=PLAYER, item=CIUPAGA, price=28)
    if event_key == "coins_picked":
        return CoinsPicked(actor=PLAYER, amount=7, purse_total=21)
    if event_key == "coins_banked":
        return CoinsBanked(amount=21, wallet_total=140)
    if event_key == "stash_deposited":
        return StashDeposited(item=CIUPAGA)
    if event_key == "stash_withdrawn":
        return StashWithdrawn(item=CIUPAGA, heirloom=subkey == "heirloom")
    if event_key == "stash_upgraded":
        return StashUpgraded(slots=6, price=120)
    if event_key == "heirloom_wielded":
        return HeirloomWielded(actor=PLAYER, item=CIUPAGA)
    if event_key == "dziad_recognized":
        return DziadRecognized(reputation=4)
    raise AssertionError(f"no fixture for pack rule {event_key}/{subkey}")


def test_every_pack_entry_renders_cleanly() -> None:
    pack = load_pack("en")
    assert pack.rules, "EN pack must not be empty"
    for (event_key, subkey), variants in pack.rules.items():
        event = fixture_event(event_key, subkey)
        assert rule_key(event) == (event_key, subkey)
        for variant in variants:
            text = render(variant.text, event, REGISTRY)
            assert "{" not in text and "}" not in text
            assert text.strip()


def test_unresolved_slot_raises() -> None:
    event = EntityDied(entity=BIES)
    with pytest.raises(KeyError):
        render("The {entity.nonexistent} dies.", event, REGISTRY)


def test_narrator_is_deterministic() -> None:
    pack = load_pack("en")
    event = fixture_event("attack_resolved", "player_hit")

    def run() -> list[str]:
        narrator = TemplateNarrator(pack, random.Random(7), REGISTRY)
        return [line.text for _ in range(10) for line in narrator.compose(event)]

    assert run() == run()


def test_unknown_event_is_silent() -> None:
    from wyraj.core.events import EntityMoved

    narrator = TemplateNarrator(load_pack("en"), random.Random(1), REGISTRY)
    moved = EntityMoved(actor=PLAYER, from_pos=(0, 0), to_pos=(1, 0))
    assert narrator.compose(moved) == []


def test_engine_flushes_paragraph_on_turn_end() -> None:
    from wyraj.core.events import TurnEnded

    bus = EventBus()
    engine = NarrationEngine(bus, TemplateNarrator(load_pack("en"), random.Random(1), REGISTRY))
    received: list[NarrationLine] = []
    engine.add_sink(received.append)
    bus.publish(fixture_event("attack_resolved", "enemy_hit"))
    assert engine.lines == []  # buffered until the turn closes
    bus.publish(TurnEnded(1))
    assert len(engine.lines) == 1
    assert received == engine.lines
    assert "you" in received[0].text.lower() or "bies" in received[0].text.lower()
