import random

from tests.test_narration_templates import fixture_event
from wyraj.content.bestiary import load_bestiary
from wyraj.content.items import load_items
from wyraj.core.events import AttackResolved, EntityRef, Outcome
from wyraj.narration.forms import build_form_registry
from wyraj.narration.templates import (
    GrammarPack,
    TemplateNarrator,
    Variant,
    load_pack,
    render,
    rule_key,
)

CONTENT = {**load_bestiary(), **load_items()}
REGISTRY_PL = build_form_registry(CONTENT, "pl")

PLAYER = EntityRef(entity=1, key="player", name="you", is_player=True)
STRZYGA = EntityRef(entity=2, key="strzyga", name="strzyga")


def strzyga_hit() -> AttackResolved:
    return AttackResolved(
        attacker=PLAYER,
        defender=STRZYGA,
        weapon=None,
        damage=3,
        outcome=Outcome.HIT,
        defender_hp_frac=0.5,
    )


def test_every_pl_entry_renders_cleanly() -> None:
    pack = load_pack("pl")
    assert pack.rules, "PL pack must not be empty"
    for (event_key, subkey), variants in pack.rules.items():
        event = fixture_event(event_key, subkey)
        assert rule_key(event) == (event_key, subkey)
        for variant in variants:
            text = render(variant.text, event, REGISTRY_PL)
            assert "{" not in text and "}" not in text
            assert text.strip()


def test_pl_covers_every_en_rule() -> None:
    en_rules = set(load_pack("en").rules)
    pl_rules = set(load_pack("pl").rules)
    missing = en_rules - pl_rules
    assert not missing, f"PL pack missing rules: {sorted(missing)}"


def test_polish_cases_resolve_for_real() -> None:
    event = strzyga_hit()
    assert render("{defender.name.bier}", event, REGISTRY_PL) == "strzygę"
    assert render("{defender.name.narz}", event, REGISTRY_PL) == "strzygą"
    assert render("{defender.name.Mian}", event, REGISTRY_PL) == "Strzyga"
    assert render("{defender.pronoun.subj}", event, REGISTRY_PL) == "ona"
    # No English articles sneak in.
    assert render("{defender.name.def}", event, REGISTRY_PL) == "strzyga"


def test_pl_player_forms() -> None:
    event = strzyga_hit()
    assert render("{attacker.pronoun.poss}", event, REGISTRY_PL) == "twój"
    assert render("{attacker.name.narz}", event, REGISTRY_PL) == "tobą"


def test_item_cases_resolve() -> None:
    from wyraj.core.events import ItemUsed

    gromnica = EntityRef(entity=5, key="gromnica", name="gromnica candle")
    event = ItemUsed(actor=PLAYER, item=gromnica, effect="light", power=80)
    assert render("{item.name.bier}", event, REGISTRY_PL) == "gromnicę"
    assert render("{item.name.narz}", event, REGISTRY_PL) == "gromnicą"


def test_fallback_to_english_for_missing_rule() -> None:
    empty_pl = GrammarPack({})
    en_rule = GrammarPack(
        {("attack_resolved", "player_hit"): [Variant(en="English fallback line.")]}
    )
    narrator = TemplateNarrator(empty_pl, random.Random(1), REGISTRY_PL, fallback_pack=en_rule)
    lines = narrator.compose(strzyga_hit())
    assert lines and lines[0].text == "English fallback line."
