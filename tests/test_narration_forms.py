import pytest

from wyraj.content.bestiary import load_bestiary
from wyraj.core.events import EntityRef
from wyraj.narration.forms import FormRegistry, NameForms, build_form_registry

BIES = EntityRef(entity=2, key="bies", name="bies")
PLAYER = EntityRef(entity=1, key="player", name="you", is_player=True)


def test_en_accessors() -> None:
    forms = NameForms(name="strzyga", plural="strzygas")
    assert forms.resolve("base") == "strzyga"
    assert forms.resolve("def") == "the strzyga"
    assert forms.resolve("indef") == "a strzyga"
    assert forms.resolve("plural") == "strzygas"
    assert forms.resolve("Def") == "The strzyga"
    assert forms.pronoun("poss") == "its"


def test_proper_nouns_take_no_article() -> None:
    forms = NameForms(name="Jaga", proper=True)
    assert forms.resolve("def") == "Jaga"
    assert forms.resolve("indef") == "Jaga"


def test_player_forms() -> None:
    registry = FormRegistry()
    forms = registry.forms_for(PLAYER)
    assert forms.resolve("def") == "you"
    assert forms.pronoun("poss") == "your"


def test_polish_case_table_resolves() -> None:
    # M4 authors these natively; the engine must already support them (spec §7).
    forms = NameForms(
        name="strzyga",
        **{
            "mian": "strzyga",
            "dop": "strzygi",
            "cel": "strzydze",
            "bier": "strzygę",
            "narz": "strzygą",
            "miej": "strzydze",
        },
    )
    assert forms.resolve("bier") == "strzygę"
    assert forms.resolve("narz") == "strzygą"
    assert forms.resolve("Bier") == "Strzygę"


def test_unknown_form_falls_back_to_base() -> None:
    forms = NameForms(name="bies")
    assert forms.resolve("bier") == "bies"  # EN maps all cases to base form


def test_unknown_pronoun_raises() -> None:
    with pytest.raises(KeyError):
        NameForms(name="bies").pronoun("nope")


def test_registry_from_bestiary() -> None:
    registry = build_form_registry(load_bestiary())
    assert registry.forms_for(BIES).resolve("plural") == "biesy"


def test_registry_falls_back_to_snapshot_name() -> None:
    registry = FormRegistry()
    unknown = EntityRef(entity=9, key="ghost", name="something pale")
    assert registry.forms_for(unknown).resolve("def") == "the something pale"
