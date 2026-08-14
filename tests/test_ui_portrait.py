import itertools

from wyraj.ui.portrait import STYLES, hp_band, render_portrait


def test_hp_bands() -> None:
    assert hp_band(1.0) == "healthy"
    assert hp_band(0.5) == "bloodied"
    assert hp_band(0.25) == "dying"
    assert hp_band(0.0) == "dying"


def test_all_combinations_render() -> None:
    weapons = [None, "noz", "toporek", "ciupaga"]
    for style, band, weapon in itertools.product(STYLES, ("healthy", "bloodied", "dying"), weapons):
        text = render_portrait(style, band, weapon)
        assert text.plain.strip()


def test_portrait_reacts_to_band_and_weapon() -> None:
    for style in STYLES:
        healthy = render_portrait(style, "healthy", None)
        dying = render_portrait(style, "dying", None)
        armed = render_portrait(style, "healthy", "ciupaga")
        # Wound decals change the glyphs; the weapon overlay adds new ones.
        assert healthy.plain != dying.plain
        assert healthy.plain != armed.plain
        # Color wash differs between bands.
        assert str(healthy.style or "") != str(dying.style or "") or healthy.spans != dying.spans


def test_unknown_style_falls_back() -> None:
    assert render_portrait("nope", "healthy", None).plain.strip()
