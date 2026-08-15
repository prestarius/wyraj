"""UI-chrome translation helper.

`set_language()` loads the catalog once at startup (EN is always merged
underneath as a fallback); `t()` looks up a key, falling back to the key
itself so a missing string is visible but never fatal. Game *narration* is
never routed through here — narration packs are per-language files.
"""

from wyraj.content.locale import load_locale

_strings: dict[str, str] = {}
_lang = "en"


def set_language(lang: str) -> None:
    global _strings, _lang
    _lang = lang
    _strings = {**load_locale("en"), **(load_locale(lang) if lang != "en" else {})}


def current_language() -> str:
    return _lang


def t(key: str, **kwargs: object) -> str:
    template = _strings.get(key, key)
    return template.format(**kwargs) if kwargs else template


set_language("en")
