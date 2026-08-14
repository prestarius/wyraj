import random

import pytest

from wyraj.content.bestiary import load_bestiary
from wyraj.core.events import (
    AttackResolved,
    EntityDied,
    EntityRef,
    EventBus,
    GameEvent,
    MoveBlocked,
    Outcome,
)
from wyraj.narration.engine import NarrationEngine, NarrationLine
from wyraj.narration.forms import build_form_registry
from wyraj.narration.templates import TemplateNarrator, load_pack, render, rule_key

PLAYER = EntityRef(entity=1, key="player", name="you", is_player=True)
BIES = EntityRef(entity=2, key="bies", name="bies")
REGISTRY = build_form_registry(load_bestiary())


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
    raise AssertionError(f"no fixture for pack rule {event_key}/{subkey}")


def test_every_pack_entry_renders_cleanly() -> None:
    pack = load_pack("en")
    assert pack.rules, "EN pack must not be empty"
    for (event_key, subkey), variants in pack.rules.items():
        event = fixture_event(event_key, subkey)
        assert rule_key(event) == (event_key, subkey)
        for variant in variants:
            text = render(variant.en, event, REGISTRY)
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


def test_engine_collects_lines_and_notifies_sinks() -> None:
    bus = EventBus()
    engine = NarrationEngine(bus, TemplateNarrator(load_pack("en"), random.Random(1), REGISTRY))
    received: list[NarrationLine] = []
    engine.add_sink(received.append)
    bus.publish(fixture_event("attack_resolved", "enemy_hit"))
    assert len(engine.lines) == 1
    assert received == engine.lines
    assert "you" in received[0].text.lower() or "bies" in received[0].text.lower()
