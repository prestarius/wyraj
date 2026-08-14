import random

from wyraj.core.components import Health, Lore, Melee, Player, Position
from wyraj.core.ecs import World
from wyraj.core.events import AttackResolved, EntityDied, EventBus, Outcome
from wyraj.core.systems.combat import attack


def build_duel(to_hit: int = 100, damage: int = 3, defender_hp: int = 10) -> tuple[World, int, int]:
    world = World()
    a = world.create(Player(), Position(0, 0), Melee(damage=damage, to_hit=to_hit), Health(20, 20))
    d = world.create(
        Lore(key="bies", name="bies"), Position(1, 0), Health(defender_hp, defender_hp)
    )
    return world, a, d


def test_guaranteed_hit_deals_damage() -> None:
    world, a, d = build_duel(to_hit=100, damage=3)
    bus = EventBus()
    events: list[AttackResolved] = []
    bus.subscribe(AttackResolved, events.append)
    attack(world, bus, random.Random(1), a, d)
    assert events[0].outcome is Outcome.HIT
    assert events[0].damage == 3
    assert world.expect(d, Health).hp == 7
    assert events[0].defender_hp_frac == 0.7


def test_guaranteed_miss() -> None:
    world, a, d = build_duel(to_hit=0)
    bus = EventBus()
    events: list[AttackResolved] = []
    bus.subscribe(AttackResolved, events.append)
    attack(world, bus, random.Random(1), a, d)
    assert events[0].outcome is Outcome.MISS
    assert world.expect(d, Health).hp == 10


def test_kill_destroys_and_emits_death() -> None:
    world, a, d = build_duel(to_hit=100, damage=10, defender_hp=5)
    bus = EventBus()
    attacks: list[AttackResolved] = []
    deaths: list[EntityDied] = []
    bus.subscribe(AttackResolved, attacks.append)
    bus.subscribe(EntityDied, deaths.append)
    attack(world, bus, random.Random(1), a, d)
    assert attacks[0].outcome is Outcome.KILL
    assert attacks[0].defender_hp_frac == 0.0
    assert deaths[0].entity.key == "bies"
    assert not world.is_alive(d)


def test_player_death_keeps_entity() -> None:
    world = World()
    bus = EventBus()
    monster = world.create(Lore(key="bies", name="bies"), Melee(damage=99, to_hit=100))
    player = world.create(Player(), Health(5, 5))
    deaths: list[EntityDied] = []
    bus.subscribe(EntityDied, deaths.append)
    attack(world, bus, random.Random(1), monster, player)
    assert deaths[0].entity.is_player
    assert world.is_alive(player)


def test_same_rng_seed_same_rolls() -> None:
    def run() -> list[Outcome]:
        world, a, d = build_duel(to_hit=50, damage=1, defender_hp=100)
        bus = EventBus()
        outcomes: list[Outcome] = []
        bus.subscribe(AttackResolved, lambda e: outcomes.append(e.outcome))
        rng = random.Random(42)
        for _ in range(20):
            attack(world, bus, rng, a, d)
        return outcomes

    assert run() == run()
