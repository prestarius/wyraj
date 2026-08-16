"""US 10.1 — portrait compositor: layer matrix, monochrome safety, ascii purity."""

from wyraj.content.portrait import BANDS, load_portraits
from wyraj.ui.portrait import PortraitState, compose_portrait, get_art, hp_band

STATUSES = ("poison", "fear", "blessing", "wet")


def test_hp_bands() -> None:
    assert hp_band(1.0) == "healthy"
    assert hp_band(0.67) == "healthy"
    assert hp_band(0.5) == "bloodied"
    assert hp_band(0.3) == "wounded"
    assert hp_band(0.09) == "dying"
    assert hp_band(0.0) == "dying"


def test_all_styles_load_with_full_layer_contract() -> None:
    arts = load_portraits()
    assert {"box", "half", "ascii"} <= set(arts)
    for art in arts.values():
        assert "default" in art.base
        assert set(art.wounds) == {"bloodied", "wounded", "dying"}
        assert set(art.status_marks) >= {"poison", "blessing", "wet"}
        assert len(art.scars) >= 2  # spec DoD: two blizny must be visible
        assert len(art.belt) >= 2  # trophy belt (spec §6.2)
        assert "mini" in art.base and len(art.base["mini"]) == 4  # short terminals


def test_matrix_renders_and_monochrome_stays_distinguishable() -> None:
    for art in load_portraits().values():
        plains = {band: compose_portrait(PortraitState(band=band), art).plain for band in BANDS}
        assert len(set(plains.values())) == len(BANDS), f"{art.style}: bands collide in mono"
        base = plains["healthy"]
        for status in STATUSES:
            rendered = compose_portrait(PortraitState(statuses=(status,)), art).plain
            assert rendered != base, f"{art.style}: status '{status}' invisible in mono"
        one = compose_portrait(PortraitState(scars=1), art).plain
        two = compose_portrait(PortraitState(scars=2), art).plain
        assert base != one != two, f"{art.style}: blizny do not accumulate in mono"
        assert compose_portrait(PortraitState(armored=True), art).plain != base
        assert compose_portrait(PortraitState(weapon_key="toporek"), art).plain != base
        belt_one = compose_portrait(PortraitState(trophies=1), art).plain
        belt_two = compose_portrait(PortraitState(trophies=2), art).plain
        assert base != belt_one != belt_two, f"{art.style}: trophy belt invisible in mono"
        mini = compose_portrait(PortraitState(mini=True), art).plain
        assert len(mini.splitlines()) == 4, f"{art.style}: mini variant is not 4 rows"


def test_everything_at_once_renders_every_style() -> None:
    state = PortraitState(
        band="dying",
        weapon_key="ciupaga",
        armored=True,
        halo=True,
        statuses=STATUSES,
        scars=3,
    )
    for art in load_portraits().values():
        assert compose_portrait(state, art).plain.strip()


def test_ascii_art_is_pure_ascii() -> None:
    art = get_art("box", use_ascii=True)
    assert art.style == "ascii"
    state = PortraitState(
        band="dying", weapon_key="toporek", armored=True, statuses=STATUSES, scars=2
    )
    plain = compose_portrait(state, art).plain
    assert all(ord(char) < 128 for char in plain if char != "\n")


def test_unknown_style_and_origin_fall_back() -> None:
    art = get_art("nope")
    assert art.style == "box"
    rendered = compose_portrait(PortraitState(origin="unheard_of"), art)
    assert rendered.plain.strip()
