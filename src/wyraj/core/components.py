"""Core components. All frozen — replace, never mutate."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Position:
    x: int
    y: int


@dataclass(frozen=True)
class Renderable:
    glyph: str
    style: str = "white"
    ascii_glyph: str | None = None  # CP437 fallback for --ascii


@dataclass(frozen=True)
class Health:
    hp: int
    max_hp: int

    @property
    def fraction(self) -> float:
        return self.hp / self.max_hp if self.max_hp else 0.0


@dataclass(frozen=True)
class Melee:
    damage: int
    to_hit: int  # percent chance to hit, 0-100


@dataclass(frozen=True)
class Actor:
    """Participates in the energy-based turn order."""

    speed: int  # energy gained per tick; 100 = baseline
    energy: int = 0


@dataclass(frozen=True)
class Player:
    pass


@dataclass(frozen=True)
class AI:
    behavior: str  # e.g. "approach"


@dataclass(frozen=True)
class Item:
    key: str
    kind: str  # "weapon" | "consumable" | "trinket"


@dataclass(frozen=True)
class WeaponStats:
    damage: int


@dataclass(frozen=True)
class Consumable:
    effect: str  # "heal" | "feed"
    power: int


@dataclass(frozen=True)
class Inventory:
    items: tuple[int, ...] = ()  # entity ids


@dataclass(frozen=True)
class Wielding:
    item: int | None = None  # entity id of the wielded weapon


@dataclass(frozen=True)
class Hunger:
    satiation: int
    max_satiation: int

    @property
    def band(self) -> str:
        if self.satiation <= 0:
            return "starving"
        if self.satiation <= self.max_satiation // 3:
            return "hungry"
        return "sated"


@dataclass(frozen=True)
class Lore:
    """Narrative metadata used by the narration engine."""

    key: str  # content id, e.g. "bies"
    name: str  # display name, e.g. "bies"
    epithets: tuple[str, ...] = field(default=())
    description: str = ""
