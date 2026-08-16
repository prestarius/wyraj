"""US 10.3 — status row: pure projection, overflow, color-blind redundancy."""

from collections.abc import Iterator

import pytest

from wyraj.core.components import StatusEffect
from wyraj.ui import i18n
from wyraj.ui.status_row import build_status_row


@pytest.fixture(autouse=True)
def _restore_language() -> Iterator[None]:
    yield
    i18n.set_language("en")


def _fx(kind: str, duration: int = 5) -> StatusEffect:
    return StatusEffect(kind=kind, duration=duration, power=1)


def test_empty_returns_none() -> None:
    assert build_status_row(()) is None


def test_names_and_turn_counters() -> None:
    row = build_status_row((_fx("bleeding", 4), _fx("blessing", 12)))
    assert row is not None
    assert "bleeding(4)" in row.plain
    assert "blessing(12)" in row.plain


def test_overflow_shows_three_plus_counter() -> None:
    effects = tuple(_fx(k) for k in ("bleeding", "poison", "fear", "blessing", "perun_favor"))
    plain = build_status_row(effects).plain  # type: ignore[union-attr]
    assert "bleeding" in plain and "poison" in plain and "fear" in plain
    assert "blessing" not in plain
    assert "+2 more" in plain
    # Exactly four fit without the counter.
    assert "+.*more" not in build_status_row(effects[:4]).plain  # type: ignore[union-attr]


def test_glyphs_make_kinds_distinguishable_in_mono() -> None:
    a = build_status_row((_fx("bleeding", 5),)).plain  # type: ignore[union-attr]
    b = build_status_row((_fx("poison", 5),)).plain  # type: ignore[union-attr]
    assert a != b


def test_ascii_mode_is_pure_ascii() -> None:
    effects = tuple(_fx(k) for k in ("bleeding", "poison", "blessing", "weles_favor"))
    plain = build_status_row(effects, use_ascii=True).plain  # type: ignore[union-attr]
    assert all(ord(c) < 128 for c in plain)


def test_unknown_kind_falls_back_neutral() -> None:
    row = build_status_row((_fx("soaked"),))
    assert row is not None
    assert "status_soaked(5)" in row.plain  # i18n falls back to the key itself


def test_pl_names() -> None:
    i18n.set_language("pl")
    plain = build_status_row((_fx("fear", 3),)).plain  # type: ignore[union-attr]
    assert "trwoga(3)" in plain
