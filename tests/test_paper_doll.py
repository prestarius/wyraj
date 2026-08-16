"""US 10.2 — paper-doll renderer: six slots, heirloom rune, truncation."""

from collections.abc import Iterator

import pytest

from wyraj.core.components import StatusEffect  # noqa: F401 — locale fixture parity
from wyraj.ui import i18n
from wyraj.ui.paper_doll import SLOTS, DollSlot, build_paper_doll


@pytest.fixture(autouse=True)
def _restore_language() -> Iterator[None]:
    yield
    i18n.set_language("en")


def _six(**overrides: DollSlot) -> tuple[DollSlot, ...]:
    base = {slot: DollSlot(slot=slot) for slot in SLOTS}
    base.update(overrides)
    return tuple(base[slot] for slot in SLOTS)


def test_empty_slots_render_dash() -> None:
    plain = build_paper_doll(_six()).plain
    for slot in SLOTS:
        assert slot in plain
    assert plain.count("—") == len(SLOTS)


def test_filled_slots_show_name_detail_and_heirloom_rune() -> None:
    slots = _six(
        weapon=DollSlot(slot="weapon", name="toporek", detail="(damage 5)", heirloom=True),
        off=DollSlot(slot="off", name="gromnica", detail="(lit, 87)"),
    )
    plain = build_paper_doll(slots).plain
    assert "toporek" in plain and "(damage 5)" in plain and "⟲" in plain
    assert "gromnica" in plain and "(lit, 87)" in plain


def test_epithet_renders_quoted() -> None:
    slots = _six(weapon=DollSlot(slot="weapon", name="toporek", epithet="Wilcza Zguba"))
    assert "„Wilcza Zguba”" in build_paper_doll(slots).plain


def test_long_names_truncate_with_ellipsis() -> None:
    slots = _six(torso=DollSlot(slot="torso", name="a very long armored kaftan of the deep woods"))
    plain = build_paper_doll(slots).plain
    assert "…" in plain
    assert "deep woods" not in plain


def test_ascii_mode_is_pure_ascii() -> None:
    slots = _six(weapon=DollSlot(slot="weapon", name="toporek", heirloom=True))
    plain = build_paper_doll(slots, use_ascii=True).plain
    assert all(ord(c) < 128 for c in plain)


def test_pl_labels() -> None:
    i18n.set_language("pl")
    plain = build_paper_doll(_six()).plain
    assert "głowa" in plain and "tors" in plain and "broń" in plain
