import pytest
from pydantic import ValidationError

from wyraj.content.bestiary import MonsterDef, load_bestiary


def test_load_real_bestiary() -> None:
    monsters = load_bestiary()
    assert "bies" in monsters
    bies = monsters["bies"]
    assert bies.hp > 0
    assert bies.behavior == "approach"
    assert bies.description


def test_invalid_monster_rejected() -> None:
    with pytest.raises(ValidationError):
        MonsterDef(
            key="broken",
            name="broken",
            glyph="xx",  # must be a single character
            ascii_glyph="x",
            hp=0,  # must be > 0
            speed=100,
            damage=1,
            to_hit=50,
        )
