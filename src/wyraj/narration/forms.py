"""Grammar-aware string forms (spec §7).

Every nameable thing declares a form table, not a single string. EN needs
only article/plural logic; PL (M4) adds case forms as extra fields (mian,
dop, cel, bier, narz, miej) authored natively in content YAML. A template
slot may request any form — unknown forms fall back to the base name, which
is exactly the EN behavior the spec calls for.

Form spec, as used in template slots like `{defender.name.def}`:
- `base`   — bare name ("bies")
- `def`    — definite ("the bies"); proper nouns skip the article
- `indef`  — indefinite ("a bies")
- `plural` — plural ("biesy", default name + "s")
- any other key — looked up in the table's extra fields (PL cases), else base
- Capitalized spec (`Def`, `Indef`, `Base`…) capitalizes the first letter.
"""

from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from wyraj.core.events import EntityRef


class NameForms(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    plural: str | None = None
    article: str = "a"
    proper: bool = False  # proper nouns ("you", named NPCs) take no article
    pronoun_subj: str = "it"
    pronoun_obj: str = "it"
    pronoun_poss: str = "its"

    def resolve(self, form: str) -> str:
        capitalize = form[:1].isupper()
        text = self._resolve_lower(form.lower())
        return text[:1].upper() + text[1:] if capitalize else text

    def _resolve_lower(self, form: str) -> str:
        match form:
            case "base" | "name":
                return self.name
            case "def":
                return self.name if self.proper else f"the {self.name}"
            case "indef":
                return self.name if self.proper else f"{self.article} {self.name}"
            case "plural":
                return self.plural if self.plural is not None else f"{self.name}s"
            case _:
                extra = self.model_extra or {}
                value = extra.get(form)
                return str(value) if value is not None else self.name

    def pronoun(self, which: str) -> str:
        match which:
            case "subj":
                return self.pronoun_subj
            case "obj":
                return self.pronoun_obj
            case "poss":
                return self.pronoun_poss
            case _:
                raise KeyError(f"unknown pronoun form '{which}'")


PLAYER_FORMS_BY_LANG = {
    "en": NameForms(
        name="you",
        proper=True,
        pronoun_subj="you",
        pronoun_obj="you",
        pronoun_poss="your",
    ),
    "pl": NameForms(
        name="ty",
        proper=True,
        pronoun_subj="ty",
        pronoun_obj="cię",
        pronoun_poss="twój",
        **{
            "mian": "ty",
            "dop": "ciebie",
            "cel": "tobie",
            "bier": "ciebie",
            "narz": "tobą",
            "miej": "tobie",
        },
    ),
}
PLAYER_FORMS = PLAYER_FORMS_BY_LANG["en"]


def build_form_registry(content: Mapping[str, "HasForms"], lang: str = "en") -> "FormRegistry":
    """Build a registry from content definitions (bestiary, items, hooks)."""
    registry = FormRegistry(lang)
    for key, definition in content.items():
        overrides: dict[str, Any] = dict(definition.forms.get(lang, {}))
        if lang != "en":
            # Articleless languages: the base name is the nominative (mian),
            # and def/indef must not glue English articles on.
            overrides.setdefault("name", overrides.get("mian", definition.name))
            overrides.setdefault("proper", True)
        registry.register(key, NameForms(name=overrides.pop("name", definition.name), **overrides))
    return registry


class HasForms(Protocol):
    name: str
    forms: dict[str, dict[str, str | bool]]


class FormRegistry:
    def __init__(self, lang: str = "en") -> None:
        self.lang = lang
        player = PLAYER_FORMS_BY_LANG.get(lang, PLAYER_FORMS_BY_LANG["en"])
        self._entries: dict[str, NameForms] = {"player": player}

    def register(self, key: str, forms: NameForms) -> None:
        self._entries[key] = forms

    def forms_for(self, ref: EntityRef) -> NameForms:
        found = self._entries.get(ref.key)
        if found is not None:
            return found
        # Unregistered things still narrate with their snapshot name.
        return NameForms(name=ref.name)
