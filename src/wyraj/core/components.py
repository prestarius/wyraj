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
class Purse:
    """Coins on the body — lost with it (M6: banking happens in the wieś)."""

    denary: int = 0


@dataclass(frozen=True)
class CoinPile:
    amount: int


@dataclass(frozen=True)
class ItemMemory:
    """Heirloom trace: the run this item last belonged to."""

    memory_tag: str


@dataclass(frozen=True)
class Channeling:
    """Calling the cranes down: interruptible, turn-counted."""

    turns_left: int


@dataclass(frozen=True)
class Znamie:
    """The mark the cranes leave where they lifted you."""


@dataclass(frozen=True)
class StashChest:
    """The skrzynia — the one thing in the world that outlives you."""


@dataclass(frozen=True)
class Perch:
    """Żerdź: where the cranes set you down, and pick you up again."""


@dataclass(frozen=True)
class Shrine:
    god: str  # "perun" | "weles"


@dataclass(frozen=True)
class Villager:
    """A friendly NPC; bumping talks instead of attacking."""

    role: str  # "innkeeper" | "trader" | "gossip"


@dataclass(frozen=True)
class Swimmer:
    """Can cross open water (utopce are at home there)."""


@dataclass(frozen=True)
class StoryHook:
    """A narrative seed placed by procgen; discovered on first sight."""

    key: str


@dataclass(frozen=True)
class OnLevel:
    depth: int  # 0 = surface puszcza, 1+ = kurhany crypts


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
class ArmorStats:
    protection: int


@dataclass(frozen=True)
class Wearing:
    item: int | None = None  # entity id of the worn armor


@dataclass(frozen=True)
class WornExtras:
    """M7 paper-doll slots beyond torso/weapon (offhand is the lit gromnica)."""

    head: int | None = None  # entity ids
    amulet: int | None = None
    feet: int | None = None


@dataclass(frozen=True)
class Quickslots:
    """M7 quickslots: bindings by item key (stack-aware, auto-refilling)."""

    slot1: str | None = None
    slot2: str | None = None
    slot3: str | None = None
    slot4: str | None = None

    def key_at(self, index: int) -> str | None:
        return (self.slot1, self.slot2, self.slot3, self.slot4)[index]

    def with_key(self, index: int, key: str | None) -> "Quickslots":
        keys = [self.slot1, self.slot2, self.slot3, self.slot4]
        keys[index] = key
        return Quickslots(*keys)


@dataclass(frozen=True)
class Epithet:
    """A weapon that earned a name (M7 §6.2): species it is the bane of."""

    species: str


@dataclass(frozen=True)
class Lifting:
    """A sługa's destination (M8 §2.2): the cradle whose lids it serves."""

    x: int
    y: int


@dataclass(frozen=True)
class Rite:
    """Pressing the lids shut (M8 §2.4): interruptible, turn-counted."""

    turns_left: int


@dataclass(frozen=True)
class Peaceful:
    """Dziady truce (M9 §3): the dead walk but do not begin. Striking one ends it."""


@dataclass(frozen=True)
class StatusEffect:
    kind: str  # "bleeding" | "poison" | "fear" | "blessing"
    duration: int  # turns remaining
    power: int  # per-tick damage (dots) or to-hit modifier (fear/blessing)


@dataclass(frozen=True)
class StatusEffects:
    effects: tuple[StatusEffect, ...] = ()


@dataclass(frozen=True)
class AttackStatus:
    """A status this creature's hits may inflict (from bestiary data)."""

    kind: str
    chance: int  # percent
    duration: int
    power: int


@dataclass(frozen=True)
class LightSource:
    turns: int


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
