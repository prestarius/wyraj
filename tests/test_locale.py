import asyncio
from collections.abc import Iterator

import pytest

from wyraj.content.locale import load_locale
from wyraj.ui import i18n


@pytest.fixture(autouse=True)
def _restore_language() -> Iterator[None]:
    yield
    i18n.set_language("en")


def test_catalogs_have_matching_keys() -> None:
    en = load_locale("en")
    pl = load_locale("pl")
    assert en, "EN catalog must exist"
    assert set(en) == set(pl), (
        f"catalog drift: only-en={sorted(set(en) - set(pl))}, only-pl={sorted(set(pl) - set(en))}"
    )


def test_t_translates_and_formats() -> None:
    i18n.set_language("pl")
    assert i18n.t("turn", n=7) == "Tura 7"
    assert i18n.t("hunger_starving") == "Umiera z głodu"
    assert i18n.t("nonexistent_key") == "nonexistent_key"
    i18n.set_language("en")
    assert i18n.t("turn", n=7) == "Turn 7"


def test_origin_pl_fields() -> None:
    from wyraj.content.origins import load_origins

    for origin in load_origins().values():
        assert origin.title_pl and origin.intro_pl and origin.description_pl
        assert origin.title_for("pl") == origin.title_pl
        assert origin.title_for("en") == origin.title


def test_app_runs_in_polish() -> None:
    from wyraj.ui.app import WyrajApp

    async def run() -> None:
        i18n.set_language("pl")
        app = WyrajApp(seed=42, lang="pl")
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.press("full_stop")
            await pilot.press("h")
            assert app.game.turn >= 2
            # The narration engine is wired to the PL pack with EN fallback.
            assert app.narration.narrator.fallback_pack is not None  # type: ignore[attr-defined]

    asyncio.run(run())
